"""Comprehensive Project 1999 EverQuest spell database with special focus on Level 60 Necromancer."""

import re
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
    # Raw spells_us.txt duration inputs. When set, the real duration depends on the
    # caster's level; duration_seconds holds the level-60 value for compatibility.
    duration_formula: Optional[int] = None
    duration_value: int = 0
    # Spell recast (reuse) time from spells_us.txt field 15, e.g. Harvest = 600 s.
    recast_seconds: float = 0.0

    def duration_at(self, level: int) -> float:
        """Duration in seconds when cast by a character of the given level."""
        if self.duration_formula is None:
            return self.duration_seconds
        ticks = buff_duration_ticks(self.duration_formula, self.duration_value, level)
        return max(6.0, ticks * 6.0)


def buff_duration_ticks(formula: int, value: int, level: int) -> int:
    """Buff duration in 6-second ticks for a caster of ``level``.

    These are the same per-formula rules the loader always used; the only change
    is that ``level`` is the caster's real level instead of a hard-coded 60, so
    level-scaled buffs (formulas 1/6-11) are correct for characters below 60.
    At level 60 every result is identical to the previous behaviour, which was
    cross-checked against landing->fade pairs measured in real P99 logs.
    Formulas 2-5, 12 and >=200 keep their prior fixed handling until they can be
    verified the same way.
    """
    if formula == 0:
        return value
    if formula in (1, 6):
        return min((level + 1) // 2, value) if value > 0 else (level + 1) // 2
    if formula == 2:
        return value if value > 0 else level
    if formula == 3:
        return value
    if formula == 4:
        return min(50, level)
    if formula == 5:
        return 3 if value <= 0 else value
    if formula == 7:
        return min(level, value) if value > 0 else level
    if formula == 8:
        return min(level + 10, value) if value > 0 else level + 10
    if formula == 9:
        return min(level * 2 + 10, value) if value > 0 else level * 2 + 10
    if formula == 10:
        return min(level * 3 + 10, value) if value > 0 else level * 3 + 10
    if formula == 11:
        return min(level * 30 + 90, value) if value > 0 else level * 30 + 90
    if formula == 12:
        return value if value > 0 else 9999
    if formula == 50:
        return 72000
    return value if value > 0 else 10


_TOKEN_RE = re.compile(r"[a-z0-9`']+")


class _SubstringIndex:
    """Find which keys of a pattern dict occur as substrings of a message, fast.

    Exactly equivalent to ``[p for p in d if p in msg]`` (in dict order), but
    instead of testing all ~4,000 spell phrases on every log line it only tests
    phrases whose rarest *interior* word appears in the message. An interior word
    is bounded by non-word characters inside the phrase, so it must also appear
    as a whole word in any message containing the phrase. Phrases with no
    interior word are always tested. The index rebuilds when the dict changes
    size, which keeps it correct when tests patch the dict in place.
    """

    def __init__(self, mapping: Dict[str, object]):
        self._mapping = mapping
        self._built_len = -1
        self._by_token: Dict[str, List[str]] = {}
        self._always: List[str] = []
        self._order: Dict[str, int] = {}

    def _build(self) -> None:
        keys = list(self._mapping.keys())
        interior: Dict[str, List[str]] = {}
        freq: Dict[str, int] = {}
        for key in keys:
            toks = [
                m.group(0)
                for m in _TOKEN_RE.finditer(key)
                if m.start() > 0 and m.end() < len(key)
            ]
            interior[key] = toks
            for t in set(toks):
                freq[t] = freq.get(t, 0) + 1
        self._by_token = {}
        self._always = []
        for key, toks in interior.items():
            if toks:
                rarest = min(toks, key=lambda t: (freq[t], -len(t)))
                self._by_token.setdefault(rarest, []).append(key)
            else:
                self._always.append(key)
        self._order = {k: i for i, k in enumerate(keys)}
        self._built_len = len(keys)

    def matches(self, msg_low: str) -> List[str]:
        if self._built_len != len(self._mapping):
            self._build()
        cands = set(self._always)
        for tok in set(_TOKEN_RE.findall(msg_low)):
            cands.update(self._by_token.get(tok, ()))
        hits = [k for k in cands if k in self._mapping and k in msg_low]
        hits.sort(key=lambda k: self._order.get(k, 1 << 30))
        return hits


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


# Recasts at least this long get their own cooldown timer (Harvest = 600 s).
RECAST_TIMER_MIN_SEC = 60.0


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
        # Spells whose recast is long enough to deserve a cooldown timer.
        self.recast_spells: Dict[str, SpellDef] = {}
        self._on_you_index = _SubstringIndex(self.spells_by_on_you)
        self._on_other_index = _SubstringIndex(self.spells_by_on_other)
        self._wear_off_index = _SubstringIndex(self.spells_by_wear_off)
        self._known_landings = [
            (p, p.strip().casefold().rstrip(" .!?"), s) for p, s in KNOWN_BUFF_LANDINGS.items()
        ]

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

                    # ── Recast / reuse time (field 15, milliseconds) ──
                    try:
                        recast_sec = int(parts[15]) / 1000.0
                    except (ValueError, IndexError):
                        recast_sec = 0.0

                    if dur_val <= 0 and dur_formula == 0:
                        # No buff duration. Keep it only as a cooldown source
                        # (e.g. Harvest: 10-minute recast, instant effect).
                        if recast_sec >= RECAST_TIMER_MIN_SEC and name.casefold() not in self.recast_spells:
                            self.recast_spells[name.casefold()] = SpellDef(
                                name=name, duration_ticks=0, duration_seconds=0.0,
                                category="cooldown", dot_type=None,
                                cast_time_sec=cast_time_sec,
                                cast_on_you=on_you or None, cast_on_other=on_other or None,
                                color="#FFC857", recast_seconds=recast_sec,
                            )
                        continue

                    # Level-60 value for the legacy duration_seconds field; the
                    # timer engine calls duration_at(caster_level) for the real one.
                    ticks = buff_duration_ticks(dur_formula, dur_val, 60)
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
                        duration_formula=dur_formula,
                        duration_value=dur_val,
                        recast_seconds=recast_sec,
                    )
                    if recast_sec >= RECAST_TIMER_MIN_SEC and name.casefold() not in self.recast_spells:
                        self.recast_spells[name.casefold()] = sdef

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
        found = self._landing_candidates(
            message, landing_map, attribute, skip_bond_of_death=skip_bond_of_death
        )
        if not found:
            return None
        best, candidates = found
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

    def landing_candidates_on_other(self, message: str) -> List[SpellDef]:
        """Every spell whose best-matching cast_on_other phrase occurs in message.

        Unlike lookup_by_cast_on_other this does not give up on shared landing
        text, so the timer engine can pick the spell that was actually cast.
        """
        found = self._landing_candidates(
            message, self.spells_by_on_other, "cast_on_other", skip_bond_of_death=True
        )
        return list(found[1].values()) if found else []

    def _index_for(self, landing_map: Dict[str, SpellDef]) -> "_SubstringIndex":
        if landing_map is self.spells_by_on_you:
            return self._on_you_index
        if landing_map is self.spells_by_on_other:
            return self._on_other_index
        return _SubstringIndex(landing_map)

    def _landing_candidates(
        self,
        message: str,
        landing_map: Dict[str, SpellDef],
        attribute: str,
        *,
        skip_bond_of_death: bool = False,
    ) -> Optional[Tuple[List[Tuple[str, SpellDef]], Dict[str, SpellDef]]]:
        msg_low = message.strip().casefold()
        matches = [
            (pattern, landing_map[pattern])
            for pattern in self._index_for(landing_map).matches(msg_low)
            if not (
                skip_bond_of_death
                and landing_map[pattern].name.casefold() == "bond of death"
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
        return best, candidates

    def lookup_by_cast_on_you(self, message: str) -> Optional[SpellDef]:
        msg_low = message.strip().casefold()

        # Curated self-buff landing text is authoritative. Local spells_us.txt
        # can contain multiple definitions with the same flavor message, but
        # known entries such as "Your feet feel quick." must still create the
        # expected personal timer rather than disappearing as ambiguous.
        # Some log sources omit the final punctuation. Normalize only the
        # trailing sentence punctuation so known self-buff landings still match
        # while preserving the phrase itself and avoiding broad fuzzy matching.
        normalized_message = msg_low.rstrip(" .!?")
        known_matches = [
            (pattern, sdef)
            for pattern, norm, sdef in self._known_landings
            if norm in normalized_message
        ]
        if known_matches:
            _, known_sdef = max(known_matches, key=lambda item: len(item[0]))
            return known_sdef

        match = self._lookup_landing_pattern(
            message, self.spells_by_on_you, "cast_on_you"
        )
        return match[1] if match else None

    HOSTILE_CATEGORIES = ("dot", "snare", "root", "mez", "debuff")

    def lookup_debuff_on_you(
        self, message: str
    ) -> Optional[Tuple[str, str, float, List[str]]]:
        """A hostile spell (Tashania, slows, roots...) landing on the player.

        Returns (landing_key, display_name, duration_seconds, fade_messages), or None.
        Mobs share landing text across spell families (Tashania/Tashanian/Howl of
        Tashan all print "You hear the barking of Tashania."), so: a candidate
        named in the message wins; otherwise the longest candidate duration is
        used as an upper bound. The timer is removed by any candidate's fade text,
        so it never outlives the real debuff.
        """
        found = self._landing_candidates(message, self.spells_by_on_you, "cast_on_you")
        if not found:
            return None
        best, candidates = found
        hostile = [
            c for c in candidates.values()
            if c.category in self.HOSTILE_CATEGORIES and c.duration_seconds > 0
        ]
        # Shared text can also belong to buffs ("You are now a wolf." is seven
        # wolf-form buffs and one odd hostile entry): only call it a debuff when
        # hostile spells clearly own the line.
        if not hostile or len(hostile) <= len(candidates) - len(hostile):
            return None
        msg_low = message.casefold()
        named = [c for c in hostile if c.name.casefold() in msg_low]
        owner = best[0][1] if best[0][1] in hostile else hostile[0]
        if named:
            chosen = max(named, key=lambda c: len(c.name))
            name, duration = chosen.name, chosen.duration_seconds
        else:
            name = owner.name
            duration = max(c.duration_seconds for c in hostile)
        fades = sorted({c.wear_off.strip() for c in hostile if c.wear_off and c.wear_off.strip()})
        return best[0][0], name, duration, fades

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
        hits = self._wear_off_index.matches(msg_low)
        return self.spells_by_wear_off[hits[0]] if hits else None

    def lookup_recast(self, name: Optional[str]) -> Optional[SpellDef]:
        """Spell definition if its recast is long enough for a cooldown timer."""
        if not name:
            return None
        return self.recast_spells.get(name.strip().casefold())


# Global singleton instance
SPELL_DB = SpellDatabase()


def lookup_necro_spell(spell_name: str) -> Optional[SpellDef]:
    """Case-insensitive spell definition lookup."""
    return SPELL_DB.lookup_by_name(spell_name)
