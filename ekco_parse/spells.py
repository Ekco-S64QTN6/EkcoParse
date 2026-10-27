"""Comprehensive Project 1999 EverQuest spell database with special focus on Level 60 Necromancer."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class SpellDef:
    name: str
    duration_ticks: int
    duration_seconds: float
    category: str              # "dot", "snare", "root", "mez", "buff", "debuff", "pet"
    dot_type: Optional[str]    # "fire", "poison", "disease", "magic", "lifetap"
    cast_time_sec: float
    buff_slot: Optional[str] = None
    cast_on_other: Optional[str] = None
    cast_on_you: Optional[str] = None
    wear_off: Optional[str] = None
    color: str = "#FF2D95"
    recast_warning_seconds: float = 10.0


# P99 spell durations are curated against individual Project 1999 Wiki spell pages.
# Duration references used for this audit include Splurt, the Necromancer Spell Lines,
# Scourge, Plague, Bond of Death, Asystole, Cessation of Cor, Demi Lich, Arch Lich,
# Diamondskin, Clarity, Celerity, Regrowth, Levitate, Symbol of Naltron, and Heroic Bond.
NECRO_SPELLS: Dict[str, SpellDef] = {
    # ── Level 60 & Endgame DoTs ──
    "Splurt": SpellDef(
        name="Splurt",
        duration_ticks=17,
        duration_seconds=102.0,
        category="dot",
        dot_type="magic",
        cast_time_sec=4.0,
        cast_on_other="'s body begins to splurt.",
        cast_on_you="Your body begins to splurt.",
        wear_off="Your body does not splurt.",
        color="#B64CFF",
        recast_warning_seconds=12.0,
    ),
    "Funeral Pyre of Kelador": SpellDef(
        name="Funeral Pyre of Kelador",
        duration_ticks=7,
        duration_seconds=42.0,
        category="dot",
        dot_type="fire",
        cast_time_sec=5.5,
        cast_on_other=" is enveloped in a funeral pyre.",
        cast_on_you="Your skin burns as you are caught in a funeral pyre.",
        wear_off="The funeral pyre ends.",
        color="#FF4040",
        recast_warning_seconds=8.0,
    ),
    "Cascading Darkness": SpellDef(
        name="Cascading Darkness",
        duration_ticks=16,
        duration_seconds=96.0,
        category="snare",
        dot_type="magic",
        cast_time_sec=7.0,
        cast_on_other=" is engulfed in darkness.",
        cast_on_you="You are engulfed in darkness.",
        wear_off="Your Cascading Darkness spell has worn off.",
        color="#00F5FF",
        recast_warning_seconds=12.0,
    ),
    "Dooming Darkness": SpellDef(
        name="Dooming Darkness",
        duration_ticks=16,
        duration_seconds=96.0,
        category="snare",
        dot_type="magic",
        cast_time_sec=4.0,
        cast_on_other=" is engulfed in darkness.",
        cast_on_you="You are engulfed in darkness.",
        wear_off="Your Dooming Darkness spell has worn off.",
        color="#00F5FF",
        recast_warning_seconds=12.0,
    ),
    "Cessation of Cor": SpellDef(
        name="Cessation of Cor",
        duration_ticks=10,
        duration_seconds=60.0,
        category="dot",
        dot_type="magic",
        cast_time_sec=5.0,
        cast_on_other="'s blood stills within their veins.",
        cast_on_you="The blood stops flowing in your veins.",
        wear_off="Your blood resumes movement.",
        color="#B64CFF",
        recast_warning_seconds=10.0,
    ),
    "Asystole": SpellDef(
        name="Asystole",
        duration_ticks=10,
        duration_seconds=60.0,
        category="dot",
        dot_type="disease",
        cast_time_sec=6.1,
        cast_on_other=" clutches their chest.",
        cast_on_you="Your heart stops.",
        wear_off="Your heartbeat resumes.",
        color="#59FF8E",
        recast_warning_seconds=10.0,
    ),
    "Envenomed Bolt": SpellDef(
        name="Envenomed Bolt",
        duration_ticks=8,
        duration_seconds=48.0,
        category="dot",
        dot_type="poison",
        cast_time_sec=6.1,
        cast_on_other=" has been poisoned.",
        cast_on_you="You have been poisoned.",
        wear_off="The poison has run its course.",
        color="#59FF8E",
        recast_warning_seconds=10.0,
    ),
    "Boil Blood": SpellDef(
        name="Boil Blood",
        duration_ticks=21,
        duration_seconds=126.0,
        category="dot",
        dot_type="fire",
        cast_time_sec=4.0,
        cast_on_other="'s blood boils.",
        cast_on_you="Your blood boils.",
        wear_off="Your blood cools.",
        color="#FFC857",
        recast_warning_seconds=8.0,
    ),
    "Ignite Blood": SpellDef(
        name="Ignite Blood",
        duration_ticks=21,
        duration_seconds=126.0,
        category="dot",
        dot_type="fire",
        cast_time_sec=4.0,
        cast_on_other="'s blood ignites.",
        cast_on_you="Your blood ignites.",
        wear_off="Your blood cools.",
        color="#FFC857",
        recast_warning_seconds=8.0,
    ),
    "Plague": SpellDef(
        name="Plague",
        duration_ticks=22,
        duration_seconds=132.0,
        category="dot",
        dot_type="disease",
        cast_time_sec=6.1,
        cast_on_other=" sweats and shivers, looking feverish.",
        cast_on_you="You feel feverish.",
        wear_off="Your fever has broken.",
        color="#59FF8E",
        recast_warning_seconds=12.0,
    ),
    "Scourge": SpellDef(
        name="Scourge",
        duration_ticks=21,
        duration_seconds=126.0,
        category="dot",
        dot_type="disease",
        cast_time_sec=6.1,
        cast_on_other=" gasps as black boils appear.",
        cast_on_you="Black boils appear on your skin.",
        wear_off="Your skin clears.",
        color="#59FF8E",
        recast_warning_seconds=10.0,
    ),
    "Bond of Death": SpellDef(
        name="Bond of Death",
        duration_ticks=9,
        duration_seconds=54.0,
        category="dot",
        dot_type="lifetap",
        cast_time_sec=7.0,
        cast_on_other=" staggers.",
        cast_on_you="You feel your lifeforce drain away.",
        wear_off="The bond fades.",
        color="#FF2D95",
        recast_warning_seconds=6.0,
    ),
    "Defoliation": SpellDef(
        name="Defoliation",
        duration_ticks=0,
        duration_seconds=0.0,
        category="dot",
        dot_type="magic",
        cast_time_sec=4.0,
        cast_on_other=" wilts.",
        cast_on_you=None,
        wear_off="You stop withering.",
        color="#FFC857",
        recast_warning_seconds=6.0,
    ),

    # ── Crowd Control & Roots ──
    "Paralyzing Earth": SpellDef(
        name="Paralyzing Earth",
        duration_ticks=30,
        duration_seconds=180.0,
        category="root",
        dot_type=None,
        cast_time_sec=2.5,
        cast_on_other="'s feet adhere to the ground.",
        cast_on_you="Your feet adhere to the ground.",
        wear_off="Your feet come free.",
        color="#00F5FF",
        recast_warning_seconds=15.0,
    ),
    "Fetter": SpellDef(
        name="Fetter",
        duration_ticks=30,
        duration_seconds=180.0,
        category="root",
        dot_type=None,
        cast_time_sec=2.5,
        cast_on_other="'s feet adhere to the ground.",
        cast_on_you="Your feet adhere to the ground.",
        wear_off="Your feet come free.",
        color="#00F5FF",
        recast_warning_seconds=15.0,
    ),
    "Enstill": SpellDef(
        name="Enstill",
        duration_ticks=16,
        duration_seconds=96.0,
        category="root",
        dot_type=None,
        cast_time_sec=2.5,
        cast_on_other=" adheres to the ground.",
        cast_on_you="You adhere to the ground.",
        wear_off="You can move again.",
        color="#00F5FF",
        recast_warning_seconds=10.0,
    ),
    "Root": SpellDef(
        name="Root",
        duration_ticks=8,
        duration_seconds=48.0,
        category="root",
        dot_type=None,
        cast_time_sec=2.0,
        cast_on_other=" stops moving.",
        cast_on_you="You stick to the ground.",
        wear_off="You can move again.",
        color="#00F5FF",
        recast_warning_seconds=8.0,
    ),
    "Screaming Terror": SpellDef(
        name="Screaming Terror",
        duration_ticks=3,
        duration_seconds=18.0,
        category="mez",
        dot_type=None,
        cast_time_sec=2.6,
        cast_on_other=" begins to scream.",
        cast_on_you="You begin to scream.",
        wear_off="You stop screaming.",
        color="#FF4040",
        recast_warning_seconds=5.0,
    ),

    # ── Lich, Buffs & Pets ──
    # Project 1999 Wiki lists Arch Lich as 19 minutes (not the longer live-era value).
    "Arch Lich": SpellDef(
        name="Arch Lich",
        buff_slot="lich",
        duration_ticks=190,
        duration_seconds=1140.0,
        category="buff",
        dot_type=None,
        cast_time_sec=2.0,
        cast_on_other="'s skin peels away.",
        cast_on_you="You feel the skin peel from your bones.",
        wear_off="Your flesh returns.",
        color="#B64CFF",
        recast_warning_seconds=30.0,
    ),
    # Project 1999 Wiki lists Demi Lich as 19 minutes (190 six-second ticks).
    "Demi Lich": SpellDef(
        name="Demi Lich",
        buff_slot="lich",
        duration_ticks=190,
        duration_seconds=1140.0,
        category="buff",
        dot_type=None,
        cast_time_sec=2.0,
        cast_on_other="'s skin peels away.",
        cast_on_you="You feel the skin peel from your bones.",
        wear_off="Your flesh returns.",
        color="#B64CFF",
        recast_warning_seconds=60.0,
    ),
    "Dead Man Floating": SpellDef(
        name="Dead Man Floating",
        buff_slot="levitate",
        duration_ticks=720,
        duration_seconds=4320.0,
        category="buff",
        dot_type=None,
        cast_time_sec=6.0,
        cast_on_other=" looks dead.",
        cast_on_you="You become like the dead.",
        wear_off="You return to life.",
        color="#00F5FF",
        recast_warning_seconds=60.0,
    ),
    "Shield of the Undertaker": SpellDef(
        name="Shield of the Undertaker",
        buff_slot="shielding",
        duration_ticks=360,
        duration_seconds=2160.0,
        category="buff",
        dot_type=None,
        cast_time_sec=5.0,
        cast_on_other=" is protected by the undertaker.",
        cast_on_you="You are protected by the undertaker.",
        wear_off="The protective shield fades.",
        color="#59FF8E",
        recast_warning_seconds=30.0,
    ),
    "Diamondskin": SpellDef(
        name="Diamondskin",
        buff_slot="rune",
        duration_ticks=900,
        duration_seconds=5400.0,
        category="buff",
        dot_type=None,
        cast_time_sec=5.0,
        cast_on_other="'s skin turns diamond-hard.",
        cast_on_you="Your skin turns diamond-hard.",
        wear_off="Your skin returns to normal.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "Manaskin": SpellDef(
        name="Manaskin",
        buff_slot="rune",
        duration_ticks=1200,
        duration_seconds=7200.0,
        category="buff",
        dot_type=None,
        cast_time_sec=5.0,
        cast_on_other="`s skin gleams with an incandescent glow.",
        cast_on_you="Your skin gleams with an incandescent glow.",
        wear_off="Your skin returns to normal.",
        color="#00F5FF",
        recast_warning_seconds=60.0,
    ),
    "Shield of the Magi": SpellDef(
        name="Shield of the Magi",
        buff_slot="shielding",
        duration_ticks=900,
        duration_seconds=5400.0,
        category="buff",
        dot_type=None,
        cast_time_sec=12.0,
        cast_on_other=None,
        cast_on_you="You feel armored.",
        wear_off="Your shielding fades..",
        color="#59FF8E",
        recast_warning_seconds=60.0,
    ),
}

# ── General Buff Database for Raid/Group Buffs (Cleric, Enchanter, Shaman, Druid) ──
KNOWN_BUFF_LANDINGS: Dict[str, SpellDef] = {
    "you feel armored.": NECRO_SPELLS["Shield of the Magi"],
    "your skin gleams with an incandescent glow.": NECRO_SPELLS["Manaskin"],
    "you become like the dead.": NECRO_SPELLS["Dead Man Floating"],
    "you feel the skin peel from your bones.": NECRO_SPELLS["Demi Lich"],
    "your body transforms into a skeletal form.": NECRO_SPELLS["Demi Lich"],
    "your skin turns diamond-hard.": NECRO_SPELLS["Diamondskin"],
    "you are protected by the undertaker.": NECRO_SPELLS["Shield of the Undertaker"],
    "your feet feel quick.": SpellDef(
        name="JourneymanBoots",
        duration_ticks=180,
        duration_seconds=1080.0,
        category="buff",
        dot_type=None,
        cast_time_sec=0.0,
        buff_slot="sow",
        cast_on_you="Your feet feel quick.",
        wear_off="Your feet slow down.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "your feet feel quick": SpellDef(
        name="JourneymanBoots",
        duration_ticks=180,
        duration_seconds=1080.0,
        category="buff",
        dot_type=None,
        cast_time_sec=0.0,
        buff_slot="sow",
        cast_on_you="Your feet feel quick.",
        wear_off="Your feet slow down.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "you feet move faster": SpellDef(
        name="JourneymanBoots",
        duration_ticks=180,
        duration_seconds=1080.0,
        category="buff",
        dot_type=None,
        cast_time_sec=0.0,
        buff_slot="sow",
        cast_on_you="Your feet feel quick.",
        wear_off="Your feet slow down.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "your feet move faster": SpellDef(
        name="JourneymanBoots",
        duration_ticks=180,
        duration_seconds=1080.0,
        category="buff",
        dot_type=None,
        cast_time_sec=0.0,
        buff_slot="sow",
        cast_on_you="Your feet feel quick.",
        wear_off="Your feet slow down.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "your feet move faster.": SpellDef(
        name="JourneymanBoots",
        duration_ticks=180,
        duration_seconds=1080.0,
        category="buff",
        dot_type=None,
        cast_time_sec=0.0,
        buff_slot="sow",
        cast_on_you="Your feet feel quick.",
        wear_off="Your feet slow down.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "you are filled with the power of aegolism.": SpellDef(
        name="Aegolism",
        duration_ticks=1500,
        duration_seconds=9000.0,
        category="buff",
        dot_type=None,
        cast_time_sec=6.0,
        buff_slot="aego",
        cast_on_you="You are filled with the power of Aegolism.",
        wear_off="Your aegolism fades.",
        color="#FFC857",
        recast_warning_seconds=120.0,
    ),
    "you feel a warm glow.": SpellDef(
        name="Blessing of Aegolism",
        duration_ticks=1500,
        duration_seconds=9000.0,
        category="buff",
        dot_type=None,
        cast_time_sec=12.0,
        buff_slot="aego",
        cast_on_you="You feel a warm glow.",
        wear_off="Your warm glow fades.",
        color="#FFC857",
        recast_warning_seconds=120.0,
    ),
    "you feel very heroic.": SpellDef(
        name="Heroic Bond",
        duration_ticks=720,
        duration_seconds=4320.0,
        category="buff",
        dot_type=None,
        cast_time_sec=6.0,
        buff_slot="heroism",
        cast_on_you="You feel very heroic.",
        wear_off="You feel less heroic.",
        color="#FFC857",
        recast_warning_seconds=60.0,
    ),
    "you feel a holy aura surround you.": SpellDef(
        name="Symbol of Naltron",
        duration_ticks=540,
        duration_seconds=3240.0,
        category="buff",
        dot_type=None,
        cast_time_sec=7.0,
        buff_slot="symbol",
        cast_on_you="You feel a holy aura surround you.",
        wear_off="The holy aura fades.",
        color="#00F5FF",
        recast_warning_seconds=60.0,
    ),
    "you feel focused.": SpellDef(
        name="Focus of Spirit",
        duration_ticks=1000,
        duration_seconds=6000.0,
        category="buff",
        dot_type=None,
        cast_time_sec=6.0,
        buff_slot="focus",
        cast_on_you="You feel focused.",
        wear_off="Your focus fades.",
        color="#59FF8E",
        recast_warning_seconds=60.0,
    ),
    "a soft breeze slips through your mind.": SpellDef(
        name="Clarity II",
        duration_ticks=350,
        duration_seconds=2100.0,
        category="buff",
        dot_type=None,
        cast_time_sec=4.0,
        buff_slot="clarity",
        cast_on_you="A soft breeze slips through your mind.",
        wear_off="The soft breeze fades.",
        color="#39FFE2",
        recast_warning_seconds=60.0,
    ),
    "you feel your spirit quicken.": SpellDef(
        name="Clarity II",
        duration_ticks=350,
        duration_seconds=2100.0,
        category="buff",
        dot_type=None,
        cast_time_sec=4.0,
        buff_slot="clarity",
        cast_on_you="You feel your spirit quicken.",
        wear_off="Your mind feels less clear.",
        color="#39FFE2",
        recast_warning_seconds=60.0,
    ),
    "you feel your pulse quicken.": SpellDef(
        name="Clarity",
        duration_ticks=270,
        duration_seconds=1620.0,
        category="buff",
        dot_type=None,
        cast_time_sec=4.0,
        buff_slot="clarity",
        cast_on_you="You feel your pulse quicken.",
        wear_off="Your mind feels less clear.",
        color="#39FFE2",
        recast_warning_seconds=60.0,
    ),
    "you feel your mind expand.": SpellDef(
        name="Koadic's Endless Intellect",
        duration_ticks=1500,
        duration_seconds=9000.0,
        category="buff",
        dot_type=None,
        cast_time_sec=8.0,
        buff_slot="clarity",
        cast_on_you="You feel your mind expand.",
        wear_off="Your mind feels less clear.",
        color="#39FFE2",
        recast_warning_seconds=120.0,
    ),
    "your body quickens.": SpellDef(
        name="Celerity",
        duration_ticks=160,
        duration_seconds=960.0,
        category="buff",
        dot_type=None,
        cast_time_sec=3.0,
        buff_slot="haste",
        cast_on_you="Your body quickens.",
        wear_off="Your body slows down.",
        color="#FFC857",
        recast_warning_seconds=30.0,
    ),
    "you feel your body regenerating.": SpellDef(
        name="Regrowth",
        duration_ticks=190,
        duration_seconds=1140.0,
        category="buff",
        dot_type=None,
        cast_time_sec=5.0,
        buff_slot="regen",
        cast_on_you="You feel your body regenerating.",
        wear_off="You stop regenerating.",
        color="#59FF8E",
        recast_warning_seconds=30.0,
    ),
    "you feel the spirit of the wolf enter you.": SpellDef(
        name="Spirit of Wolf",
        duration_ticks=360,
        duration_seconds=2160.0,
        category="buff",
        dot_type=None,
        cast_time_sec=5.0,
        buff_slot="sow",
        cast_on_you="You feel the spirit of the wolf enter you.",
        wear_off="Your feet slow down.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "you feel your skin harden.": SpellDef(
        name="Skin like Nature",
        duration_ticks=1200,
        duration_seconds=7200.0,
        category="buff",
        dot_type=None,
        cast_time_sec=7.0,
        buff_slot="skin",
        cast_on_you="You feel your skin harden.",
        wear_off="Your skin returns to normal.",
        color="#59FF8E",
        recast_warning_seconds=60.0,
    ),
    "you feel yourself floating.": SpellDef(
        name="Levitate",
        duration_ticks=190,
        duration_seconds=1140.0,
        category="buff",
        dot_type=None,
        cast_time_sec=3.0,
        buff_slot="levitate",
        cast_on_you="You feel yourself floating.",
        wear_off="You land gently on the ground.",
        color="#00F5FF",
        recast_warning_seconds=30.0,
    ),
    "you feel your body become translucent.": SpellDef(
        name="Invisibility",
        duration_ticks=100,
        duration_seconds=600.0,
        category="buff",
        dot_type=None,
        cast_time_sec=3.0,
        buff_slot="invis",
        cast_on_you="You feel your body become translucent.",
        wear_off="You feel yourself appear.",
        color="#39FFE2",
        recast_warning_seconds=20.0,
    ),
    "you feel like someone is watching you.": SpellDef(
        name="See Invisible",
        duration_ticks=270,
        duration_seconds=1620.0,
        category="buff",
        dot_type=None,
        cast_time_sec=3.0,
        buff_slot="see_invis",
        cast_on_you="You feel like someone is watching you.",
        wear_off="You feel like someone has stopped watching you.",
        color="#39FFE2",
        recast_warning_seconds=30.0,
    ),
}


class SpellDatabase:
    """Universal Project 1999 spell catalog, reading spells_us.txt with full fallback."""

    def __init__(self, eq_dir: Optional[str] = "/home/ekco/Games/Project1999"):
        # The lookup API case-folds names. Store curated P99 entries under the same
        # normalized keys so local spells_us.txt data cannot replace these durations.
        self.spells_by_name: Dict[str, SpellDef] = {
            name.casefold(): sdef for name, sdef in NECRO_SPELLS.items()
        }
        self.spells_by_on_you: Dict[str, SpellDef] = dict(KNOWN_BUFF_LANDINGS)
        self.spells_by_wear_off: Dict[str, str] = {}
        self.spells_by_on_other: Dict[str, SpellDef] = {}

        for sdef in NECRO_SPELLS.values():
            if sdef.cast_on_other:
                self.spells_by_on_other[sdef.cast_on_other.lower()] = sdef
            if sdef.wear_off:
                self.spells_by_wear_off[sdef.wear_off.lower()] = sdef.name

        for sdef in KNOWN_BUFF_LANDINGS.values():
            self.spells_by_name[sdef.name.lower()] = sdef
            if sdef.wear_off:
                self.spells_by_wear_off[sdef.wear_off.lower()] = sdef.name

        if eq_dir:
            self._load_spells_us(eq_dir)

    def _load_spells_us(self, eq_dir: str) -> None:
        """Parse spells_us.txt using verified EQEmu field layout (spdat.h).

        Field indices (caret-delimited):
          0: spell_id        1: name           2: player_1
          3: teleport_zone   4: you_cast       5: other_casts
          6: cast_on_you     7: cast_on_other  8: spell_fades
          9: range           13: cast_time (ms)
          16: duration_formula  17: duration_value (ticks)
          83: goodEffect (1 = beneficial, 0 = detrimental)
        """
        path = Path(eq_dir) / "spells_us.txt"
        if not path.exists():
            return

        try:
            with open(path, "r", encoding="latin-1", errors="replace") as f:
                for line in f:
                    parts = line.strip().split("^")
                    if len(parts) < 84:
                        continue
                    name = parts[1].strip()
                    if not name:
                        continue
                    on_you = parts[6].strip()
                    on_other = parts[7].strip()
                    wear_off = parts[8].strip()

                    # ── Read beneficial flag from field 83 ──
                    try:
                        is_beneficial = (int(parts[83]) == 1)
                    except (ValueError, IndexError):
                        is_beneficial = False

                    # ── Cast time (field 13, in milliseconds) ──
                    try:
                        cast_time_ms = int(parts[13])
                        cast_time_sec = cast_time_ms / 1000.0
                    except (ValueError, IndexError):
                        cast_time_sec = 4.0

                    # ── Duration calculation (EQEmu formulas 0-12 at level 60) ──
                    try:
                        dur_formula = int(parts[16])
                        dur_val = int(parts[17])
                    except (ValueError, IndexError):
                        dur_formula = 0
                        dur_val = 0

                    if dur_val <= 0 and dur_formula == 0:
                        continue

                    level = 60
                    ticks = dur_val

                    if dur_formula == 0:
                        ticks = dur_val
                    elif dur_formula in (1, 6):
                        # min(ceil(level/2), value)
                        ticks = min((level + 1) // 2, dur_val) if dur_val > 0 else (level + 1) // 2
                    elif dur_formula == 2:
                        # (value/5*3) or scaled: typically just dur_val
                        ticks = dur_val if dur_val > 0 else level
                    elif dur_formula == 3:
                        # Fixed duration: value ticks exactly
                        ticks = dur_val
                    elif dur_formula == 4:
                        # min(50, level)
                        ticks = min(50, level)
                    elif dur_formula == 5:
                        # 3 ticks (18 seconds — stun/mezzes)
                        ticks = 3 if dur_val <= 0 else dur_val
                    elif dur_formula == 7:
                        # min(level, value)
                        ticks = min(level, dur_val) if dur_val > 0 else level
                    elif dur_formula == 8:
                        # min(level + 10, value)
                        ticks = min(level + 10, dur_val) if dur_val > 0 else level + 10
                    elif dur_formula == 9:
                        # min(level*2 + 10, value)
                        ticks = min(level * 2 + 10, dur_val) if dur_val > 0 else level * 2 + 10
                    elif dur_formula == 10:
                        # min(level*3 + 10, value)  — long-duration buffs like Demi Lich
                        ticks = min(level * 3 + 10, dur_val) if dur_val > 0 else level * 3 + 10
                    elif dur_formula == 11:
                        # min(level*30 + 90, value) — very long buffs
                        ticks = min(level * 30 + 90, dur_val) if dur_val > 0 else level * 30 + 90
                    elif dur_formula == 12:
                        # Permanent until cancelled
                        ticks = dur_val if dur_val > 0 else 9999
                    elif dur_formula == 50:
                        # Permanent
                        ticks = 72000
                    else:
                        ticks = dur_val if dur_val > 0 else 10

                    dur_seconds = max(6.0, ticks * 6.0)

                    # ── Determine category using beneficial flag + name heuristics ──
                    name_low = name.lower()
                    # spells_us.txt field 9 is range, not target type.
                    # The target type field is near the end of the legacy spell row.
                    target_type = parts[98] if len(parts) > 98 else ""
                    if target_type == "14" or "augmentation of death" in name_low or "savage spirit" in name_low:
                        category = "pet_buff"
                        color = "#FFC857"
                    elif is_beneficial:
                        category = "buff"
                        color = "#59FF8E"
                    elif "darkness" in name_low or "snare" in name_low:
                        category = "snare"
                        color = "#00F5FF"
                    elif "root" in name_low or "fetter" in name_low or "enstill" in name_low:
                        category = "root"
                        color = "#00F5FF"
                    elif "terror" in name_low or "fear" in name_low:
                        category = "mez"
                        color = "#FF4040"
                    else:
                        category = "dot"
                        color = "#FF2D95"

                    # ── Buff slot assignment for slot-based replacement ──
                    slot = None
                    if any(k in name_low for k in ["lich", "call of bones", "allure of death"]):
                        slot = "lich"
                        color = "#B64CFF"
                    elif any(k in name_low for k in ["manaskin", "diamondskin", "steelskin", "rune"]):
                        slot = "rune"
                        color = "#00F5FF"
                    elif any(k in name_low for k in ["shield of the magi", "shielding"]):
                        slot = "shielding"
                        color = "#59FF8E"
                    elif any(k in name_low for k in ["dead man floating", "levitate"]):
                        slot = "levitate"
                        color = "#00F5FF"
                    elif any(k in name_low for k in ["aegolism", "aego"]):
                        slot = "aego"
                        color = "#FFC857"
                    elif any(k in name_low for k in ["heroic bond", "heroism"]):
                        slot = "heroism"
                        color = "#FFC857"
                    elif any(k in name_low for k in ["symbol of"]):
                        slot = "symbol"
                        color = "#00F5FF"
                    elif any(k in name_low for k in ["focus of spirit"]):
                        slot = "focus"
                        color = "#59FF8E"
                    elif any(k in name_low for k in ["clarity", "breeze", "koadic"]):
                        slot = "clarity"
                        color = "#39FFE2"
                    elif any(k in name_low for k in ["celerity", "speed of the shissar", "augment"]):
                        slot = "haste"
                        color = "#FFC857"
                    elif any(k in name_low for k in ["regrowth", "chloroplast", "regeneration"]):
                        slot = "regen"
                        color = "#59FF8E"
                    elif any(k in name_low for k in ["spirit of wolf", "pack spirit"]):
                        slot = "sow"
                        color = "#00F5FF"
                    elif any(k in name_low for k in ["skin like nature", "protection of the glades"]):
                        slot = "skin"
                        color = "#59FF8E"

                    sdef = SpellDef(
                        name=name,
                        duration_ticks=ticks,
                        duration_seconds=dur_seconds,
                        category=category,
                        dot_type=None,
                        cast_time_sec=cast_time_sec,
                        buff_slot=slot,
                        cast_on_you=on_you if on_you else None,
                        cast_on_other=on_other if on_other else None,
                        wear_off=wear_off if wear_off else None,
                        color=color,
                    )

                    # Hardcoded NECRO_SPELLS and KNOWN_BUFF_LANDINGS take priority
                    if name.lower() not in self.spells_by_name:
                        self.spells_by_name[name.lower()] = sdef
                    if on_you and on_you.lower() not in self.spells_by_on_you:
                        self.spells_by_on_you[on_you.lower()] = sdef
                    if on_other and on_other.lower() not in self.spells_by_on_other:
                        self.spells_by_on_other[on_other.lower()] = sdef
                    if wear_off and wear_off.lower() not in self.spells_by_wear_off:
                        self.spells_by_wear_off[wear_off.lower()] = name
        except Exception as e:
            pass

    def lookup_by_name(self, name: str) -> Optional[SpellDef]:
        return self.spells_by_name.get(name.strip().lower())

    def _lookup_landing_pattern(
        self,
        message: str,
        landing_map: Dict[str, SpellDef],
        attribute: str,
        *,
        skip_bond_of_death: bool = False,
    ) -> Optional[Tuple[str, SpellDef]]:
        """Find the most-specific landing pattern without guessing on collisions.

        Some P99 spells intentionally share identical landing text. The generic
        lookup maps retain one entry per message for compatibility, so consult
        the name-indexed catalog as well: if different spells own the same best
        pattern, only a pending cast can safely tell us which one landed.
        """
        msg_low = message.strip().casefold()
        matches = [
            (pattern, sdef)
            for pattern, sdef in landing_map.items()
            if pattern in msg_low
            and not (
                skip_bond_of_death
                and sdef.name.casefold() == "bond of death"
            )
        ]
        if not matches:
            return None

        # Prefer a longer phrase over a generic substring; only equal-length
        # best matches can make this line ambiguous.
        longest = max(len(pattern) for pattern, _ in matches)
        best = [
            (pattern, sdef)
            for pattern, sdef in matches
            if len(pattern) == longest
        ]

        candidates: Dict[str, SpellDef] = {}
        for pattern, sdef in best:
            candidates.setdefault(sdef.name.casefold(), sdef)
            for definition in self.spells_by_name.values():
                landing = getattr(definition, attribute, None)
                if landing and landing.strip().casefold() == pattern.strip().casefold():
                    candidates.setdefault(definition.name.casefold(), definition)

        if len(candidates) > 1:
            definitions = list(candidates.values())
            first = definitions[0]
            # Arch Lich and Demi Lich have the same landing line but identical
            # personal-buff timing/slot behavior. Preserve this safe fallback;
            # do not apply it to hostile effects such as fear or darkness spells.
            equivalent_personal_buff = (
                first.category in ("buff", "cooldown", "util")
                and bool(first.buff_slot)
                and all(
                    definition.category == first.category
                    and definition.buff_slot == first.buff_slot
                    and definition.duration_seconds == first.duration_seconds
                    and (definition.wear_off or "").casefold()
                    == (first.wear_off or "").casefold()
                    for definition in definitions
                )
            )
            if not equivalent_personal_buff:
                return None
        return best[0]

    def lookup_by_cast_on_you(self, message: str) -> Optional[SpellDef]:
        msg_low = message.strip().casefold()

        # Curated self-buff landing text is authoritative. Local spells_us.txt
        # can contain multiple definitions with the same flavor message, but
        # known entries such as "Your feet feel quick." must still create the
        # expected personal timer rather than disappearing as ambiguous.
        known_matches = [
            (pattern, sdef)
            for pattern, sdef in KNOWN_BUFF_LANDINGS.items()
            if pattern in msg_low
        ]
        if known_matches:
            _, known_sdef = max(known_matches, key=lambda item: len(item[0]))
            return known_sdef

        match = self._lookup_landing_pattern(
            message, self.spells_by_on_you, "cast_on_you"
        )
        return match[1] if match else None

    def lookup_by_cast_on_other(self, message: str) -> Optional[Tuple[SpellDef, str]]:
        match = self._lookup_landing_pattern(
            message,
            self.spells_by_on_other,
            "cast_on_other",
            skip_bond_of_death=True,
        )
        if not match:
            return None

        pattern, sdef = match
        msg_low = message.casefold()
        idx = msg_low.find(pattern)
        target = message[:idx].strip() if idx > 0 else "Target"
        return sdef, target

    def lookup_wear_off(self, message: str) -> Optional[str]:
        msg_low = message.strip().lower()
        if msg_low in self.spells_by_wear_off:
            return self.spells_by_wear_off[msg_low]
        for pattern, sname in self.spells_by_wear_off.items():
            if pattern in msg_low:
                return sname
        return None


# Global singleton instance
SPELL_DB = SpellDatabase()


def lookup_necro_spell(spell_name: str) -> Optional[SpellDef]:
    """Case-insensitive spell definition lookup."""
    return SPELL_DB.lookup_by_name(spell_name)
