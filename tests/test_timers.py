"""Unit tests for GINA-style timers, Necromancer DoT running clock, and Buffs list."""

import unittest
from datetime import datetime, timedelta

from ekco_parse.spells import SPELL_DB
from ekco_parse.timer_engine import TimerEngine


class TestTimerEngine(unittest.TestCase):

    def setUp(self):
        self.engine = TimerEngine()
        self.engine.current_target = "a hill giant"

    def test_necro_dots_running_clock_sorting(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        # P99 Wiki durations: Splurt 102s, Cascading Darkness 96s, Bond of Death 54s.
        self.engine.process_line("a hill giant's body begins to splurt.", t0)
        self.engine.process_line("a hill giant is enveloped in a funeral pyre.", t0)
        self.engine.process_line("a hill giant is engulfed in darkness.", t0)
        self.engine.process_line("a hill giant staggers.", t0)

        # Get sorted DoTs
        sorted_dots = self.engine.get_sorted_dots()
        self.assertEqual(len(sorted_dots), 4)

        # Must be strictly ordered by remaining_seconds ascending (soonest to fade first!)
        actual_order = [d.name for d in sorted_dots]
        self.assertEqual(actual_order[0], "Funeral Pyre of Kelador")
        self.assertEqual(actual_order[1], "Bond of Death")
        self.assertIn(actual_order[2], ("Cascading Darkness", "Dooming Darkness"))
        self.assertEqual(actual_order[3], "Splurt")

    def test_buffs_separate_list(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        # Cast Arch Lich (1230s)
        self.engine.process_line("You feel the skin peel from your bones.", t0)
        # Cast Dead Man Floating (4320s)
        self.engine.process_line("You become like the dead.", t0)
        # Also cast a DoT
        self.engine.process_line("a hill giant is enveloped in a funeral pyre.", t0)

        buffs = self.engine.get_sorted_buffs()
        dots = self.engine.get_sorted_dots()

        # Buffs list must contain ONLY buffs
        self.assertEqual(len(buffs), 2)
        buff_names = [b.name for b in buffs]
        self.assertTrue("Arch Lich" in buff_names or "Demi Lich" in buff_names)
        self.assertIn("Dead Man Floating", buff_names)
        self.assertNotIn("Funeral Pyre of Kelador", buff_names)

        # DoTs list must contain ONLY DoTs
        self.assertEqual(len(dots), 1)
        self.assertEqual(dots[0].name, "Funeral Pyre of Kelador")

    def test_resisted_cast_does_not_create_timer(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        resist_messages = (
            "Your target resisted the Scourge spell.",
            "a hill giant resisted your Scourge spell.",
        )

        for message in resist_messages:
            with self.subTest(message=message):
                engine = TimerEngine()
                engine.current_target = "a hill giant"
                engine.handle_spell_cast_start("You", "Scourge", t0)

                created = engine.process_line(message, t0 + timedelta(seconds=7))
                self.assertEqual(created, [])
                self.assertEqual(engine.active_timers, {})
                self.assertIsNone(engine.pending_cast_spell)
                self.assertIsNone(engine.pending_cast_time)

                # A later unrelated log line must not resurrect the failed cast.
                engine.process_line("You say, 'still no landing'.", t0 + timedelta(seconds=15))
                self.assertEqual(engine.active_timers, {})

    def test_recast_refreshes_same_spell_target_even_if_target_case_changes(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        sdef = SPELL_DB.lookup_by_name("Scourge")
        self.assertIsNotNone(sdef)
        first = self.engine._add_spell_timer(sdef, "a hill giant", t0)
        self.assertIsNotNone(first)

        self.engine.tick(35.0)
        recast_time = t0 + timedelta(seconds=35)
        refreshed = self.engine._add_spell_timer(sdef, "A HILL GIANT", recast_time)

        self.assertIsNotNone(refreshed)
        self.assertEqual(len(self.engine.active_timers), 1)
        self.assertEqual(len(self.engine.get_sorted_dots()), 1)
        self.assertEqual(refreshed.remaining_seconds, 126.0)
        self.assertEqual(refreshed.created_at, recast_time)

    def test_demi_lich_uses_p99_wiki_duration_and_cast_identity(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        self.engine.handle_spell_cast_start("You", "Demi Lich", t0)

        created = self.engine.process_line(
            "You feel the skin peel from your bones.",
            t0 + timedelta(seconds=2),
        )
        buffs = self.engine.get_sorted_buffs()

        self.assertEqual([timer.name for timer in buffs], ["Demi Lich"])
        self.assertEqual(buffs[0].total_seconds, 19 * 60)
        self.assertEqual(len(self.engine.active_timers), 1)
        self.assertIsNone(self.engine.pending_cast_spell)
        self.assertEqual(len(created), 1)

    def test_wiki_audited_spell_durations(self):
        expected_seconds = {
            "Arch Lich": 19 * 60,
            "Demi Lich": 19 * 60,
            "Diamondskin": 90 * 60,
            "Scourge": 21 * 6,
            "Plague": 22 * 6,
            "Envenomed Bolt": 8 * 6,
            "Bond of Death": 9 * 6,
            "Cessation of Cor": 10 * 6,
            "Asystole": 10 * 6,
            "Celerity": 16 * 60,
            "Clarity": 27 * 60,
            "Levitate": 19 * 60,
            "Regrowth": 19 * 60,
            "Heroic Bond": 72 * 60,
            "Symbol of Naltron": 54 * 60,
        }
        for spell_name, expected in expected_seconds.items():
            with self.subTest(spell=spell_name):
                spell = SPELL_DB.lookup_by_name(spell_name)
                self.assertIsNotNone(spell, f"{spell_name} should be in the case-insensitive spell catalog")
                self.assertEqual(spell.duration_seconds, expected)

    def test_wear_off_cancels_timer(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        self.engine.process_line("a hill giant is enveloped in a funeral pyre.", t0)
        self.assertEqual(len(self.engine.get_sorted_dots()), 1)

        # Wear-off message
        self.engine.process_line("The funeral pyre ends.", t0)
        self.assertEqual(len(self.engine.get_sorted_dots()), 0)

    def test_mob_slain_clears_dots_on_target(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        self.engine.current_target = "a hill giant"
        self.engine.process_line("a hill giant is enveloped in a funeral pyre.", t0)
        self.engine.process_line("a hill giant's body begins to splurt.", t0)
        self.assertEqual(len(self.engine.get_sorted_dots()), 2)

        # Target slain
        self.engine.on_mob_slain("a hill giant")
        self.assertEqual(len(self.engine.get_sorted_dots()), 0)


if __name__ == "__main__":
    unittest.main()
