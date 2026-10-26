"""Unit tests for EverQuest log line parsing."""

import unittest
from datetime import datetime
from ekco_parse.models import CombatAction, HealAction, Location, LootRecord
from ekco_parse.parser import LogParser


class TestLogParser(unittest.TestCase):

    def setUp(self):
        self.parser = LogParser(character_name="Ekco")

    def test_loc_parsing(self):
        line = "[Sun Oct 26 12:34:56 2026] Your Location is 2821.39, 10392.84, 0.32"
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, Location)
        self.assertAlmostEqual(event.y, 2821.39)
        self.assertAlmostEqual(event.x, 10392.84)
        self.assertAlmostEqual(event.z, 0.32)

    def test_zone_change(self):
        line = "[Fri Oct 23 05:23:20 2026] You have entered Skyshrine."
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertEqual(event.get("type"), "zone_change")
        self.assertEqual(event.get("zone"), "Skyshrine")

    def test_melee_damage_dealt(self):
        line = "[Sun May 24 18:53:55 2026] You crush Guard Chopin for 50 points of damage."
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, CombatAction)
        self.assertEqual(event.actor, "You")
        self.assertEqual(event.target, "Guard Chopin")
        self.assertEqual(event.verb, "crush")
        self.assertEqual(event.damage, 50)
        self.assertFalse(event.is_crit)

    def test_melee_crit(self):
        line = "[Sun May 24 18:54:00 2026] You kick Guard Wextr for 34 points of damage. (critical)"
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, CombatAction)
        self.assertEqual(event.damage, 34)
        self.assertTrue(event.is_crit)

    def test_tank_damage_taken_on_you(self):
        line = "[Sun May 24 18:53:58 2026] Guard Wextr slashes YOU for 53 points of damage."
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, CombatAction)
        self.assertEqual(event.actor, "Guard Wextr")
        self.assertEqual(event.target, "YOU")
        self.assertEqual(event.verb, "slashes")
        self.assertEqual(event.damage, 53)

    def test_tank_block_defense(self):
        line = "[Sun May 24 18:54:00 2026] Guard Xantar tries to slash YOU, but YOU block!"
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, CombatAction)
        self.assertTrue(event.is_miss)
        self.assertEqual(event.miss_type, "block")

    def test_tank_dodge_defense(self):
        line = "[Sun May 24 18:54:02 2026] Guard Xantar tries to slash YOU, but YOU dodge!"
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, CombatAction)
        self.assertTrue(event.is_miss)
        self.assertEqual(event.miss_type, "dodge")

    def test_enemy_misses_you(self):
        line = "[Sun May 24 18:53:55 2026] Guard Chopin tries to bash YOU, but misses!"
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, CombatAction)
        self.assertTrue(event.is_miss)
        self.assertEqual(event.miss_type, "miss")

    def test_non_melee_damage(self):
        line = "[Wed Oct 21 09:46:40 2026] Taegria Fe`Dhar was hit by non-melee for 784 points of damage."
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, CombatAction)
        self.assertEqual(event.target, "Taegria Fe`Dhar")
        self.assertEqual(event.damage, 784)
        self.assertTrue(event.is_non_melee)

    def test_healing(self):
        line = "[Sun Oct 26 12:34:56 2026] Drippin healed you for 300 points of damage."
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, HealAction)
        self.assertEqual(event.caster, "Drippin")
        self.assertEqual(event.amount, 300)

    def test_loot(self):
        line = "[Thu May 28 00:25:46 2026] --You have looted a Spell: Bristlebane`s Bundle.--"
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertIsInstance(event, LootRecord)
        self.assertEqual(event.item, "Spell: Bristlebane`s Bundle")
        self.assertEqual(event.looter, "You")

    def test_slain_and_exp(self):
        line = "[Wed Oct 21 09:47:24 2026] You have slain Taegria Fe`Dhar!"
        res = self.parser.parse_line(line)
        self.assertIsNotNone(res)
        log_line, event = res
        self.assertEqual(event.get("type"), "death")
        self.assertEqual(event.get("mob"), "Taegria Fe`Dhar")

        exp_line = "[Wed Oct 21 09:47:24 2026] You gain experience!!"
        exp_res = self.parser.parse_line(exp_line)
        self.assertEqual(exp_res[1].get("type"), "experience")


if __name__ == "__main__":
    unittest.main()
