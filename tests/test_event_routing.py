"""Regression tests for main-app event routing."""

import unittest
from datetime import datetime

from ekco_parse.config import load_config
from ekco_parse.ui.main_app import EkcoParseApp


def log_line(message: str, second: int = 0) -> str:
    ts = datetime(2026, 10, 26, 12, 0, second)
    return f"[{ts.strftime('%a %b %d %H:%M:%S %Y')}] {message}"


class TestMainAppEventRouting(unittest.TestCase):
    def setUp(self):
        self.app = EkcoParseApp(config=load_config())
        self.app.timer_engine.audio_enabled = False

    def test_player_death_clears_buff_timers(self):
        self.app._process_log_line(log_line("You become like the dead."))
        self.assertTrue(self.app.timer_engine.get_sorted_buffs())

        self.app._process_log_line(log_line("You have been slain by a hill giant!", 1))

        self.assertEqual(self.app.timer_engine.get_sorted_buffs(), [])
        self.assertTrue(self.app.timer_engine.recent_alerts)
        self.assertIn("died", self.app.timer_engine.recent_alerts[0]["text"].lower())

    def test_mob_death_uses_current_zone_respawn_duration(self):
        self.app.active_zone = "Lower Guk"

        self.app._process_log_line(log_line("You have slain a decaying skeleton!"))

        timer = self.app.timer_engine.active_timers["respawn_a decaying skeleton"]
        self.assertEqual(timer.category, "respawn")
        self.assertEqual(timer.target, "Lower Guk")
        self.assertEqual(timer.total_seconds, 1680.0)


if __name__ == "__main__":
    unittest.main()
