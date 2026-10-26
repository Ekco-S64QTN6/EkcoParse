"""GINA-style spell, buff, debuff, raid alert, and DoT countdown engine with dual-list tracking."""

import re
import sys
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from ekco_parse.models import Timer
from ekco_parse.spawn_timers import get_zone_respawn_seconds
from ekco_parse.spells import NECRO_SPELLS, SPELL_DB, SpellDef, lookup_necro_spell


class CompiledTrigger:
    """Represents a pre-compiled user or built-in trigger pattern."""

    def __init__(
        self,
        name: str,
        pattern: str,
        timer_seconds: float,
        alert_text: str,
        category: str = "buff",
        color: str = "#00F5FF",
        sound: bool = False,
        wear_off_pattern: Optional[str] = None,
    ):
        self.name = name
        self.pattern_str = pattern
        self.regex = re.compile(pattern, re.IGNORECASE)
        self.timer_seconds = timer_seconds
        self.alert_text = alert_text
        self.category = category
        self.color = color
        self.sound = sound
        self.wear_off_str = wear_off_pattern
        self.wear_off_regex = re.compile(wear_off_pattern, re.IGNORECASE) if wear_off_pattern else None


class TimerEngine:
    """
    Manages active timers with distinct separation for:
    1. Active Damage Over Time (DoTs) & CC running clock sorted by expiry (soonest recast first).
    2. Active Buffs & Utilities running clock with duration & recast tracking.
    """

    def __init__(self, triggers_config: Optional[List[Dict[str, Any]]] = None):
        self.triggers: List[CompiledTrigger] = []
        # active_timers: key -> Timer
        self.active_timers: Dict[str, Timer] = {}
        self.recent_alerts: Deque[Dict[str, Any]] = deque(maxlen=30)
        self.audio_enabled: bool = True
        self.alert_callback: Optional[Callable[[Timer], None]] = None

        # Track active target and pending spell casting state
        self.current_target: str = "Unknown Target"
        self.pending_cast_spell: Optional[str] = None
        self.pending_cast_time: Optional[datetime] = None

        if triggers_config:
            self.load_triggers(triggers_config)

    def load_triggers(self, configs: List[Dict[str, Any]]) -> None:
        """Compile and register triggers from configuration dictionary."""
        self.triggers.clear()
        for c in configs:
            try:
                trigger = CompiledTrigger(
                    name=c.get("name", "Trigger"),
                    pattern=c["pattern"],
                    timer_seconds=float(c.get("timer_seconds", 0)),
                    alert_text=c.get("alert_text", "{name} Alert!"),
                    category=c.get("category", "buff"),
                    color=c.get("color", "#00F5FF"),
                    sound=bool(c.get("sound", False)),
                    wear_off_pattern=c.get("wear_off_pattern"),
                )
                self.triggers.append(trigger)
            except Exception as e:
                print(f"[TimerEngine] Error compiling trigger {c.get('name')}: {e}")

    def set_current_target(self, target: str) -> None:
        """Update active combat target for DoT tracking."""
        if target and target.upper() not in ("YOU", "UNKNOWN TARGET"):
            self.current_target = target.strip()

    def handle_spell_cast_start(self, caster: str, spell_name: str, timestamp: datetime) -> None:
        """Called when 'You begin casting <spell>.' is parsed."""
        if caster.lower() == "you":
            self.pending_cast_spell = spell_name.strip()
            self.pending_cast_time = timestamp

    def handle_spell_interrupt(self) -> None:
        """Cancel pending cast if interrupted."""
        self.pending_cast_spell = None
        self.pending_cast_time = None

    def handle_spell_resist(self, spell_name: Optional[str] = None) -> None:
        """Cancel pending spell if resisted."""
        self.pending_cast_spell = None
        self.pending_cast_time = None

    @staticmethod
    def _normalize_mob_name(value: Optional[str]) -> str:
        normalized = " ".join((value or "").split()).casefold()
        # EQ kill messages and spell landing messages can differ only by an
        # article ("a hill giant" vs "the hill giant").
        return re.sub(r"^(?:a|an|the)\s+", "", normalized)

    def on_mob_slain(
        self,
        mob_name: str,
        zone: str = "",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Clear timers for a slain mob and start its respawn timer at the log time."""
        clean_mob = self._normalize_mob_name(mob_name)
        to_delete = []
        for timer_id, timer in self.active_timers.items():
            if clean_mob and self._normalize_mob_name(timer.target) == clean_mob:
                to_delete.append(timer_id)

        for t_id in to_delete:
            self.active_timers.pop(t_id, None)

        # Do not let a pending cast land on the target after it has died.
        if clean_mob and self._normalize_mob_name(self.current_target) == clean_mob:
            self.current_target = "Unknown Target"
            self.handle_spell_interrupt()

        # Add/refresh the respawn timer based on zone.
        if mob_name.strip():
            self.add_respawn_timer(mob_name.strip(), zone, created_at=timestamp)

    def on_player_death(self, play_sound: bool = True) -> None:
        """Clear buffs after death and optionally sound an alert.

        Set play_sound=False while replaying historical log lines at startup so an
        old death does not ring the terminal bell on launch.
        """
        to_delete = [
            tid for tid, t in self.active_timers.items()
            if t.category in ("buff", "cooldown", "util")
        ]
        for tid in to_delete:
            self.active_timers.pop(tid, None)

        self.recent_alerts.appendleft({
            "timestamp": datetime.now(),
            "name": "DEATH",
            "text": "You have died! All buffs cleared.",
            "category": "raid",
            "color": "#FF4040",
        })

        if self.audio_enabled and play_sound:
            self.beep()

    def add_respawn_timer(
        self,
        mob_name: str,
        zone: str = "",
        created_at: Optional[datetime] = None,
    ) -> None:
        """Start a respawn countdown for a slain mob based on zone spawn timer."""
        respawn_sec = get_zone_respawn_seconds(zone)
        normalized_mob = self._normalize_mob_name(mob_name)

        # Replace an existing respawn timer even if the log changes casing or
        # includes a different article for the same creature name.
        for existing_id, existing_timer in list(self.active_timers.items()):
            if (
                existing_timer.category == "respawn"
                and self._normalize_mob_name(existing_timer.name) == normalized_mob
            ):
                self.active_timers.pop(existing_id, None)

        timer_id = f"respawn_{mob_name}"

        timer = Timer(
            id=timer_id,
            name=mob_name,
            alert_text=f"{mob_name} respawning",
            total_seconds=float(respawn_sec),
            remaining_seconds=float(respawn_sec),
            category="respawn",
            color="#FFC857",
            sound=True,
            target=zone or "Unknown",
            created_at=created_at or datetime.now(),
        )
        self.active_timers[timer_id] = timer

    def process_line(self, message: str, timestamp: datetime) -> List[Timer]:
        """Evaluate raw log message against wear-offs, spell landings, and triggers."""
        # Clear failed casts before the elapsed-cast fallback can mistake the resist
        # message for a successful landing. This is important when replaying logs too.
        if (
            re.match(r"^Your spell is interrupted\.$", message, re.IGNORECASE)
            or re.search(
                r"\bresisted\s+(?:your|the)\s+.+?\s+spell\.$",
                message,
                re.IGNORECASE,
            )
        ):
            self.handle_spell_resist()
            return []

        new_timers: List[Timer] = []

        # 1. Wear-off checks
        to_remove = []
        for timer_id, timer in self.active_timers.items():
            if timer.wear_off_pattern:
                try:
                    if re.search(timer.wear_off_pattern, message, re.IGNORECASE):
                        to_remove.append(timer_id)
                except Exception:
                    pass

        # Check generic EverQuest wear-off pattern: Your <Spell> spell has worn off.
        m_worn = re.match(r"^Your (?P<spell>.+?) spell has worn off\.", message, re.IGNORECASE)
        if m_worn:
            sname = m_worn.group("spell").strip().lower()
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.name.lower() == sname])

        # Check SPELL_DB wear off dictionary
        wear_spell = SPELL_DB.lookup_wear_off(message)
        if wear_spell:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.name.lower() == wear_spell.lower()])

        # Check slot-based wear-offs
        msg_low = message.lower()
        if "your flesh returns" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "lich" or "lich" in t.name.lower()])
        if "your shielding fades" in msg_low or "the protective shield fades" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "shielding" or "shield" in t.name.lower()])
        if "your skin returns to normal" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot in ("rune", "skin") or "skin" in t.name.lower()])
        if "you return to life" in msg_low or "you land gently on the ground" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "levitate" or "dead man" in t.name.lower()])
        if "your feet slow down" in msg_low or "the spirit of wolf leaves you" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "sow" or "wolf" in t.name.lower()])
        if "your warm glow fades" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "aego" or "aego" in t.name.lower()])
        if "you feel less heroic" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "heroism" or "hero" in t.name.lower()])
        if "the holy aura fades" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "symbol" or "symbol" in t.name.lower()])
        if "your focus fades" in msg_low or "you feel less focused" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "focus" or "focus" in t.name.lower()])
        if "your mind feels less clear" in msg_low or "the soft breeze fades" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "clarity" or "clarity" in t.name.lower()])
        if "your body slows down" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "haste"])
        if "you stop regenerating" in msg_low:
            to_remove.extend([tid for tid, t in self.active_timers.items() if t.buff_slot == "regen"])

        for t_id in set(to_remove):
            self.cancel_timer(t_id, reason="wore_off")

        # 2. Universal Spell Landing Detection (Self buffs, Raid buffs, DoTs)
        matched_spell = None
        target_name = self.current_target
        pending_sdef = (
            SPELL_DB.lookup_by_name(self.pending_cast_spell)
            if self.pending_cast_spell
            else None
        )
        message_lower = message.casefold()

        # Prefer the spell actually being cast when its landing text matches. Some P99
        # spells share the same message (notably Arch Lich and Demi Lich).
        if (
            pending_sdef
            and pending_sdef.cast_on_you
            and pending_sdef.cast_on_you.strip().casefold() in message_lower
        ):
            matched_spell = pending_sdef
            target_name = "Self"
            self.pending_cast_spell = None
            self.pending_cast_time = None

        # Check if spell landed on YOU (e.g. self-buff or buffed by another player)
        if not matched_spell:
            sdef_you = SPELL_DB.lookup_by_cast_on_you(message)
            if sdef_you:
                matched_spell = sdef_you
                target_name = "Self"

        # Check if spell landed on an enemy (DoT / snare / root / debuff)
        if not matched_spell and self.pending_cast_spell:
            sdef_pend = pending_sdef or SPELL_DB.lookup_by_name(self.pending_cast_spell)
            if (
                sdef_pend
                and sdef_pend.cast_on_other
                and sdef_pend.cast_on_other.casefold() in message_lower
            ):
                matched_spell = sdef_pend
                idx = message_lower.find(sdef_pend.cast_on_other.casefold())
                target_name = message[:idx].strip() if idx > 0 else self.current_target
                self.current_target = target_name
                self.pending_cast_spell = None
                self.pending_cast_time = None

        if not matched_spell:
            res_other = SPELL_DB.lookup_by_cast_on_other(message)
            # Pet-buff landing text can come from any player's pet during startup
            # log replay. Only count it through the pending-cast path above, which
            # proves that this character actually cast that pet buff.
            if res_other and res_other[0].category != "pet_buff":
                landed_sdef, landed_target = res_other

                # spells_us.txt can have overlapping or imperfect landing text for
                # related spells. When a target landing occurs during our pending
                # cast and belongs to the same effect family, trust the explicit cast
                # name instead of adding the generic spell matched from the text.
                offensive_categories = ("dot", "snare", "root", "mez", "debuff")
                use_pending_cast = False
                if (
                    pending_sdef
                    and self.pending_cast_time
                    and pending_sdef.category in offensive_categories
                    and landed_sdef.category == pending_sdef.category
                ):
                    elapsed = (timestamp - self.pending_cast_time).total_seconds()
                    min_elapsed = max(0.0, pending_sdef.cast_time_sec - 1.5)
                    max_elapsed = pending_sdef.cast_time_sec + 3.0
                    use_pending_cast = min_elapsed <= elapsed <= max_elapsed

                if use_pending_cast:
                    matched_spell = pending_sdef
                    self.pending_cast_spell = None
                    self.pending_cast_time = None
                else:
                    matched_spell = landed_sdef

                target_name = landed_target
                self.current_target = target_name

        # If a pending spell was casting and finishes without interrupt/resist
        if not matched_spell and self.pending_cast_spell:
            sdef = pending_sdef or SPELL_DB.lookup_by_name(self.pending_cast_spell)
            if sdef and self.pending_cast_time:
                elapsed = (timestamp - self.pending_cast_time).total_seconds()
                if elapsed >= (sdef.cast_time_sec - 0.5):
                    matched_spell = sdef
                    if sdef.category in ("buff", "cooldown", "util"):
                        target_name = "Self"
                    elif sdef.category == "pet_buff":
                        # The landing text normally identifies the pet. If no
                        # landing line is available, don't assign its timer to
                        # the currently selected combat target.
                        target_name = "Pet"
                    else:
                        target_name = self.current_target
                    self.pending_cast_spell = None
                    self.pending_cast_time = None

        if matched_spell:
            timer = self._add_spell_timer(matched_spell, target_name, timestamp)
            if timer:
                new_timers.append(timer)

        # 3. Custom / Configured Triggers
        for trig in self.triggers:
            m = trig.regex.search(message)
            if m:
                groups = m.groupdict()
                formatted_alert = trig.alert_text
                try:
                    formatted_alert = trig.alert_text.format(**groups)
                except Exception:
                    pass

                t_target = groups.get("target") or groups.get("mob") or "Self"
                timer_key = f"{trig.name}_{t_target}"

                timer = Timer(
                    id=timer_key,
                    name=trig.name,
                    alert_text=formatted_alert,
                    total_seconds=trig.timer_seconds,
                    remaining_seconds=trig.timer_seconds,
                    category=trig.category,
                    color=trig.color,
                    sound=trig.sound,
                    target=t_target,
                    wear_off_pattern=trig.wear_off_str,
                    created_at=timestamp,
                )

                self.active_timers[timer_key] = timer
                new_timers.append(timer)

                self.recent_alerts.appendleft({
                    "timestamp": timestamp,
                    "name": trig.name,
                    "text": formatted_alert,
                    "category": trig.category,
                    "color": trig.color,
                })

                if trig.sound and self.audio_enabled:
                    self.beep()

                if self.alert_callback:
                    self.alert_callback(timer)

        return new_timers

    def _add_spell_timer(self, sdef: SpellDef, target: str, timestamp: datetime) -> Optional[Timer]:
        """Create or refresh a spell timer from a P99 SpellDef."""
        # Instant-effect spells (e.g. Defoliation) should not leave a countdown behind.
        if sdef.duration_seconds <= 0:
            return None

        target = " ".join((target or "Self").split())
        target_key = target.casefold()

        # This is the player's personal Buffs window, not a group buff tracker.
        # During startup catch-up, logs can contain a cleric (or another player)
        # receiving the same buff before/after it landed on us. Do not create a
        # personal buff timer for another character; our own landed lines are
        # normalized to target="Self" by lookup_by_cast_on_you().
        if sdef.category in ("buff", "cooldown", "util") and target_key != "self":
            return None

        spell_key = sdef.name.strip().casefold()
        timer_id = f"spell:{spell_key}::{target_key}"

        # Replace the same buff slot only on the same target. A recast refreshes the
        # existing row instead of creating another row due to target-name casing.
        if sdef.buff_slot:
            to_replace = [
                tid
                for tid, t in self.active_timers.items()
                if t.buff_slot == sdef.buff_slot
                and " ".join((t.target or "Self").split()).casefold() == target_key
            ]
            for tid in to_replace:
                self.active_timers.pop(tid, None)

        # Remove any duplicate spell/target rows left by older case-sensitive IDs.
        duplicates = [
            tid
            for tid, t in self.active_timers.items()
            if t.name.strip().casefold() == spell_key
            and " ".join((t.target or "Self").split()).casefold() == target_key
            and t.category == sdef.category
        ]
        for tid in duplicates:
            self.active_timers.pop(tid, None)

        alert_msg = f"{sdef.name} on {target}" if target != "Self" else f"{sdef.name} Active"

        wear_off_pat = sdef.wear_off or f"Your {sdef.name} spell has worn off\\."
        timer = Timer(
            id=timer_id,
            name=sdef.name,
            alert_text=alert_msg,
            total_seconds=sdef.duration_seconds,
            remaining_seconds=sdef.duration_seconds,
            category=sdef.category,
            color=sdef.color,
            sound=(sdef.category in ("root", "mez", "snare")),
            target=target,
            wear_off_pattern=wear_off_pat,
            buff_slot=sdef.buff_slot,
            created_at=timestamp,
        )

        self.active_timers[timer_id] = timer

        self.recent_alerts.appendleft({
            "timestamp": timestamp,
            "name": sdef.name,
            "text": alert_msg,
            "category": sdef.category,
            "color": sdef.color,
        })

        if self.alert_callback:
            self.alert_callback(timer)

        return timer

    def tick(self, elapsed_seconds: float) -> List[Timer]:
        """Decrement all active timers and reap after expiration grace period."""
        expired = []
        to_delete = []

        for timer_id, timer in list(self.active_timers.items()):
            timer.remaining_seconds -= elapsed_seconds
            if timer.remaining_seconds <= 0:
                expired.append(timer)
                # Keep expired timer on screen for 5 seconds to highlight "RECAST NOW!"
                if timer.remaining_seconds <= -5.0:
                    to_delete.append(timer_id)

        for t_id in to_delete:
            del self.active_timers[t_id]

        return expired

    def get_sorted_dots(self) -> List[Timer]:
        """
        Return active offensive DoTs, snares, roots, and debuffs
        STRICTLY SORTED by remaining seconds ascending (soonest to fade / recast first!).
        """
        dots = [
            t for t in self.active_timers.values()
            if t.category in ("dot", "snare", "root", "mez", "debuff", "raid")
        ]
        return sorted(dots, key=lambda t: t.remaining_seconds)

    def get_sorted_buffs(self) -> List[Timer]:
        """
        Return active self & pet buffs and utilities
        STRICTLY SORTED by remaining seconds ascending (soonest to expire first!).
        """
        buffs = [
            t for t in self.active_timers.values()
            if (
                t.category == "pet_buff"
                or (
                    t.category in ("buff", "cooldown", "util")
                    and (t.target or "Self").strip().casefold() == "self"
                )
            )
        ]
        return sorted(buffs, key=lambda t: t.remaining_seconds)

    def cancel_timer(self, timer_id: str, reason: str = "cancelled") -> Optional[Timer]:
        """Cancel and remove an active timer."""
        return self.active_timers.pop(timer_id, None)

    def clear_all(self) -> None:
        """Clear all active timers."""
        self.active_timers.clear()

    def clear_buffs(self) -> None:
        """Clear only buff timers (used on death/zoning)."""
        to_delete = [tid for tid, t in self.active_timers.items() if t.category in ("buff", "cooldown", "util")]
        for tid in to_delete:
            self.active_timers.pop(tid, None)

    def get_sorted_respawns(self) -> List[Timer]:
        """
        Return active mob respawn timers
        STRICTLY SORTED by remaining seconds ascending (soonest to pop first!).
        """
        respawns = [
            t for t in self.active_timers.values()
            if t.category == "respawn"
        ]
        return sorted(respawns, key=lambda t: t.remaining_seconds)

    def beep(self) -> None:
        """Trigger terminal audio alert bell."""
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception:
            pass
