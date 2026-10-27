"""Main Companion Application for Ekco Parse - Transparent High-Density Overlay."""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, TabbedContent, TabPane

from ekco_parse.config import Config, load_config
from ekco_parse.dps_engine import DpsEngine
from ekco_parse.loot_engine import LootEngine
from ekco_parse.models import CombatAction, HealAction, Location, LootRecord
from ekco_parse.parser import LogParser
from ekco_parse.tailer import LogTailer
from ekco_parse.timer_engine import TimerEngine
from ekco_parse.ui.theme import (
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_PURPLE,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_MUTED,
)
from ekco_parse.ui.widgets.buff_panel import BuffClockWidget
from ekco_parse.ui.widgets.dot_panel import DotClockWidget
from ekco_parse.ui.widgets.dps_panel import DpsWidget
from ekco_parse.ui.widgets.mitigation_panel import MitigationWidget
from ekco_parse.ui.widgets.loot_panel import LootWidget
from ekco_parse.ui.widgets.respawn_panel import RespawnWidget


class EkcoParseApp(App):
    """Transparent, high-density EverQuest P99 companion overlay."""

    CSS = f"""
    Screen {{
        background: ansi_default;
        padding: 0;
        margin: 0;
        overflow: hidden;
    }}

    #main-container {{
        background: ansi_default;
        layout: vertical;
        height: 100%;
        padding: 0 1;
    }}

    .panel {{
        background: ansi_default;
        margin-bottom: 0;
        padding: 0 1;
    }}

    #dot-panel {{
        height: auto;
        max-height: 8;
        border: round {COLOR_MAGENTA};
        background: ansi_default;
    }}

    #dps-panel {{
        height: auto;
        max-height: 8;
        border: round {COLOR_CYAN};
        background: ansi_default;
    }}

    #buff-panel {{
        height: auto;
        max-height: 15;
        border: round {COLOR_GREEN};
        background: ansi_default;
        overflow-y: auto;
    }}

    TabbedContent, TabPane {{
        background: ansi_default;
    }}

    #dashboard-tabs {{
        height: 1fr;
    }}

    /* Keep keyboard tab switching, but remove the visible tab strip. */
    #dashboard-tabs > ContentTabs {{
        display: none;
    }}

    #tab-live, #tab-defense, #tab-ledger {{
        height: 1fr;
        padding: 0;
        background: ansi_default;
    }}

    #mitigation-panel {{
        height: auto;
        max-height: 12;
        border: round {COLOR_CYAN};
        background: ansi_default;
    }}

    #loot-panel {{
        height: 1fr;
        border: round {COLOR_MAGENTA};
        background: ansi_default;
        overflow-y: auto;
    }}

    #respawn-panel, #respawn-live-panel {{
        height: auto;
        max-height: 6;
        border: round {COLOR_AMBER};
        background: ansi_default;
        overflow-y: auto;
    }}
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "spawn_map", "Map"),
        ("r", "reset_encounter", "Reset Fight"),
        ("c", "clear_timers", "Clear Timers"),
        ("s", "toggle_audio", "Mute/Unmute"),
        ("t", "test_sim", "Simulate"),
        ("1", "show_live", "Live"),
        ("2", "show_defense", "Defense"),
        ("3", "show_ledger", "Ledger"),
    ]

    def __init__(self, config: Optional[Config] = None):
        # ANSI default backgrounds let Kitty/compositor opacity show through
        # each widget cell. CSS "transparent" alone can resolve against the
        # opaque Textual theme surface.
        super().__init__(ansi_color=True)
        self.config = config or load_config()

        self.dps_engine = DpsEngine(
            character_name=self.config.character_name,
            encounter_timeout_sec=self.config.encounter_timeout_sec,
            history_limit=self.config.history_limit,
        )
        self.timer_engine = TimerEngine(triggers_config=self.config.triggers)
        self.loot_engine = LootEngine(history_limit=100)
        self.parser = LogParser(character_name=self.config.character_name)

        self.tailer: Optional[LogTailer] = None
        self.active_zone: str = self.config.default_zone
        self.is_tailing: bool = False
        self._last_tick_time = time.time()
        self._last_log_timestamp: Optional[datetime] = None  # Last EQ log timestamp seen

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            # Start directly with the red DoTs panel; the header and tab strip
            # are hidden to keep the game overlay compact.
            with TabbedContent(initial="tab-live", id="dashboard-tabs"):
                with TabPane("Live", id="tab-live"):
                    yield DotClockWidget(id="dot-panel", classes="panel")
                    yield DpsWidget(id="dps-panel", classes="panel")
                    yield BuffClockWidget(id="buff-panel", classes="panel")
                    # Keep the monster countdown visible on the main overlay.
                    yield RespawnWidget(id="respawn-live-panel", classes="panel")
                with TabPane("Defense", id="tab-defense"):
                    yield MitigationWidget(id="mitigation-panel", classes="panel")
                with TabPane("Ledger", id="tab-ledger"):
                    yield LootWidget(id="loot-panel", classes="panel")
                    yield RespawnWidget(id="respawn-panel", classes="panel")

    def on_mount(self) -> None:
        # Request always-on-top via xdotool (non-blocking, best-effort)
        self._set_always_on_top()

        target_log = self.config.resolve_log_path()
        self.catchup_from_log(target_log)

        # Startup replay can take longer than a normal tick. Begin wall-clock
        # delta accounting after replay so its processing time is not charged to
        # every active timer on the first interval.
        self._last_tick_time = time.time()

        self.tailer = LogTailer(
            filepath=target_log,
            start_at_end=True,
            poll_interval_sec=self.config.poll_interval_sec,
        )
        self.is_tailing = self.tailer.open()
        self.set_interval(self.config.tick_interval_sec, self._tick)
        self._update_ui()

    def _set_always_on_top(self) -> None:
        """Use xdotool to set the terminal window as always-on-top."""
        try:
            import subprocess as _sp
            _sp.Popen(
                ["xdotool", "getactivewindow", "set_window", "--overrideredirect", "0"],
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
            )
            # Small delay then set above
            _sp.Popen(
                ["bash", "-c", "sleep 0.3 && xdotool getactivewindow windowactivate --sync set_window --urgency 0 && xdotool getactivewindow windowstate --add ABOVE"],
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
            )
        except Exception:
            pass

    def catchup_from_log(self, target_log: Path) -> None:
        """Scan recent log history on startup to recover active buffs and correct timers."""
        if not target_log.exists():
            return

        try:
            with open(target_log, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                size = f.tell()
                # Scan last 400KB (~6,000 lines, covering past several hours)
                f.seek(max(0, size - 400000), 0)
                lines = f.readlines()

            for line in lines:
                self._process_log_line(line, update_recent=False)

            # Reconcile remaining durations against last LOG timestamp (not wall clock)
            # When offline, EQ buffs freeze — so we measure elapsed in-game time only
            if self._last_log_timestamp:
                ref_time = self._last_log_timestamp
            else:
                ref_time = datetime.now()

            for tid, t in list(self.timer_engine.active_timers.items()):
                elapsed = (ref_time - t.created_at).total_seconds()
                t.remaining_seconds = t.total_seconds - elapsed
                if t.remaining_seconds <= 0:
                    del self.timer_engine.active_timers[tid]
        except Exception:
            pass

    def _tick(self) -> None:
        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # Spell durations are real-time. Log silence (for example, no combat/chat
        # for a while) must not pause buffs or DoT/CC timers, otherwise long buffs
        # drift by minutes and expired effects remain on screen. Respawn timers are
        # wall-clock countdowns too, so advance every active timer on every tick.
        self.timer_engine.tick(dt)

        self.dps_engine.check_inactivity()

        if self.tailer:
            lines = self.tailer.read_available_lines()
            for line in lines:
                self._process_log_line(line, update_recent=True)

        self._update_ui()

    def _process_log_line(self, line: str, update_recent: bool = True) -> None:
        parsed = self.parser.parse_line(line)
        if not parsed:
            return

        log_line, event = parsed
        ts = log_line.timestamp

        # Track last log timestamp for offline detection & timer reconciliation
        self._last_log_timestamp = ts

        self.timer_engine.process_line(log_line.message, ts)

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
            etype = event.get("type")
            if etype == "spell_cast":
                self.timer_engine.handle_spell_cast_start(event.get("caster", ""), event.get("spell", ""), ts)
            elif etype == "spell_interrupt":
                self.timer_engine.handle_spell_interrupt()
            elif etype == "spell_resist":
                self.timer_engine.handle_spell_resist(event.get("spell"))
            elif etype == "death":
                mob = event.get("mob", "")
                slayer = event.get("slayer", "You")
                if update_recent:
                    self.dps_engine.on_mob_death(mob, slayer)
                    self.loot_engine.record_kill(mob, slayer, ts)
                self.timer_engine.on_mob_slain(mob, self.active_zone, timestamp=ts)
            elif etype == "player_death":
                if update_recent:
                    self.dps_engine.end_active_encounter(reason="player_death")
                self.timer_engine.on_player_death(play_sound=update_recent)
            elif etype == "experience":
                if update_recent:
                    self.loot_engine.record_exp(ts)
            elif etype == "coin_loot":
                if update_recent:
                    self.loot_engine.record_coin_loot(event.get("money", ""), ts)
            elif etype == "zone_change":
                self.active_zone = event.get("zone", self.active_zone)

    def _update_ui(self) -> None:
        if not self.is_mounted:
            return

        enc = self.dps_engine.active_encounter
        target_name = enc.target if enc else "NONE"
        fight_dur = enc.duration_seconds if enc else 0.0
        enc_dps = enc.total_dps if enc else 0.0
        tot_dmg = enc.total_damage if enc else 0

        # Update Buffs Panel (all buffs, single lines)
        sorted_buffs = self.timer_engine.get_sorted_buffs()
        self.query_one("#buff-panel", BuffClockWidget).update_buffs(sorted_buffs)

        # Update DoTs Panel
        sorted_dots = self.timer_engine.get_sorted_dots()
        self.query_one("#dot-panel", DotClockWidget).update_dots(sorted_dots)

        # Update DPS Panel
        self.query_one("#dps-panel", DpsWidget).update_encounter(
            encounter=enc,
            session_total_dmg=self.dps_engine.session_total_damage,
        )

        # Defense details are available on their own tab so the compact live
        # overlay remains readable while still exposing the existing engine.
        player_stats = enc.combatants.get("You") if enc else None
        self.query_one("#mitigation-panel", MitigationWidget).update_mitigation(
            encounter=enc,
            player_stats=player_stats,
        )

        # Keep both respawn views in sync: the compact live overlay and Ledger.
        self.query_one("#loot-panel", LootWidget).update_loot(self.loot_engine)
        sorted_respawns = self.timer_engine.get_sorted_respawns()
        self.query_one("#respawn-panel", RespawnWidget).update_respawns(sorted_respawns)
        self.query_one("#respawn-live-panel", RespawnWidget).update_respawns(sorted_respawns)

    def action_show_live(self) -> None:
        self.query_one("#dashboard-tabs", TabbedContent).active = "tab-live"

    def action_show_defense(self) -> None:
        self.query_one("#dashboard-tabs", TabbedContent).active = "tab-defense"

    def action_show_ledger(self) -> None:
        self.query_one("#dashboard-tabs", TabbedContent).active = "tab-ledger"

    def action_reset_encounter(self) -> None:
        self.dps_engine.end_active_encounter(reason="manual_reset")

    def action_clear_timers(self) -> None:
        self.timer_engine.clear_all()

    def action_toggle_audio(self) -> None:
        self.timer_engine.audio_enabled = not self.timer_engine.audio_enabled

    def action_spawn_map(self) -> None:
        try:
            cmd = f"'{sys.executable}' -m ekco_parse.main --map --zone '{self.active_zone}'"
            if shutil.which("kitty"):
                subprocess.Popen(["kitty", "--title", "Ekco Map GPS", "--", "bash", "-lc", cmd])
            elif shutil.which("xterm"):
                subprocess.Popen(["xterm", "-title", "Ekco Map GPS", "-e", "bash", "-lc", cmd])
            else:
                subprocess.Popen(["bash", "-lc", cmd])
        except Exception:
            pass

    def action_test_sim(self) -> None:
        now = datetime.now()
        ts_str = now.strftime("%a %b %d %H:%M:%S %Y")
        self._process_log_line(f"[{ts_str}] You begin casting Splurt.")
        self._process_log_line(f"[{ts_str}] a hill giant`s body begins to splurt.")
        self._process_log_line(f"[{ts_str}] You begin casting Funeral Pyre of Kelador.")
        self._process_log_line(f"[{ts_str}] a hill giant is enveloped in a funeral pyre.")
        self._process_log_line(f"[{ts_str}] You hit a hill giant for 784 points of non-melee damage.")


def main():
    config = load_config()
    app = EkcoParseApp(config=config)
    app.run()


if __name__ == "__main__":
    main()
