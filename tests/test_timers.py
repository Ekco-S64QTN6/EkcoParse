"""Unit tests for GINA-style timers, Necromancer DoT running clock, and Buffs list."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from ekco_parse.models import Timer
from ekco_parse.spells import SPELL_DB, SpellDef
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

    def test_pending_invoke_fear_wins_over_generic_inspire_fear_landing(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        invoke_fear = SpellDef(
            name="Invoke Fear",
            duration_ticks=25,
            duration_seconds=150.0,
            category="mez",
            dot_type=None,
            cast_time_sec=3.0,
            cast_on_other=" is overcome by supernatural terror.",
        )
        inspire_fear = SpellDef(
            name="Inspire Fear",
            duration_ticks=25,
            duration_seconds=150.0,
            category="mez",
            dot_type=None,
            cast_time_sec=3.0,
            cast_on_other=" cowers in terror.",
        )

        # Model local spells_us.txt data where the generic landing lookup maps
        # the target's message to Inspire Fear, even though we cast Invoke Fear.
        with patch.dict(
            SPELL_DB.spells_by_name,
            {"invoke fear": invoke_fear, "inspire fear": inspire_fear},
        ), patch.dict(
            SPELL_DB.spells_by_on_other,
            {inspire_fear.cast_on_other.lower(): inspire_fear},
        ):
            engine = TimerEngine()
            engine.handle_spell_cast_start("You", "Invoke Fear", t0)

            created = engine.process_line(
                "a spectre cowers in terror.",
                t0 + timedelta(seconds=2.5),
            )
            self.assertEqual([timer.name for timer in created], ["Invoke Fear"])
            self.assertEqual([timer.name for timer in engine.get_sorted_dots()], ["Invoke Fear"])
            self.assertEqual(engine.get_sorted_dots()[0].target, "a spectre")
            self.assertIsNone(engine.pending_cast_spell)
            self.assertIsNone(engine.pending_cast_time)

            # A later line must not trigger the elapsed-cast fallback and add a
            # second timer for the original cast.
            engine.process_line("You say, 'still tracking'.", t0 + timedelta(seconds=8))
            self.assertEqual([timer.name for timer in engine.get_sorted_dots()], ["Invoke Fear"])
            self.assertEqual(len(engine.active_timers), 1)

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

    def test_personal_buffs_ignore_other_players_from_startup_log_replay(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        heroism = SPELL_DB.lookup_by_name("Heroic Bond")
        self.assertIsNotNone(heroism)

        # Catch-up can encounter the caster's own landing message as well as ours.
        # The caster's timer must not be counted as one of our personal buffs.
        other_player_timer = self.engine._add_spell_timer(
            heroism, "ClericName", t0
        )
        self.assertIsNone(other_player_timer)
        self.assertEqual(self.engine.get_sorted_buffs(), [])

        # The line indicating that the buff landed on us remains tracked exactly once.
        self.engine.process_line("You feel very heroic.", t0 + timedelta(seconds=1))
        buffs = self.engine.get_sorted_buffs()
        self.assertEqual([timer.name for timer in buffs], ["Heroic Bond"])
        self.assertEqual([timer.target for timer in buffs], ["Self"])
        self.assertEqual(len(self.engine.active_timers), 1)

        # Replaying the same self landing refreshes the same row instead of duplicating it.
        self.engine.process_line("You feel very heroic.", t0 + timedelta(seconds=2))
        buffs = self.engine.get_sorted_buffs()
        self.assertEqual(len(buffs), 1)
        self.assertEqual(len(self.engine.active_timers), 1)
        self.assertEqual(buffs[0].created_at, t0 + timedelta(seconds=2))

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

    def test_mob_slain_clears_all_timers_for_that_mob(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        self.engine.current_target = "a hill giant"
        self.engine.handle_spell_cast_start("You", "Scourge", t0)

        # Timers can belong to the same target across different categories.
        for category in ("dot", "debuff", "snare", "root", "mez", "raid", "buff", "cooldown", "util"):
            timer_id = f"{category}_hill_giant"
            self.engine.active_timers[timer_id] = Timer(
                id=timer_id,
                name=f"Test {category}",
                alert_text=f"Test {category}",
                total_seconds=120.0,
                remaining_seconds=80.0,
                category=category,
                target="the hill giant",  # Articles/case can differ from the kill line.
                created_at=t0,
            )

        # A similar but different mob must keep its timers.
        self.engine.active_timers["other_mob_dot"] = Timer(
            id="other_mob_dot",
            name="Scourge",
            alert_text="Scourge on a hill giantess",
            total_seconds=120.0,
            remaining_seconds=80.0,
            category="dot",
            target="a hill giantess",
            created_at=t0,
        )

        self.engine.on_mob_slain("A HILL GIANT")

        remaining = list(self.engine.active_timers.values())
        self.assertEqual(
            [timer.id for timer in remaining if timer.category != "respawn"],
            ["other_mob_dot"],
        )
        self.assertTrue(any(timer.category == "respawn" and timer.name == "A HILL GIANT" for timer in remaining))
        self.assertEqual(self.engine.current_target, "Unknown Target")
        self.assertIsNone(self.engine.pending_cast_spell)
        self.assertIsNone(self.engine.pending_cast_time)


if __name__ == "__main__":
    unittest.main()
