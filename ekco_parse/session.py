"""Shared log session: one place that turns EQ log lines into engine state.

Both front ends use this — the Textual dashboard and the click-through HUD —
so event routing, startup catch-up, character detection and log following
behave identically in each.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ekco_parse.config import Config, character_from_log, newest_log
from ekco_parse.dps_engine import DpsEngine
from ekco_parse.loot_engine import LootEngine
from ekco_parse.models import CombatAction, HealAction, LootRecord
from ekco_parse.parser import LogParser
from ekco_parse.tailer import LogTailer
from ekco_parse.timer_engine import TimerEngine

LEVEL_STATE = Path.home() / ".local" / "state" / "ekco-parse" / "levels.json"
# A gap this long before "Welcome to EverQuest!" is treated as time spent camped.
MIN_OFFLINE_GAP_SEC = 20.0
FOLLOW_CHECK_SEC = 5.0
RE_CAMP_START = re.compile(r"^It will take you about (?P<sec>\d+) seconds to prepare your camp\.$")
RE_CAMP_ABORT = re.compile(r"^You abandon your preparations to camp\.$")


class LogSession:
    def __init__(self, config: Config):
        self.config = config
        self.dps_engine = DpsEngine(
            character_name=config.character_name,
            encounter_timeout_sec=config.encounter_timeout_sec,
            history_limit=config.history_limit,
        )
        self.timer_engine = TimerEngine(triggers_config=config.triggers)
        self.loot_engine = LootEngine(history_limit=100)
        self.parser = LogParser(character_name=config.character_name)
        self.tailer: Optional[LogTailer] = None
        self.active_zone: str = config.default_zone
        # False until the log itself names a zone; the config default is a guess.
        self._zone_known = False
        self.is_tailing = False
        self.log_path: Optional[Path] = None
        self._last_log_timestamp: Optional[datetime] = None
        self._last_follow_check = 0.0
        # Live camp detection: buffs freeze in EQ while you are logged out.
        self._camp_deadline: Optional[float] = None
        self.offline = False
        if config.character_level:
            self.timer_engine.set_caster_level(config.character_level)

    # ── character ────────────────────────────────────────────────────────
    @property
    def character_name(self) -> str:
        return self.parser.character_name

    def _set_character(self, name: str) -> None:
        self.parser.character_name = name
        self.dps_engine.character_name = name
        level = self.config.character_level or self._load_levels().get(name)
        if level:
            self.timer_engine.set_caster_level(level)

    def _load_levels(self) -> dict:
        try:
            return json.loads(LEVEL_STATE.read_text())
        except (OSError, ValueError):
            return {}

    def _remember_level(self, name: str, level: int) -> None:
        if self.config.character_level:
            return  # an explicit config value wins
        self.timer_engine.set_caster_level(level)
        levels = self._load_levels()
        if levels.get(name) != level:
            levels[name] = level
            try:
                LEVEL_STATE.parent.mkdir(parents=True, exist_ok=True)
                LEVEL_STATE.write_text(json.dumps(levels, indent=1, sort_keys=True))
            except OSError:
                pass

    # ── lifecycle ────────────────────────────────────────────────────────
    def start(self, path: Optional[Path] = None, catchup=None) -> None:
        """Pick the log, recover state from its recent history, start tailing.

        ``catchup`` lets a front end interpose its own replay hook.
        """
        path = Path(path) if path else self._initial_log()
        self.log_path = path
        name = character_from_log(path)
        self._set_character(name or self.config.character_name)
        self._catchup = catchup or self.catchup_from_log
        self._catchup(path)
        self.tailer = LogTailer(
            filepath=path, start_at_end=True, poll_interval_sec=self.config.poll_interval_sec
        )
        self.is_tailing = self.tailer.open()

    def _initial_log(self) -> Path:
        """The configured character's log, or a newer one if you last played someone else."""
        path = self.config.resolve_log_path()
        if not self.config.follow_active_log:
            return path
        latest = newest_log(self.config.log_dir)
        try:
            if latest and (not path.exists() or latest.stat().st_mtime > path.stat().st_mtime):
                return latest
        except OSError:
            pass
        return path

    def follow_active_log(self) -> bool:
        """Switch logs when another character's log becomes the active one."""
        if not self.config.follow_active_log or not self.log_path:
            return False
        now = time.monotonic()
        if now - self._last_follow_check < FOLLOW_CHECK_SEC:
            return False
        self._last_follow_check = now
        latest = newest_log(self.config.log_dir)
        if not latest or latest == self.log_path:
            return False
        try:
            latest_m = latest.stat().st_mtime
            current_m = self.log_path.stat().st_mtime if self.log_path.exists() else 0
        except OSError:
            return False
        # Only follow a log that is being written right now and is clearly newer.
        if time.time() - latest_m > 30 or latest_m - current_m < 2:
            return False
        self.timer_engine.clear_all()
        self.dps_engine.end_active_encounter(reason="character_switch")
        self.active_zone = self.config.default_zone
        self._zone_known = False
        self.start(latest, catchup=getattr(self, "_catchup", None))
        return True

    def catchup_from_log(self, target_log: Path) -> None:
        """Replay recent history to recover active buffs and correct timers."""
        if not target_log.exists():
            return
        try:
            with open(target_log, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                size = f.tell()
                # Last 400KB (~6,000 lines, several hours of play)
                f.seek(max(0, size - 400000), 0)
                lines = f.readlines()
            for line in lines:
                self.process_line(line, update_recent=False)
            # Remaining time = duration minus in-game time since landing. The
            # reference is the last log line (buffs freeze while camped), and
            # on_login() already moved created_at forward across camp gaps.
            ref_time = self._last_log_timestamp or datetime.now()
            for tid, t in list(self.timer_engine.active_timers.items()):
                t.remaining_seconds = t.total_seconds - (ref_time - t.created_at).total_seconds()
                if t.remaining_seconds <= 0:
                    del self.timer_engine.active_timers[tid]
        except Exception:
            pass

    def tick(self, elapsed_seconds: float) -> None:
        """Advance timers by wall-clock time, pausing buffs while camped."""
        if self._camp_deadline and time.time() > self._camp_deadline:
            self.offline = True
        if self.offline:
            self.timer_engine.tick(elapsed_seconds, categories=("respawn",))
        else:
            self.timer_engine.tick(elapsed_seconds)
        self.dps_engine.check_inactivity()

    def poll(self) -> int:
        """Read and process new log lines; returns how many were read."""
        self.follow_active_log()
        if not self.tailer:
            return 0
        lines = self.tailer.read_available_lines()
        for line in lines:
            self.process_line(line, update_recent=True)
        return len(lines)

    # ── routing ──────────────────────────────────────────────────────────
    def process_line(self, line: str, update_recent: bool = True) -> None:
        parsed = self.parser.parse_line(line)
        if not parsed:
            return
        log_line, event = parsed
        ts = log_line.timestamp
        previous_ts = self._last_log_timestamp
        self._last_log_timestamp = ts

        self.timer_engine.process_line(log_line.message, ts)

        if update_recent:
            m = RE_CAMP_START.match(log_line.message)
            if m:
                self._camp_deadline = time.time() + int(m.group("sec")) + 5
            elif RE_CAMP_ABORT.match(log_line.message):
                self._camp_deadline = None

        if isinstance(event, CombatAction):
            if update_recent:
                self.dps_engine.process_combat_action(event)
            if event.actor.lower() == "you" and event.target.upper() != "YOU":
                self.timer_engine.set_current_target(event.target)
            elif event.target.upper() == "YOU" and event.actor:
                self.timer_engine.set_current_target(event.actor)
        elif isinstance(event, HealAction):
            if update_recent:
                self.dps_engine.process_heal(event)
        elif isinstance(event, LootRecord):
            if update_recent:
                self.loot_engine.record_loot(event)
        elif isinstance(event, dict):
            self._route_event(event, ts, previous_ts, update_recent)

    def _route_event(self, event: dict, ts: datetime, previous_ts: Optional[datetime],
                     update_recent: bool) -> None:
        etype = event.get("type")
        te = self.timer_engine
        if etype == "spell_cast":
            te.handle_spell_cast_start(event.get("caster", ""), event.get("spell", ""), ts)
        elif etype == "spell_interrupt":
            te.handle_spell_interrupt()
        elif etype == "spell_resist":
            te.handle_spell_resist(event.get("spell"))
        elif etype == "death":
            mob = event.get("mob", "")
            slayer = event.get("slayer", "You")
            if update_recent:
                self.dps_engine.on_mob_death(mob, slayer)
                self.loot_engine.record_kill(mob, slayer, ts)
            te.on_mob_slain(mob, self.active_zone, timestamp=ts)
        elif etype == "player_death":
            if update_recent:
                self.dps_engine.end_active_encounter(reason="player_death")
            te.on_player_death(play_sound=update_recent)
        elif etype == "experience":
            if update_recent:
                self.loot_engine.record_exp(ts)
        elif etype == "coin_loot":
            if update_recent:
                self.loot_engine.record_coin_loot(event.get("money", ""), ts)
        elif etype == "zone_change":
            new_zone = event.get("zone") or self.active_zone
            moved = new_zone.casefold() != self.active_zone.casefold()
            # "You have entered" is a real zone-in. A /who naming a different zone
            # means a zone-in was missed, unless the old zone was only the config
            # default guess at startup.
            if moved and (event.get("entered") or self._zone_known):
                te.on_zone_change(new_zone)
            else:
                # Same zone (or first sighting): still drop leftovers from others.
                te.drop_other_zone_respawns(new_zone)
            self.active_zone = new_zone
            self._zone_known = True
        elif etype == "login":
            gap = (ts - previous_ts).total_seconds() if previous_ts else 0.0
            # If live ticking was already paused through the camp, only shift
            # created_at; otherwise also give the lost time back.
            te.on_login(gap if gap >= MIN_OFFLINE_GAP_SEC else 0.0,
                        adjust_remaining=not (update_recent and self.offline))
            self.offline = False
            self._camp_deadline = None
            if update_recent:
                self.dps_engine.end_active_encounter(reason="login")
        elif etype == "level":
            self._remember_level(self.character_name, event["level"])
        elif etype == "who_row":
            if event.get("name", "").casefold() == self.character_name.casefold():
                self._remember_level(self.character_name, event["level"])
