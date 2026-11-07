"""Regression tests for main-app event routing."""

import time
import unittest
from datetime import datetime

from ekco_parse.config import load_config
from ekco_parse.spells import SPELL_DB
from ekco_parse.spawn_timers import get_zone_respawn_seconds
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

    def test_spell_and_respawn_countdowns_advance_when_log_is_idle(self):
        now = time.time()
        self.app._last_tick_time = now - 5.0
        t0 = datetime.now()
        spell = SPELL_DB.lookup_by_name("Demi Lich")
        self.assertIsNotNone(spell)
        spell_timer = self.app.timer_engine._add_spell_timer(spell, "Self", t0)
        self.app.timer_engine.add_respawn_timer("a sentry", "Skyshrine", created_at=t0)
        respawn_timer = self.app.timer_engine.active_timers["respawn_a sentry"]
        spell_before = spell_timer.remaining_seconds
        respawn_before = respawn_timer.remaining_seconds

        # The app itself is not mounted in this unit test; isolate timer behavior
        # from Textual's screen/widget refresh.
        from unittest.mock import patch
        with patch.object(self.app, "_update_ui"):
            self.app._tick()

        self.assertAlmostEqual(spell_timer.remaining_seconds, spell_before - 5.0, delta=0.2)
        self.assertAlmostEqual(respawn_timer.remaining_seconds, respawn_before - 5.0, delta=0.2)

    def test_on_mount_resets_tick_clock_after_log_catchup(self):
        from unittest.mock import patch

        self.app._last_tick_time = 10.0
        with (
            patch.object(self.app, "catchup_from_log") as catchup,
            patch("ekco_parse.ui.main_app.LogTailer"),
            patch.object(self.app, "set_interval"),
            patch.object(self.app, "_update_ui"),
            patch("ekco_parse.ui.main_app.time.time", return_value=1234.5),
        ):
            self.app.on_mount()

        catchup.assert_called_once()
        self.assertEqual(self.app._last_tick_time, 1234.5)

    def test_zone_respawn_defaults_match_p99_reference_times(self):
        expected_seconds = {
            "Skyshrine": 30 * 60,
            "Kael Drakkal": 28 * 60,
            "Thurgadin": 7 * 60,
            "Cobalt Scar": 20 * 60,
            "Plane of Fear": 8 * 60 * 60,
            "Plane of Growth": 12 * 60 * 60,
            "Temple of Veeshan": 72 * 60,
            "Plane of Mischief": 70 * 60 + 10,
        }

        for zone, expected in expected_seconds.items():
            with self.subTest(zone=zone):
                self.assertEqual(get_zone_respawn_seconds(zone), expected)

    def test_skyshrine_respawn_timer_uses_30_minutes_and_death_log_time(self):
        self.app.active_zone = "Skyshrine"
        death_time = datetime(2026, 10, 26, 12, 0, 0)

        self.app._process_log_line(log_line("You have slain a sentry!"))

        timer = self.app.timer_engine.active_timers["respawn_a sentry"]
        self.assertEqual(timer.total_seconds, 1800.0)
        self.assertEqual(timer.created_at, death_time)
        self.assertEqual(timer.remaining_seconds, 1800.0)

    def test_named_mob_slain_by_pet_clears_its_active_dot_timers(self):
        self.app.active_zone = "Skyshrine"
        mob = "Ualkic Fe'Dhar"
        death_time = datetime(2026, 10, 26, 12, 0, 1)
        self.app.timer_engine.current_target = mob

        for spell_name in ("Scourge", "Screaming Terror", "Root", "Dooming Darkness"):
            spell = SPELL_DB.lookup_by_name(spell_name)
            self.assertIsNotNone(spell)
            # Landing text occasionally leaves punctuation on an extracted target.
            target_name = f"{mob}." if spell_name == "Dooming Darkness" else mob
            self.app.timer_engine._add_spell_timer(spell, target_name, death_time)

        # Another mob's active DoT should not be cleared by this named kill.
        other_spell = SPELL_DB.lookup_by_name("Scourge")
        self.app.timer_engine._add_spell_timer(other_spell, "a froglok", death_time)

        self.app._process_log_line(
            log_line(f"{mob} has been slain by petname!", 1)
        )

        remaining = list(self.app.timer_engine.active_timers.values())
        self.assertEqual(
            [(timer.name, timer.target) for timer in remaining if timer.category != "respawn"],
            [("Scourge", "a froglok")],
        )
        respawns = [timer for timer in remaining if timer.category == "respawn"]
        self.assertEqual(len(respawns), 1)
        self.assertEqual(respawns[0].name, mob)
        self.assertEqual(respawns[0].total_seconds, 1800.0)
        self.assertEqual(respawns[0].created_at, death_time)
        self.assertEqual(self.app.timer_engine.current_target, "Unknown Target")
        self.assertIsNone(self.app.timer_engine.pending_cast_spell)

    def test_coin_loot_events_update_denomination_totals(self):
        self.app._process_log_line(
            log_line("You receive 2 platinum, 3 gold, 4 silver, and 5 copper from the corpse.")
        )

        self.assertEqual(self.app.loot_engine.total_coin_messages, 1)
        self.assertEqual(self.app.loot_engine.coin_totals["platinum"], 2)
        self.assertEqual(self.app.loot_engine.coin_totals["gold"], 3)
        self.assertEqual(self.app.loot_engine.coin_totals["silver"], 4)
        self.assertEqual(self.app.loot_engine.coin_totals["copper"], 5)
        self.assertIn("platinum", self.app.loot_engine.coin_history[0]["money"])

    def test_mob_death_uses_current_zone_respawn_duration(self):
        self.app.active_zone = "Lower Guk"

        self.app._process_log_line(log_line("You have slain a decaying skeleton!"))

        timer = self.app.timer_engine.active_timers["respawn_a decaying skeleton"]
        self.assertEqual(timer.category, "respawn")
        self.assertEqual(timer.target, "Lower Guk")
        self.assertEqual(timer.total_seconds, 1680.0)


class TestZoneTracking(unittest.TestCase):
    """Zoning (seen via "You have entered" or /who) drops timers from other zones."""

    def setUp(self):
        self.app = EkcoParseApp(config=load_config())
        self.te = self.app.timer_engine
        self.te.audio_enabled = False

    def _add_dot(self, mob: str) -> None:
        spell = SPELL_DB.lookup_by_name("Scourge")
        self.te._add_spell_timer(spell, mob, datetime(2026, 10, 26, 12, 0, 0))

    def test_who_all_is_not_a_zone(self):
        self.app._process_log_line(log_line("You have entered Skyshrine."))
        self.app._process_log_line(log_line("There are 2 players in EverQuest.", 1))
        self.assertEqual(self.app.active_zone, "Skyshrine")

    def test_entering_zone_drops_respawns_from_other_zones(self):
        self.app._process_log_line(log_line("You have entered Plane of Mischief."))
        self.te.add_respawn_timer("Popple Dop", "Plane of Mischief")
        self.app._process_log_line(log_line("You have entered Skyshrine.", 1))
        self.te.add_respawn_timer("a sentry", "Skyshrine")

        names = [t.name for t in self.te.get_sorted_respawns()]
        self.assertEqual(names, ["a sentry"])

    def test_who_in_new_zone_clears_previous_zone_timers(self):
        self.app._process_log_line(log_line("You have entered Plane of Mischief."))
        self.te.add_respawn_timer("Popple Dop", "Plane of Mischief")
        self._add_dot("Popple Dop")

        # The zone-in line was missed; /who shows we are elsewhere now.
        self.app._process_log_line(log_line("There are 3 players in Skyshrine.", 5))

        self.assertEqual(self.app.active_zone, "Skyshrine")
        self.assertEqual(self.te.get_sorted_respawns(), [])
        self.assertEqual(self.te.get_sorted_dots(), [])

    def test_who_in_same_zone_keeps_dots_and_local_respawns(self):
        self.app._process_log_line(log_line("You have entered Skyshrine."))
        self.te.add_respawn_timer("a sentry", "Skyshrine")
        self.te.add_respawn_timer("Jaelk", "EverQuest")  # leftover bad tag
        self._add_dot("a wyvern")

        self.app._process_log_line(log_line("There is 1 player in Skyshrine.", 5))

        self.assertEqual([t.name for t in self.te.get_sorted_respawns()], ["a sentry"])
        self.assertEqual(len(self.te.get_sorted_dots()), 1)

    def test_first_who_does_not_clear_dots_when_zone_was_only_the_default(self):
        self.app.session.active_zone = "Somewhere Else"
        self._add_dot("a wyvern")
        self.app._process_log_line(log_line("There is 1 player in Skyshrine."))
        self.assertEqual(len(self.te.get_sorted_dots()), 1)
        self.assertEqual(self.app.active_zone, "Skyshrine")


if __name__ == "__main__":
    unittest.main()
