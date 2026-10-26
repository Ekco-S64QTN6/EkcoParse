"""Unit tests for GamParse DPS calculation and combat encounters."""

import unittest
from datetime import datetime, timedelta

from ekco_parse.dps_engine import DpsEngine
from ekco_parse.models import CombatAction


class TestDpsEngine(unittest.TestCase):

    def setUp(self):
        self.engine = DpsEngine(character_name="Ekco", encounter_timeout_sec=10.0)

    def test_encounter_lifecycle(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        # Action 1: player hit
        a1 = CombatAction(actor="You", target="a hill giant", verb="slash", damage=100, timestamp=t0)
        self.engine.process_combat_action(a1)

        self.assertIsNotNone(self.engine.active_encounter)
        self.assertEqual(self.engine.active_encounter.target, "a hill giant")
        self.assertEqual(self.engine.active_encounter.total_damage, 100)

        # Action 2: pet hit 2 seconds later
        t1 = t0 + timedelta(seconds=2)
        a2 = CombatAction(actor="Your pet", target="a hill giant", verb="bite", damage=50, timestamp=t1)
        self.engine.process_combat_action(a2)

        self.assertEqual(self.engine.active_encounter.total_damage, 150)
        self.assertAlmostEqual(self.engine.active_encounter.duration_seconds, 2.0)
        self.assertAlmostEqual(self.engine.active_encounter.total_dps, 75.0)

        # Action 3: target slain
        self.engine.on_mob_death("a hill giant", slayer="You")
        self.assertIsNone(self.engine.active_encounter)
        self.assertEqual(len(self.engine.encounter_history), 1)

        archived = self.engine.encounter_history[0]
        self.assertEqual(archived.target, "a hill giant")
        self.assertEqual(archived.total_damage, 150)

    def test_combatant_summary_metrics(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        self.engine.process_combat_action(
            CombatAction(
                actor="You",
                target="a hill giant",
                verb="slash",
                damage=100,
                is_crit=True,
                timestamp=t0,
            )
        )
        self.engine.process_combat_action(
            CombatAction(
                actor="You",
                target="a hill giant",
                verb="slash",
                damage=0,
                is_miss=True,
                timestamp=t0 + timedelta(seconds=1),
            )
        )

        player = self.engine.active_encounter.get_combatant("You")
        self.assertEqual(player.accuracy, 50.0)
        self.assertEqual(player.crit_rate, 100.0)
        self.assertEqual(player.max_hit, 100)
        self.assertEqual(self.engine.active_encounter.total_damage, 100)

    def test_incoming_damage_does_not_inflate_outgoing_dps(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        incoming = CombatAction(
            actor="a hill giant",
            target="YOU",
            verb="slashes",
            damage=50,
            timestamp=t0,
        )
        self.engine.process_combat_action(incoming)

        enc = self.engine.active_encounter
        self.assertIsNotNone(enc)
        self.assertEqual(enc.total_damage, 0)
        self.assertEqual(self.engine.session_total_damage, 0)
        self.assertNotIn("a hill giant", enc.combatants)
        self.assertEqual(enc.get_combatant("You").damage_taken, 50)

    def test_enemy_misses_contribute_to_avoidance(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        self.engine.process_combat_action(
            CombatAction(
                actor="a hill giant",
                target="YOU",
                verb="slashes",
                damage=50,
                timestamp=t0,
            )
        )
        self.engine.process_combat_action(
            CombatAction(
                actor="a hill giant",
                target="YOU",
                verb="punches",
                damage=0,
                is_miss=True,
                miss_type="dodge",
                timestamp=t0,
            )
        )
        self.engine.process_combat_action(
            CombatAction(
                actor="a hill giant",
                target="YOU",
                verb="bashes",
                damage=0,
                is_miss=True,
                miss_type="miss",
                timestamp=t0,
            )
        )

        player = self.engine.active_encounter.get_combatant("You")
        self.assertEqual(player.enemy_misses, 1)
        self.assertAlmostEqual(player.avoidance_rate, 2 / 3 * 100)

    def test_mitigation_and_avoidance(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        # Mob hits YOU for 50
        a1 = CombatAction(actor="a hill giant", target="YOU", verb="slashes", damage=50, timestamp=t0)
        self.engine.process_combat_action(a1)

        # Mob tries to hit YOU, but YOU dodge
        a2 = CombatAction(
            actor="a hill giant",
            target="YOU",
            verb="punches",
            damage=0,
            is_miss=True,
            miss_type="dodge",
            timestamp=t0,
        )
        self.engine.process_combat_action(a2)

        player = self.engine.active_encounter.get_combatant("You")
        self.assertEqual(player.damage_taken, 50)
        self.assertEqual(player.hits_taken, 1)
        self.assertEqual(player.dodges, 1)
        # Avoidance: 1 avoided out of 2 total incoming = 50%
        self.assertAlmostEqual(player.avoidance_rate, 50.0)


if __name__ == "__main__":
    unittest.main()
