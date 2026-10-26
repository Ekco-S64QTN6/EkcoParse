"""Unit tests for GINA-style timers, Necromancer DoT running clock, and Buffs list."""

import unittest
from datetime import datetime
from ekco_parse.timer_engine import TimerEngine


class TestTimerEngine(unittest.TestCase):

    def setUp(self):
        self.engine = TimerEngine()
        self.engine.current_target = "a hill giant"

    def test_necro_dots_running_clock_sorting(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        # 1. Splurt (96s)
        self.engine.process_line("a hill giant's body begins to splurt.", t0)
        # 2. Funeral Pyre of Kelador (42s)
        self.engine.process_line("a hill giant is enveloped in a funeral pyre.", t0)
        # 3. Cascading Darkness (90s)
        self.engine.process_line("a hill giant is engulfed in darkness.", t0)
        # 4. Bond of Death (24s)
        self.engine.process_line("a hill giant staggers.", t0)

        # Get sorted DoTs
        sorted_dots = self.engine.get_sorted_dots()
        self.assertEqual(len(sorted_dots), 4)

        # Must be strictly ordered by remaining_seconds ascending (soonest to fade first!)
        actual_order = [d.name for d in sorted_dots]
        self.assertEqual(actual_order[0], "Bond of Death")
        self.assertEqual(actual_order[1], "Funeral Pyre of Kelador")
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
