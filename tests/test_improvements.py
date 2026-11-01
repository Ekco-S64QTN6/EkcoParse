"""Tests for log-session improvements: cooldowns, zoning, camping, levels, logs."""

import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from ekco_parse.config import Config, DEFAULT_CONFIG, character_from_log
from ekco_parse.parser import LogParser
from ekco_parse.session import LogSession
from ekco_parse.spells import SPELL_DB, SpellDef, _SubstringIndex, buff_duration_ticks
from ekco_parse.timer_engine import TimerEngine

T0 = datetime(2026, 11, 1, 12, 0, 0)


def line(t: datetime, msg: str) -> str:
    return f"[{t.strftime('%a %b %d %H:%M:%S %Y')}] {msg}"


class TestSubstringIndex(unittest.TestCase):
    def test_matches_equal_brute_force_in_dict_order(self):
        d = {" is engulfed in darkness.": 1, "'s skin peels away.": 2, "x.": 3, "you feel armored.": 4}
        idx = _SubstringIndex(d)
        for msg in ["a hill giant is engulfed in darkness.", "tpow's skin peels away.", "you feel armored.", "nothing"]:
            low = msg.casefold()
            self.assertEqual(idx.matches(low), [k for k in d if k in low])

    def test_rebuilds_when_dict_grows(self):
        d = {"you feel armored.": 1}
        idx = _SubstringIndex(d)
        self.assertEqual(idx.matches("you feel quick."), [])
        d["you feel quick."] = 2
        self.assertEqual(idx.matches("you feel quick."), ["you feel quick."])


class TestDurations(unittest.TestCase):
    def test_level_scaled_formula_uses_caster_level(self):
        # formula 10 = min(3*level + 10, value)
        self.assertEqual(buff_duration_ticks(10, 190, 60), 190)
        self.assertEqual(buff_duration_ticks(10, 190, 30), 100)
        sdef = SpellDef(name="Test Buff", duration_ticks=190, duration_seconds=1140.0,
                        category="buff", dot_type=None, cast_time_sec=2.0,
                        cast_on_you="You feel tested.", duration_formula=10, duration_value=190)
        self.assertEqual(sdef.duration_at(60), 1140.0)
        self.assertEqual(sdef.duration_at(30), 600.0)

    def test_curated_spells_ignore_level(self):
        sdef = SPELL_DB.lookup_by_name("Arch Lich")
        self.assertEqual(sdef.duration_at(20), sdef.duration_seconds)


class TestCooldowns(unittest.TestCase):
    def test_harvest_starts_ten_minute_recast(self):
        if not SPELL_DB.lookup_recast("Harvest"):
            self.skipTest("spells_us.txt not available")
        te = TimerEngine()
        te.handle_spell_cast_start("You", "Harvest", T0)
        created = te.process_line("You gather mana from your surroundings.", T0 + timedelta(seconds=10))
        names = [t.name for t in created]
        self.assertIn("Harvest recast", names)
        cd = te.active_timers["cooldown:harvest"]
        self.assertEqual(cd.total_seconds, 600.0)
        self.assertIn(cd, te.get_sorted_buffs())

    def test_harvest_survives_the_stun_interrupt_p99_prints_first(self):
        if not SPELL_DB.lookup_recast("Harvest"):
            self.skipTest("spells_us.txt not available")
        te = TimerEngine()
        te.handle_spell_cast_start("You", "Harvest", T0)
        te.process_line("Your spell is interrupted.", T0 + timedelta(seconds=10))
        te.handle_spell_interrupt()
        te.process_line("You are stunned!", T0 + timedelta(seconds=10))
        created = te.process_line("You gather mana from your surroundings.", T0 + timedelta(seconds=10))
        self.assertIn("Harvest recast", [t.name for t in created])

    def test_no_cooldown_when_someone_else_harvests(self):
        te = TimerEngine()
        created = te.process_line("You gather mana from your surroundings.", T0)
        self.assertFalse(any(t.category == "cooldown" for t in created))


class TestZoneAndLogin(unittest.TestCase):
    def _engine_with(self):
        te = TimerEngine()
        te._add_spell_timer(SpellDef(name="Clinging Darkness", duration_ticks=8, duration_seconds=48.0,
                                     category="snare", dot_type=None, cast_time_sec=2.0), "a gnoll", T0)
        te._add_spell_timer(SpellDef(name="Shielding", duration_ticks=360, duration_seconds=2160.0,
                                     category="buff", dot_type=None, cast_time_sec=2.0), "Self", T0)
        return te

    def test_zoning_drops_mob_timers_keeps_buffs(self):
        te = self._engine_with()
        te.on_zone_change()
        self.assertEqual([t.name for t in te.active_timers.values()], ["Shielding"])

    def test_login_gives_back_camped_time(self):
        te = self._engine_with()
        buff = next(t for t in te.active_timers.values() if t.name == "Shielding")
        te.on_login(3600)
        self.assertEqual(buff.created_at, T0 + timedelta(seconds=3600))
        self.assertEqual(buff.remaining_seconds, 2160.0 + 3600)

    def test_catchup_does_not_count_camped_hours(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "eqlog_Testchar_project1999.txt"
            # Shielding lands, we camp 2 hours later, log back in 5 hours later.
            log.write_text("\n".join([
                line(T0, "You feel armored."),
                line(T0 + timedelta(minutes=10), "It will take you about 30 seconds to prepare your camp."),
                line(T0 + timedelta(hours=5), "Welcome to EverQuest!"),
                line(T0 + timedelta(hours=5, seconds=5), "You say, 'back'"),
            ]) + "\n")
            cfg = Config({**DEFAULT_CONFIG, "log_tailer": {"log_dir": d}})
            s = LogSession(cfg)
            s.catchup_from_log(log)
            buffs = s.timer_engine.get_sorted_buffs()
            self.assertEqual(len(buffs), 1, "buff must survive a camp")
            # ~10 minutes of in-game time elapsed, not 5 hours
            self.assertAlmostEqual(buffs[0].total_seconds - buffs[0].remaining_seconds, 605, delta=40)


class TestParserAdditions(unittest.TestCase):
    def setUp(self):
        self.p = LogParser("Ekco")

    def test_rune_absorb(self):
        _, ev = self.p.parse_line(line(T0, "a goblin tries to hit YOU, but YOUR magical skin absorbs the blow!"))
        self.assertEqual((ev.target, ev.miss_type), ("YOU", "rune"))

    def test_level_and_who_and_login(self):
        _, ev = self.p.parse_line(line(T0, "You have gained a level! Welcome to level 27!"))
        self.assertEqual((ev["type"], ev["level"]), ("level", 27))
        _, ev = self.p.parse_line(line(T0, "[60 Sorcerer] Ekco (High Elf) <South Qeynos Bait and Tackle>"))
        self.assertEqual((ev["type"], ev["level"], ev["name"]), ("who_row", 60, "Ekco"))
        _, ev = self.p.parse_line(line(T0, "Welcome to EverQuest!"))
        self.assertEqual(ev["type"], "login")

    def test_zone_entry_vs_who_zone(self):
        _, ev = self.p.parse_line(line(T0, "You have entered The Overthere."))
        self.assertTrue(ev.get("entered"))
        _, ev = self.p.parse_line(line(T0, "There are 3 players in The Overthere."))
        self.assertFalse(ev.get("entered"))


class TestLogSelection(unittest.TestCase):
    def test_character_from_log_name(self):
        self.assertEqual(character_from_log(Path("eqlog_Ekco_project1999.txt")), "Ekco")
        self.assertIsNone(character_from_log(Path("dbg.txt")))

    def test_p99_naming_found_even_with_wrong_server(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "eqlog_Tpow_project1999.txt").write_text("")
            time.sleep(0.01)
            (Path(d) / "eqlog_Other_project1999.txt").write_text("")  # newer, must not win
            cfg = Config({**DEFAULT_CONFIG, "character": {"name": "Tpow", "server": "blue"},
                          "log_tailer": {"log_dir": d}})
            self.assertEqual(cfg.resolve_log_path().name, "eqlog_Tpow_project1999.txt")

    def test_session_takes_character_name_from_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "eqlog_Ekco_project1999.txt"
            log.write_text(line(T0, "[60 Sorcerer] Ekco (High Elf) <Guild>") + "\n")
            cfg = Config({**DEFAULT_CONFIG, "character": {"name": "Tpow", "level": 60},
                          "log_tailer": {"log_dir": d}})
            s = LogSession(cfg)
            s.start(log)
            self.assertEqual(s.character_name, "Ekco")
            self.assertEqual(s.dps_engine.character_name, "Ekco")


if __name__ == "__main__":
    unittest.main()
