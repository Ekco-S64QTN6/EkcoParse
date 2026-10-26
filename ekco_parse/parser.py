"""EverQuest P99 log parser engine with pre-compiled regex matchers."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ekco_parse.models import CombatAction, HealAction, Location, LogLine, LootRecord


# Regex for timestamp prefix: [Sun Oct 26 12:34:56 2026] Message...
RE_TIMESTAMP = re.compile(
    r"^\[(?P<ts>[A-Za-z]{3}\s+[A-Za-z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4})\]\s+(?P<msg>.*)$"
)

# /loc coordinates: Your Location is 123.45, -678.90, 12.34
RE_LOC = re.compile(
    r"^Your Location is\s+(?P<y>[-\d.]+),\s+(?P<x>[-\d.]+),\s+(?P<z>[-\d.]+)$"
)

# Zone change: You have entered Skyshrine.
RE_ZONE = re.compile(r"^You have entered\s+(?P<zone>.+?)\.?$")

# Zone check via /who: There is 1 player in Skyshrine.
RE_WHO_ZONE = re.compile(r"^There (?:is|are) \d+ players? in (?P<zone>.+?)\.?$", re.IGNORECASE)

# Heading check: You think you are facing North.
RE_HEADING = re.compile(r"^You think you are facing\s+(?P<heading>[A-Za-z]+)\.?$")

# Melee damage dealt on YOU (Tank mitigation)
RE_MELEE_ON_YOU = re.compile(
    r"^(?P<actor>[A-Za-z0-9_`'\s]+?)\s+(?P<verb>slash|slashes|crush|crushes|pierce|pierces|hit|hits|kick|kicks|punch|punches|bite|bites|claw|claws|strike|strikes|bash|bashes|gash|gashes|slice|slices)\s+YOU\s+for\s+(?P<damage>\d+)\s+points? of damage\.(?:\s+\((?P<special>critical|crippling blow)\))?$"
)

# Melee damage dealt general: Actor verb Target for X points of damage.
RE_MELEE_DAMAGE = re.compile(
    r"^(?P<actor>You|Your pet|[A-Za-z0-9_`'\s]+?)\s+(?P<verb>slash|slashes|crush|crushes|pierce|pierces|hit|hits|kick|kicks|punch|punches|bite|bites|claw|claws|strike|strikes|bash|bashes|backstab|backstabs|gash|gashes|slice|slices)\s+(?P<target>.+?)\s+for\s+(?P<damage>\d+)\s+points? of damage\.(?:\s+\((?P<special>critical|crippling blow)\))?$"
)

# Non-melee / spell damage: Target was hit by non-melee for X points of damage.
RE_NON_MELEE_WAS_HIT = re.compile(
    r"^(?P<target>.+?)\s+was\s+(?:hit|pierced|burned|chilled|shocked)\s+by non-melee\s+for\s+(?P<damage>\d+)\s+points? of damage\.$"
)

RE_NON_MELEE_TAKEN_SPELL = re.compile(
    r"^(?P<target>.+?)\s+has taken\s+(?P<damage>\d+)\s+damage from your\s+(?P<spell>.+?)\.$"
)

RE_NON_MELEE_YOU_HIT = re.compile(
    r"^You hit\s+(?P<target>.+?)\s+for\s+(?P<damage>\d+)\s+points? of non-melee damage\.$"
)

RE_NON_MELEE_OTHER_HIT = re.compile(
    r"^(?P<actor>[A-Za-z0-9_`']+?)\s+hit\s+(?P<target>.+?)\s+for\s+(?P<damage>\d+)\s+points? of non-melee damage\.$"
)

# Misses and Defenses
RE_YOU_MISS = re.compile(r"^You try to\s+(?P<verb>\w+)\s+(?P<target>.+?),\s+but miss!$")
RE_ENEMY_MISS_YOU = re.compile(r"^(?P<actor>.+?)\s+tries to\s+(?P<verb>\w+)\s+YOU,\s+but misses!$")
RE_DEFENSE_ON_YOU = re.compile(
    r"^(?P<actor>.+?)\s+tries to\s+(?P<verb>\w+)\s+YOU,\s+but YOU\s+(?P<defense>dodge|parry|block|riposte)!$"
)
RE_DEFENSE_OTHER = re.compile(
    r"^(?P<actor>.+?)\s+tries to\s+(?P<verb>\w+)\s+(?P<target>.+?),\s+but\s+(?P<defender>.+?)\s+(?P<defense>dodges|parries|blocks|ripostes)!$"
)
RE_GENERAL_MISS = re.compile(r"^(?P<actor>.+?)\s+tries to\s+(?P<verb>\w+)\s+(?P<target>.+?),\s+but misses!$")

# Heals
RE_HEAL_ON_YOU = re.compile(r"^You have been healed for\s+(?P<amount>\d+)\s+points? of damage\.$")
RE_YOU_HEAL = re.compile(r"^You healed\s+(?P<recipient>.+?)\s+for\s+(?P<amount>\d+)\s+points? of damage\.$")
RE_OTHER_HEALED_YOU = re.compile(r"^(?P<caster>[A-Za-z0-9_`']+)\s+healed you for\s+(?P<amount>\d+)\s+points? of damage\.$")
RE_OTHER_HEAL_OTHER = re.compile(r"^(?P<caster>[A-Za-z0-9_`']+)\s+healed\s+(?P<recipient>.+?)\s+for\s+(?P<amount>\d+)\s+points? of damage\.$")
RE_HEALED_HIT_POINTS = re.compile(r"^(?P<recipient>.+?)\s+has been healed for\s+(?P<amount>\d+)\s+hit points by\s+(?P<caster>.+?)\.$")

# Spell casts & Resists
RE_YOU_CAST = re.compile(r"^You begin casting\s+(?P<spell>.+?)\.$")
RE_OTHER_CAST = re.compile(r"^(?P<actor>[A-Za-z0-9_`']+)\s+begins casting\s+(?P<spell>.+?)\.$")
RE_SPELL_INTERRUPT = re.compile(r"^Your spell is interrupted\.$")
RE_TARGET_RESIST = re.compile(r"^Your target resisted the\s+(?P<spell>.+?)\s+spell\.$")
RE_MOB_RESIST = re.compile(r"^(?P<target>.+?)\s+resisted your\s+(?P<spell>.+?)\s+spell\.$")

# Deaths & Experience
RE_YOU_SLAY = re.compile(r"^You have slain\s+(?P<mob>.+?)!$")
RE_OTHER_SLAY = re.compile(r"^(?P<mob>.+?)\s+has been slain by\s+(?P<slayer>.+?)!$")
RE_MOB_DIED = re.compile(r"^(?P<mob>.+?)\s+died\.$")
RE_YOU_DIED = re.compile(r"^You have been slain by\s+(?P<killer>.+?)!$")
RE_YOU_DIED_ALT = re.compile(r"^You died\.$")
RE_EXP_GAIN = re.compile(r"^You gain (?:party )?experience!!$")
RE_LOADING = re.compile(r"^LOADING, PLEASE WAIT\.\.\.$")

# Loot
RE_YOU_LOOT = re.compile(r"^--You have looted a\s+(?P<item>.+?)\.--$")
RE_OTHER_LOOT = re.compile(r"^--(?P<looter>[A-Za-z0-9_`']+)\s+has looted a\s+(?P<item>.+?)\.--$")
RE_COIN_LOOT = re.compile(r"^You receive\s+(?P<money>.+?)\s+from the corpse\.$")


class LogParser:
    """Parses raw EverQuest log lines into structured domain events."""

    def __init__(self, character_name: str = "Ekco"):
        self.character_name = character_name

    def parse_line(self, line: str) -> Optional[Tuple[LogLine, Optional[Any]]]:
        """
        Parse raw log line. Returns tuple of (LogLine, EventObject)
        where EventObject can be CombatAction, HealAction, Location, LootRecord, or trigger dict.
        """
        m = RE_TIMESTAMP.match(line)
        if not m:
            return None

        ts_raw = m.group("ts")
        msg = m.group("msg")

        try:
            # EQ format: Sun Oct 26 12:34:56 2026
            dt = datetime.strptime(ts_raw, "%a %b %d %H:%M:%S %Y")
        except ValueError:
            dt = datetime.now()

        log_line = LogLine(
            timestamp_raw=ts_raw,
            timestamp=dt,
            message=msg,
            original_line=line,
        )

        event = self._identify_event(msg, dt)
        return log_line, event

    def _identify_event(self, msg: str, dt: datetime) -> Optional[Any]:
        """Classify message into domain model."""

        # 1. Location (/loc)
        m = RE_LOC.match(msg)
        if m:
            return Location(
                y=float(m.group("y")),
                x=float(m.group("x")),
                z=float(m.group("z")),
                timestamp=dt,
            )

        # 2. Zone change (via entering zone or /who command)
        m = RE_ZONE.match(msg)
        if m:
            return {"type": "zone_change", "zone": m.group("zone").strip()}

        m = RE_WHO_ZONE.match(msg)
        if m:
            return {"type": "zone_change", "zone": m.group("zone").strip()}

        # 3. Heading check
        m = RE_HEADING.match(msg)
        if m:
            return {"type": "heading", "heading": m.group("heading")}

        # 4. Tank Mitigation: Damage taken by YOU
        m = RE_MELEE_ON_YOU.match(msg)
        if m:
            special = m.group("special")
            return CombatAction(
                actor=m.group("actor").strip(),
                target="YOU",
                verb=m.group("verb"),
                damage=int(m.group("damage")),
                is_crit=(special == "critical"),
                is_crippling=(special == "crippling blow"),
                timestamp=dt,
            )

        # 5. Non-melee / Spell damage (check BEFORE general melee to avoid 'was hit' matching melee)
        m = RE_NON_MELEE_WAS_HIT.match(msg)
        if m:
            return CombatAction(
                actor="Non-Melee",
                target=m.group("target").strip(),
                verb="non-melee",
                damage=int(m.group("damage")),
                is_non_melee=True,
                timestamp=dt,
            )

        m = RE_NON_MELEE_TAKEN_SPELL.match(msg)
        if m:
            return CombatAction(
                actor=self.character_name,
                target=m.group("target").strip(),
                verb="spell",
                damage=int(m.group("damage")),
                is_non_melee=True,
                timestamp=dt,
            )

        m = RE_NON_MELEE_YOU_HIT.match(msg)
        if m:
            return CombatAction(
                actor="You",
                target=m.group("target").strip(),
                verb="non-melee",
                damage=int(m.group("damage")),
                is_non_melee=True,
                timestamp=dt,
            )

        m = RE_NON_MELEE_OTHER_HIT.match(msg)
        if m:
            return CombatAction(
                actor=m.group("actor").strip(),
                target=m.group("target").strip(),
                verb="non-melee",
                damage=int(m.group("damage")),
                is_non_melee=True,
                timestamp=dt,
            )

        # 6. General Melee Damage (You, Pet, or others)
        m = RE_MELEE_DAMAGE.match(msg)
        if m:
            actor = m.group("actor").strip()
            target = m.group("target").strip()
            special = m.group("special")
            return CombatAction(
                actor=actor,
                target=target,
                verb=m.group("verb"),
                damage=int(m.group("damage")),
                is_crit=(special == "critical"),
                is_crippling=(special == "crippling blow"),
                timestamp=dt,
            )

        # 7. Misses & Defenses
        m = RE_YOU_MISS.match(msg)
        if m:
            return CombatAction(
                actor="You",
                target=m.group("target").strip(),
                verb=m.group("verb"),
                damage=0,
                is_miss=True,
                miss_type="miss",
                timestamp=dt,
            )

        m = RE_DEFENSE_ON_YOU.match(msg)
        if m:
            return CombatAction(
                actor=m.group("actor").strip(),
                target="YOU",
                verb=m.group("verb"),
                damage=0,
                is_miss=True,
                miss_type=m.group("defense").lower(),
                timestamp=dt,
            )

        m = RE_ENEMY_MISS_YOU.match(msg)
        if m:
            return CombatAction(
                actor=m.group("actor").strip(),
                target="YOU",
                verb=m.group("verb"),
                damage=0,
                is_miss=True,
                miss_type="miss",
                timestamp=dt,
            )

        m = RE_DEFENSE_OTHER.match(msg)
        if m:
            return CombatAction(
                actor=m.group("actor").strip(),
                target=m.group("target").strip(),
                verb=m.group("verb"),
                damage=0,
                is_miss=True,
                miss_type=m.group("defense").lower(),
                timestamp=dt,
            )

        m = RE_GENERAL_MISS.match(msg)
        if m:
            return CombatAction(
                actor=m.group("actor").strip(),
                target=m.group("target").strip(),
                verb=m.group("verb"),
                damage=0,
                is_miss=True,
                miss_type="miss",
                timestamp=dt,
            )

        # 8. Heals
        m = RE_HEAL_ON_YOU.match(msg)
        if m:
            return HealAction(
                caster="Unknown",
                recipient="You",
                amount=int(m.group("amount")),
                timestamp=dt,
            )

        m = RE_YOU_HEAL.match(msg)
        if m:
            return HealAction(
                caster="You",
                recipient=m.group("recipient").strip(),
                amount=int(m.group("amount")),
                timestamp=dt,
            )

        m = RE_OTHER_HEALED_YOU.match(msg)
        if m:
            return HealAction(
                caster=m.group("caster").strip(),
                recipient="You",
                amount=int(m.group("amount")),
                timestamp=dt,
            )

        m = RE_OTHER_HEAL_OTHER.match(msg)
        if m:
            return HealAction(
                caster=m.group("caster").strip(),
                recipient=m.group("recipient").strip(),
                amount=int(m.group("amount")),
                timestamp=dt,
            )

        m = RE_HEALED_HIT_POINTS.match(msg)
        if m:
            return HealAction(
                caster=m.group("caster").strip(),
                recipient=m.group("recipient").strip(),
                amount=int(m.group("amount")),
                timestamp=dt,
            )

        # 9. Spells cast & resists
        m = RE_YOU_CAST.match(msg)
        if m:
            return {"type": "spell_cast", "caster": "You", "spell": m.group("spell")}

        m = RE_OTHER_CAST.match(msg)
        if m:
            return {"type": "spell_cast", "caster": m.group("actor"), "spell": m.group("spell")}

        m = RE_SPELL_INTERRUPT.match(msg)
        if m:
            return {"type": "spell_interrupt"}

        m = RE_TARGET_RESIST.match(msg)
        if m:
            return {"type": "spell_resist", "spell": m.group("spell")}

        m = RE_MOB_RESIST.match(msg)
        if m:
            return {"type": "spell_resist", "target": m.group("target"), "spell": m.group("spell")}

        # 10. Deaths
        m = RE_YOU_SLAY.match(msg)
        if m:
            return {"type": "death", "mob": m.group("mob").strip(), "slayer": "You"}

        m = RE_OTHER_SLAY.match(msg)
        if m:
            return {"type": "death", "mob": m.group("mob").strip(), "slayer": m.group("slayer").strip()}

        m = RE_MOB_DIED.match(msg)
        if m:
            return {"type": "death", "mob": m.group("mob").strip(), "slayer": "Unknown"}

        # Player death: "You have been slain by X!" or "You died."
        m = RE_YOU_DIED.match(msg)
        if m:
            return {"type": "player_death", "killer": m.group("killer").strip()}

        m = RE_YOU_DIED_ALT.match(msg)
        if m:
            return {"type": "player_death", "killer": "Unknown"}

        # Loading screen (zone transition / character switch)
        m = RE_LOADING.match(msg)
        if m:
            return {"type": "loading"}

        # 11. Experience
        m = RE_EXP_GAIN.match(msg)
        if m:
            return {"type": "experience"}

        # 12. Loot
        m = RE_YOU_LOOT.match(msg)
        if m:
            return LootRecord(item=m.group("item").strip(), looter="You", timestamp=dt)

        m = RE_OTHER_LOOT.match(msg)
        if m:
            return LootRecord(
                item=m.group("item").strip(),
                looter=m.group("looter").strip(),
                timestamp=dt,
            )

        m = RE_COIN_LOOT.match(msg)
        if m:
            return {"type": "coin_loot", "money": m.group("money").strip()}

        return None
