"""Unit tests for GINA-style timers, Necromancer DoT running clock, and Buffs list."""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ekco_parse.models import Timer
from ekco_parse.spells import SPELL_DB, SpellDatabase, SpellDef
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
        # Darkness spells share a landing phrase; cast context identifies which
        # spell landed instead of relying on the catalog's first matching name.
        self.engine.handle_spell_cast_start("You", "Dooming Darkness", t0)
        self.engine.process_line(
            "a hill giant is engulfed in darkness.", t0 + timedelta(seconds=4)
        )
        self.engine.handle_spell_cast_start(
            "You", "Bond of Death", t0 + timedelta(seconds=4)
        )
        self.engine.process_line("a hill giant staggers.", t0 + timedelta(seconds=11))

        # Get sorted DoTs
        sorted_dots = self.engine.get_sorted_dots()
        self.assertEqual(len(sorted_dots), 4)

        # Must be strictly ordered by remaining_seconds ascending (soonest to fade first!)
        actual_order = [d.name for d in sorted_dots]
        self.assertEqual(actual_order[0], "Funeral Pyre of Kelador")
        self.assertEqual(actual_order[1], "Bond of Death")
        self.assertIn(actual_order[2], ("Cascading Darkness", "Dooming Darkness"))
        self.assertEqual(actual_order[3], "Splurt")

    def test_pet_combat_stagger_does_not_create_bond_of_death_timer(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)

        # Pet/melee combat can produce the same generic "staggers" text as
        # Bond of Death's landing message. Without a player cast, it is not a DoT.
        created = self.engine.process_line("a hill giant staggers.", t0)
        self.assertEqual(created, [])
        self.assertEqual(self.engine.get_sorted_dots(), [])
        self.assertEqual(self.engine.active_timers, {})

        # The same landing text remains valid when Bond of Death is actually cast.
        self.engine.handle_spell_cast_start("You", "Bond of Death", t0 + timedelta(seconds=1))
        created = self.engine.process_line(
            "a hill giant staggers.",
            t0 + timedelta(seconds=8),
        )
        self.assertEqual([timer.name for timer in created], ["Bond of Death"])
        self.assertEqual([timer.name for timer in self.engine.get_sorted_dots()], ["Bond of Death"])
        self.assertEqual(self.engine.get_sorted_dots()[0].target, "a hill giant")

    def test_pet_targeted_spell_is_classified_as_pet_buff(self):
        # Legacy spells_us.txt stores target type at field 98; field 9 is range.
        fields = [""] * 99
        fields[0] = "99999"
        fields[1] = "Companion Ward"
        fields[4] = "You begin casting Companion Ward."
        fields[5] = "Someone begins casting Companion Ward."
        fields[7] = " is surrounded by companion energy."
        fields[8] = "The companion energy fades."
        fields[9] = "100"  # Range must not be mistaken for target type.
        fields[13] = "5000"
        fields[16] = "0"
        fields[17] = "10"
        fields[83] = "1"  # Beneficial spell.
        fields[98] = "14"  # Pet target type.

        with tempfile.TemporaryDirectory() as spell_dir:
            Path(spell_dir, "spells_us.txt").write_text(
                "^".join(fields) + "\n",
                encoding="latin-1",
            )
            database = SpellDatabase(eq_dir=spell_dir)

        spell = database.lookup_by_name("Companion Ward")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.category, "pet_buff")
        self.assertEqual(spell.duration_seconds, 60.0)

    def test_pet_buff_landing_from_another_player_is_ignored(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        savage_spirit = SpellDef(
            name="Savage Spirit",
            duration_ticks=20,
            duration_seconds=120.0,
            category="pet_buff",
            dot_type=None,
            cast_time_sec=5.0,
            cast_on_other=" is empowered by savage spirit.",
        )

        # Startup replay may include another player's pet buff landing. Since
        # this character did not begin the cast, it must not create a timer.
        with patch.dict(
            SPELL_DB.spells_by_name,
            {"savage spirit": savage_spirit},
        ), patch.dict(
            SPELL_DB.spells_by_on_other,
            {savage_spirit.cast_on_other.lower(): savage_spirit},
        ):
            engine = TimerEngine()
            engine.handle_spell_cast_start("AnotherPlayer", "Savage Spirit", t0)
            created = engine.process_line(
                "another player's pet is empowered by savage spirit.",
                t0 + timedelta(seconds=5),
            )

        self.assertEqual(created, [])
        self.assertEqual(engine.get_sorted_buffs(), [])
        self.assertEqual(engine.active_timers, {})
        self.assertIsNone(engine.pending_cast_spell)

    def test_pet_buff_landing_appears_in_buffs_window(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        pet_buff = SpellDef(
            name="Augmentation of Death",
            duration_ticks=20,
            duration_seconds=120.0,
            category="pet_buff",
            dot_type=None,
            cast_time_sec=5.0,
            cast_on_other=" is protected by a tiny ward.",
        )

        with patch.dict(
            SPELL_DB.spells_by_name,
            {"augmentation of death": pet_buff},
        ), patch.dict(
            SPELL_DB.spells_by_on_other,
            {pet_buff.cast_on_other.lower(): pet_buff},
        ):
            engine = TimerEngine()
            engine.current_target = "a hill giant"
            engine.handle_spell_cast_start("You", "Augmentation of Death", t0)
            created = engine.process_line(
                "Fluffy is protected by a tiny ward.",
                t0 + timedelta(seconds=5),
            )

        self.assertEqual([timer.name for timer in created], ["Augmentation of Death"])
        buffs = engine.get_sorted_buffs()
        self.assertEqual([timer.name for timer in buffs], ["Augmentation of Death"])
        self.assertEqual(buffs[0].target, "Fluffy")
        self.assertEqual(buffs[0].category, "pet_buff")
        self.assertEqual(engine.get_sorted_dots(), [])

    def test_jboots_known_landing_survives_local_catalog_collision(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        duplicate_landing = SpellDef(
            name="Conflicting Local Spell",
            duration_ticks=10,
            duration_seconds=60.0,
            category="buff",
            dot_type=None,
            cast_time_sec=0.0,
            cast_on_you="Your feet feel quick.",
            wear_off="Your conflicting spell fades.",
        )

        # A local spells_us.txt definition can share the JBoots message. The
        # curated known buff should remain authoritative instead of being
        # discarded as ambiguous and leaving the buff list empty.
        with patch.dict(
            SPELL_DB.spells_by_name,
            {"conflicting local spell": duplicate_landing},
        ):
            created = self.engine.process_line("Your feet feel quick.", t0)

        self.assertEqual([timer.name for timer in created], ["JourneymanBoots"])
        self.assertEqual(created[0].target, "Self")
        self.assertEqual(created[0].category, "buff")
        self.assertEqual(created[0].total_seconds, 1080.0)
        self.assertEqual(
            [timer.name for timer in self.engine.get_sorted_buffs()],
            ["JourneymanBoots"],
        )

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

    def test_failed_cast_outcomes_clear_pending_spell(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        for message in ("Your spell did not take hold.", "Your spell fizzles!"):
            with self.subTest(message=message):
                engine = TimerEngine()
                engine.current_target = "a hill giant"
                engine.handle_spell_cast_start("You", "Dooming Darkness", t0)

                created = engine.process_line(message, t0 + timedelta(seconds=4))

                self.assertEqual(created, [])
                self.assertEqual(engine.active_timers, {})
                self.assertIsNone(engine.pending_cast_spell)
                self.assertIsNone(engine.pending_cast_time)

    def test_real_fear_landing_uses_pending_cast_when_messages_are_shared(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        invoke_fear = SpellDef(
            name="Invoke Fear",
            duration_ticks=25,
            duration_seconds=150.0,
            category="mez",
            dot_type=None,
            cast_time_sec=3.0,
            cast_on_you="Your mind fills with fear.",
            cast_on_other=" looks very afraid.",
        )
        inspire_fear = SpellDef(
            name="Inspire Fear",
            duration_ticks=20,
            duration_seconds=120.0,
            category="mez",
            dot_type=None,
            cast_time_sec=3.0,
            cast_on_you="Your mind fills with fear.",
            cast_on_other=" looks very afraid.",
        )

        # These are the literal style of landing messages in the attached log.
        # Even when generic lookup points at Inspire Fear, the explicit cast wins.
        with patch.dict(
            SPELL_DB.spells_by_name,
            {"invoke fear": invoke_fear, "inspire fear": inspire_fear},
        ), patch.dict(
            SPELL_DB.spells_by_on_other,
            {" looks very afraid.": inspire_fear},
        ), patch.dict(
            SPELL_DB.spells_by_on_you,
            {"your mind fills with fear.": inspire_fear},
        ):
            engine = TimerEngine()
            engine.handle_spell_cast_start("You", "Invoke Fear", t0)

            created = engine.process_line(
                "Jaelk looks very afraid.",
                t0 + timedelta(seconds=3),
            )

            self.assertEqual([timer.name for timer in created], ["Invoke Fear"])
            self.assertEqual([timer.target for timer in created], ["Jaelk"])
            self.assertIsNone(engine.pending_cast_spell)
            self.assertIsNone(engine.pending_cast_time)

    def test_ambiguous_landing_is_not_guessed_without_pending_cast(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        invoke_fear = SpellDef(
            name="Invoke Fear",
            duration_ticks=25,
            duration_seconds=150.0,
            category="mez",
            dot_type=None,
            cast_time_sec=3.0,
            cast_on_you="Your mind fills with fear.",
            cast_on_other=" looks very afraid.",
        )
        inspire_fear = SpellDef(
            name="Inspire Fear",
            duration_ticks=20,
            duration_seconds=120.0,
            category="mez",
            dot_type=None,
            cast_time_sec=3.0,
            cast_on_you="Your mind fills with fear.",
            cast_on_other=" looks very afraid.",
        )

        with patch.dict(
            SPELL_DB.spells_by_name,
            {"invoke fear": invoke_fear, "inspire fear": inspire_fear},
        ), patch.dict(
            SPELL_DB.spells_by_on_other,
            {" looks very afraid.": inspire_fear},
        ), patch.dict(
            SPELL_DB.spells_by_on_you,
            {"your mind fills with fear.": inspire_fear},
        ):
            self.assertIsNone(
                SPELL_DB.lookup_by_cast_on_you("Your mind fills with fear.")
            )
            self.assertIsNone(
                SPELL_DB.lookup_by_cast_on_other("Jaelk looks very afraid.")
            )

            engine = TimerEngine()
            created = engine.process_line(
                "Jaelk looks very afraid.",
                t0,
            )
            self.assertEqual(created, [])
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

    def test_unrelated_log_line_does_not_consume_pending_invoke_fear(self):
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

        with patch.dict(
            SPELL_DB.spells_by_name,
            {"invoke fear": invoke_fear, "inspire fear": inspire_fear},
        ), patch.dict(
            SPELL_DB.spells_by_on_other,
            {inspire_fear.cast_on_other.lower(): inspire_fear},
        ):
            engine = TimerEngine()
            engine.handle_spell_cast_start("You", "Invoke Fear", t0)

            # Cross the expected cast time with an unrelated message first.
            created = engine.process_line(
                "You say, 'still casting'.",
                t0 + timedelta(seconds=2.6),
            )
            self.assertEqual(created, [])
            self.assertEqual(engine.pending_cast_spell, "Invoke Fear")
            self.assertEqual(engine.active_timers, {})

            # Even if the landing text maps generically to Inspire Fear, the cast
            # identity should win and only the correctly targeted timer is added.
            created = engine.process_line(
                "a spectre cowers in terror.",
                t0 + timedelta(seconds=3.0),
            )
            self.assertEqual([timer.name for timer in created], ["Invoke Fear"])
            self.assertEqual(len(engine.active_timers), 1)
            timer = next(iter(engine.active_timers.values()))
            self.assertEqual(timer.name, "Invoke Fear")
            self.assertEqual(timer.target, "a spectre")
            self.assertIsNone(engine.pending_cast_spell)

    def test_unrelated_log_line_does_not_create_unknown_dooming_darkness_duplicate(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        dooming_darkness = SpellDef(
            name="Dooming Darkness",
            duration_ticks=16,
            duration_seconds=96.0,
            category="snare",
            dot_type="magic",
            cast_time_sec=4.0,
            cast_on_other=" is engulfed in shadow.",
        )
        cascading_darkness = SpellDef(
            name="Cascading Darkness",
            duration_ticks=16,
            duration_seconds=96.0,
            category="snare",
            dot_type="magic",
            cast_time_sec=7.0,
            cast_on_other=" is engulfed in darkness.",
        )

        with patch.dict(
            SPELL_DB.spells_by_name,
            {"dooming darkness": dooming_darkness, "cascading darkness": cascading_darkness},
        ), patch.dict(
            SPELL_DB.spells_by_on_other,
            {cascading_darkness.cast_on_other.lower(): cascading_darkness},
        ):
            engine = TimerEngine()
            engine.handle_spell_cast_start("You", "Dooming Darkness", t0)

            created = engine.process_line(
                "You say, 'still casting'.",
                t0 + timedelta(seconds=3.6),
            )
            self.assertEqual(created, [])
            self.assertEqual(engine.pending_cast_spell, "Dooming Darkness")
            self.assertEqual(engine.active_timers, {})

            created = engine.process_line(
                "a hill giant is engulfed in darkness.",
                t0 + timedelta(seconds=4.0),
            )
            self.assertEqual([timer.name for timer in created], ["Dooming Darkness"])
            self.assertEqual(len(engine.active_timers), 1)
            timer = next(iter(engine.active_timers.values()))
            self.assertEqual(timer.name, "Dooming Darkness")
            self.assertEqual(timer.target, "a hill giant")
            self.assertIsNone(engine.pending_cast_spell)

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

    def test_generic_wear_off_messages_remove_early_broken_spells(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        fear = SpellDef(
            name="Fear",
            duration_ticks=25,
            duration_seconds=150.0,
            category="mez",
            dot_type=None,
            cast_time_sec=3.0,
        )
        roots = SpellDef(
            name="Paralyzing Roots",
            duration_ticks=30,
            duration_seconds=180.0,
            category="root",
            dot_type=None,
            cast_time_sec=2.5,
        )
        self.engine._add_spell_timer(fear, "a spectre", t0)
        self.engine._add_spell_timer(roots, "Ualkic Fe'Dhar", t0)

        # These messages should remove timers immediately, even without a final
        # period, because fear/root effects can break before their full duration.
        self.engine.process_line(
            "your fear spell has worn off",
            t0 + timedelta(seconds=10),
        )
        self.assertNotIn("spell:fear::a spectre", self.engine.active_timers)
        self.assertIn("spell:paralyzing roots::ualkic fe'dhar", self.engine.active_timers)

        self.engine.process_line(
            "Your Paralyzing Roots spell has worn off..",
            t0 + timedelta(seconds=12),
        )
        self.assertEqual(self.engine.get_sorted_dots(), [])
        self.assertEqual(self.engine.active_timers, {})

    def test_tick_can_advance_respawns_while_other_timers_are_paused(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        scourge = SPELL_DB.lookup_by_name("Scourge")
        self.assertIsNotNone(scourge)
        dot_timer = self.engine._add_spell_timer(scourge, "a hill giant", t0)
        self.assertIsNotNone(dot_timer)
        self.engine.add_respawn_timer("a hill giant", "Lower Guk", created_at=t0)
        respawn_timer = self.engine.active_timers["respawn_a hill giant"]
        dot_before = dot_timer.remaining_seconds
        respawn_before = respawn_timer.remaining_seconds

        self.engine.tick(5.0, categories=("respawn",))

        self.assertEqual(dot_timer.remaining_seconds, dot_before)
        self.assertEqual(respawn_timer.remaining_seconds, respawn_before - 5.0)

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
        # A differently-cased previous respawn countdown should be refreshed,
        # not left beside the new one.
        self.engine.add_respawn_timer("a hill giant", "Old Zone")

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
        respawn_timers = [
            timer for timer in remaining
            if timer.category == "respawn" and self.engine._normalize_mob_name(timer.name) == "hill giant"
        ]
        self.assertEqual(len(respawn_timers), 1)
        self.assertEqual(respawn_timers[0].name, "A HILL GIANT")
        self.assertEqual(self.engine.current_target, "Unknown Target")
        self.assertIsNone(self.engine.pending_cast_spell)
        self.assertIsNone(self.engine.pending_cast_time)


if __name__ == "__main__":
    unittest.main()
