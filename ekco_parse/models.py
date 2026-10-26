"""Domain models and data structures for Ekco Parse."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class LogLine:
    """Represents a raw log line with parsed timestamp and content."""
    timestamp_raw: str
    timestamp: datetime
    message: str
    original_line: str


@dataclass
class CombatAction:
    """Represents a combat action (hit, miss, crit, non-melee, riposte, etc.)."""
    actor: str                # "You", "Ekco", "a hill giant", "Your pet"
    target: str               # "a hill giant", "YOU", etc.
    verb: str                 # "slash", "crush", "pierce", "backstab", "punch", etc.
    damage: int               # 0 if miss
    is_crit: bool = False
    is_crippling: bool = False
    is_non_melee: bool = False
    is_miss: bool = False
    miss_type: Optional[str] = None  # "miss", "dodge", "parry", "riposte", "block"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HealAction:
    """Represents a healing event."""
    caster: str               # "You", "Clericname"
    recipient: str            # "You", "Warriorname"
    amount: int
    spell: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CombatantStats:
    """Aggregated stats for an individual participant in combat."""
    name: str
    damage_dealt: int = 0
    hits_landed: int = 0
    misses: int = 0
    crits: int = 0
    max_hit: int = 0
    non_melee_damage: int = 0
    
    # Tank / incoming damage stats
    damage_taken: int = 0
    hits_taken: int = 0
    dodges: int = 0
    parries: int = 0
    ripostes: int = 0
    blocks: int = 0
    enemy_misses: int = 0
    max_hit_taken: int = 0

    # Healing
    healing_done: int = 0
    healing_received: int = 0

    @property
    def total_swings(self) -> int:
        return self.hits_landed + self.misses

    @property
    def accuracy(self) -> float:
        if self.total_swings == 0:
            return 0.0
        return (self.hits_landed / self.total_swings) * 100.0

    @property
    def crit_rate(self) -> float:
        if self.hits_landed == 0:
            return 0.0
        return (self.crits / self.hits_landed) * 100.0

    @property
    def avoidance_rate(self) -> float:
        total_incoming = self.hits_taken + self.dodges + self.parries + self.ripostes + self.blocks + self.enemy_misses
        if total_incoming == 0:
            return 0.0
        avoided = self.dodges + self.parries + self.ripostes + self.blocks + self.enemy_misses
        return (avoided / total_incoming) * 100.0


@dataclass
class Encounter:
    """Represents a continuous combat encounter (fight against one or more mobs)."""
    id: str
    target: str
    start_time: datetime
    last_action_time: datetime
    end_time: Optional[datetime] = None
    is_active: bool = True
    combatants: Dict[str, CombatantStats] = field(default_factory=dict)
    actions: List[CombatAction] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        end = self.end_time if self.end_time else self.last_action_time
        diff = (end - self.start_time).total_seconds()
        return max(1.0, diff)

    @property
    def total_damage(self) -> int:
        return sum(c.damage_dealt for c in self.combatants.values())

    @property
    def total_dps(self) -> float:
        return self.total_damage / self.duration_seconds

    def get_combatant(self, name: str) -> CombatantStats:
        if name not in self.combatants:
            self.combatants[name] = CombatantStats(name=name)
        return self.combatants[name]


@dataclass
class Timer:
    """Represents a GINA-style active countdown timer or alert."""
    id: str
    name: str
    alert_text: str
    total_seconds: float
    remaining_seconds: float
    category: str = "buff"    # "buff", "debuff", "raid", "cooldown", "util"
    color: str = "#00F5FF"
    sound: bool = False
    target: Optional[str] = None
    wear_off_pattern: Optional[str] = None
    buff_slot: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        return self.remaining_seconds <= 0

    @property
    def progress_pct(self) -> float:
        if self.total_seconds <= 0:
            return 0.0
        return max(0.0, min(1.0, self.remaining_seconds / self.total_seconds))


@dataclass
class Location:
    """Represents parsed /loc coordinates."""
    y: float                   # North / South (+ = North, - = South)
    x: float                   # West / East (+ = West, - = East)
    z: float                   # Elevation / Altitude
    zone: str = "Unknown"
    heading: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LootRecord:
    """Represents an item looted event."""
    item: str
    looter: str
    count: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
