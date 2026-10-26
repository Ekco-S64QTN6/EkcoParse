"""GamParse-style combat and DPS calculation engine."""

import time
import uuid
from collections import deque
from datetime import datetime
from typing import Deque, Dict, List, Optional

from ekco_parse.models import CombatAction, CombatantStats, Encounter, HealAction


class DpsEngine:
    """Manages active fight encounters, live DPS metrics, and combat history."""

    def __init__(
        self,
        character_name: str = "Ekco",
        encounter_timeout_sec: float = 60.0,
        history_limit: int = 50,
    ):
        self.character_name = character_name
        self.encounter_timeout_sec = encounter_timeout_sec
        self.history_limit = history_limit

        self.active_encounter: Optional[Encounter] = None
        self.encounter_history: Deque[Encounter] = deque(maxlen=history_limit)

        # All-time session aggregates
        self.session_start = datetime.now()
        self.session_total_damage: int = 0
        self.session_max_hit: int = 0
        self.session_max_hit_actor: str = ""
        self.session_total_encounters: int = 0
        self.session_total_damage_taken: int = 0

    def process_combat_action(self, action: CombatAction) -> None:
        """Process a hit, miss, crit, or mitigation event."""
        now = action.timestamp

        # Check if active encounter timed out
        if self.active_encounter:
            idle_sec = (now - self.active_encounter.last_action_time).total_seconds()
            if idle_sec > self.encounter_timeout_sec:
                self.end_active_encounter(reason="timeout")

        # Determine target of encounter
        encounter_target = action.target
        if action.target.upper() == "YOU" and action.actor:
            encounter_target = action.actor
        elif action.actor.upper() == "YOU" and action.target:
            encounter_target = action.target

        # Start new encounter if none is active
        if not self.active_encounter:
            self.active_encounter = Encounter(
                id=str(uuid.uuid4())[:8],
                target=encounter_target or "Unknown Target",
                start_time=now,
                last_action_time=now,
                is_active=True,
            )
            self.session_total_encounters += 1

        enc = self.active_encounter
        enc.last_action_time = now
        enc.actions.append(action)

        # If encounter target is still default, refine it
        if enc.target in ("Unknown Target", "YOU") and encounter_target not in ("Unknown Target", "YOU"):
            enc.target = encounter_target

        # Track actor (damage dealer) stats
        actor_name = action.actor
        if actor_name.lower() in ("you", self.character_name.lower()):
            actor_name = "You"

        combatant = enc.get_combatant(actor_name)
        if action.damage > 0:
            combatant.damage_dealt += action.damage
            combatant.hits_landed += 1
            if action.is_crit or action.is_crippling:
                combatant.crits += 1
            if action.is_non_melee:
                combatant.non_melee_damage += action.damage
            if action.damage > combatant.max_hit:
                combatant.max_hit = action.damage

            # Update session aggregates
            self.session_total_damage += action.damage
            if action.damage > self.session_max_hit:
                self.session_max_hit = action.damage
                self.session_max_hit_actor = actor_name
        elif action.is_miss:
            combatant.misses += 1

        # Track tank mitigation if YOU are the target
        if action.target.upper() == "YOU":
            player_tank = enc.get_combatant("You")
            if action.damage > 0:
                player_tank.hits_taken += 1
                player_tank.damage_taken += action.damage
                if action.damage > player_tank.max_hit_taken:
                    player_tank.max_hit_taken = action.damage
                self.session_total_damage_taken += action.damage
            elif action.is_miss:
                m_type = action.miss_type or "miss"
                if m_type == "dodge":
                    player_tank.dodges += 1
                elif m_type == "parry":
                    player_tank.parries += 1
                elif m_type == "riposte":
                    player_tank.ripostes += 1
                elif m_type == "block":
                    player_tank.blocks += 1
                else:
                    # Enemy missed player
                    pass

    def process_heal(self, heal: HealAction) -> None:
        """Process healing cast or received."""
        if not self.active_encounter:
            return

        enc = self.active_encounter
        caster_name = heal.caster
        if caster_name.lower() in ("you", self.character_name.lower()):
            caster_name = "You"

        c = enc.get_combatant(caster_name)
        c.healing_done += heal.amount

        rec_name = heal.recipient
        if rec_name.lower() in ("you", self.character_name.lower()):
            rec_name = "You"
        r = enc.get_combatant(rec_name)
        r.healing_received += heal.amount

    def on_mob_death(self, mob_name: str, slayer: str = "") -> None:
        """Handle target death: finalize active encounter."""
        if self.active_encounter:
            # If the slain mob matches or encounter was active, conclude it
            self.end_active_encounter(reason="death")

    def check_inactivity(self) -> None:
        """Periodic check for idle fight timeout."""
        if self.active_encounter and self.active_encounter.is_active:
            idle = (datetime.now() - self.active_encounter.last_action_time).total_seconds()
            if idle > self.encounter_timeout_sec:
                self.end_active_encounter(reason="timeout")

    def end_active_encounter(self, reason: str = "manual") -> Optional[Encounter]:
        """Conclude active encounter and push to history."""
        if not self.active_encounter:
            return None

        enc = self.active_encounter
        enc.is_active = False
        enc.end_time = enc.last_action_time
        self.encounter_history.appendleft(enc)
        self.active_encounter = None
        return enc

    def reset_session(self) -> None:
        """Reset all combat metrics and history."""
        self.active_encounter = None
        self.encounter_history.clear()
        self.session_start = datetime.now()
        self.session_total_damage = 0
        self.session_max_hit = 0
        self.session_max_hit_actor = ""
        self.session_total_encounters = 0
        self.session_total_damage_taken = 0

    def get_ranked_combatants(self, encounter: Optional[Encounter] = None) -> List[CombatantStats]:
        """Return combatants ordered by total damage dealt descending."""
        target_enc = encounter or self.active_encounter
        if not target_enc:
            return []
        return sorted(
            target_enc.combatants.values(),
            key=lambda c: c.damage_dealt,
            reverse=True,
        )
