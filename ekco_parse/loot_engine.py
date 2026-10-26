"""Live kill, experience, and loot tracking engine."""

import re
from collections import Counter, deque
from datetime import datetime
from typing import Deque, Dict, List, Optional

from ekco_parse.models import LootRecord


class LootEngine:
    """Tracks mob deaths, experience milestones, and loot histories."""

    def __init__(self, history_limit: int = 100):
        self.session_start = datetime.now()
        self.history_limit = history_limit

        # Kills
        self.total_kills: int = 0
        self.mob_kills: Counter = Counter()
        self.recent_kills: Deque[Dict[str, str]] = deque(maxlen=history_limit)

        # Experience
        self.exp_ticks: int = 0
        self.last_exp_time: Optional[datetime] = None

        # Loot
        self.total_looted: int = 0
        self.loot_records: Deque[LootRecord] = deque(maxlen=history_limit)
        self.item_counts: Counter = Counter()

        # Preserve the original message while keeping separate denomination totals.
        self.total_coin_messages: int = 0
        self.coin_totals: Counter = Counter()
        self.coin_history: Deque[Dict[str, str]] = deque(maxlen=history_limit)

    @property
    def session_duration_hours(self) -> float:
        secs = (datetime.now() - self.session_start).total_seconds()
        return max(0.001, secs / 3600.0)

    @property
    def kills_per_hour(self) -> float:
        return self.total_kills / self.session_duration_hours

    @property
    def exp_per_hour(self) -> float:
        return self.exp_ticks / self.session_duration_hours

    def record_kill(self, mob: str, slayer: str = "You", timestamp: Optional[datetime] = None) -> None:
        """Record a slain mob."""
        ts = timestamp or datetime.now()
        self.total_kills += 1
        clean_mob = mob.strip()
        self.mob_kills[clean_mob] += 1
        self.recent_kills.appendleft({
            "mob": clean_mob,
            "slayer": slayer or "Unknown",
            "time": ts.strftime("%H:%M:%S"),
        })

    def record_exp(self, timestamp: Optional[datetime] = None) -> None:
        """Record an experience milestone."""
        self.exp_ticks += 1
        self.last_exp_time = timestamp or datetime.now()

    def record_loot(self, record: LootRecord) -> None:
        """Record an item looted."""
        self.total_looted += 1
        clean_item = record.item.strip()
        self.item_counts[clean_item] += 1
        self.loot_records.appendleft(record)

    def record_coin_loot(self, money: str, timestamp: Optional[datetime] = None) -> None:
        """Record a coin-loot message and sum any recognizable denominations."""
        clean_money = money.strip()
        ts = timestamp or datetime.now()
        self.total_coin_messages += 1
        self.coin_history.appendleft({
            "money": clean_money,
            "time": ts.strftime("%H:%M:%S"),
        })

        denominations = {
            "platinum": "platinum", "plat": "platinum", "pp": "platinum",
            "gold": "gold", "gp": "gold",
            "silver": "silver", "sp": "silver",
            "copper": "copper", "cp": "copper",
        }
        pattern = r"\b(?P<amount>\d+)\s+(?P<denomination>platinum|plat|pp|gold|gp|silver|sp|copper|cp)\b"
        for match in re.finditer(pattern, clean_money, re.IGNORECASE):
            denomination = denominations[match.group("denomination").lower()]
            self.coin_totals[denomination] += int(match.group("amount"))

    def reset_session(self) -> None:
        """Reset session counters."""
        self.session_start = datetime.now()
        self.total_kills = 0
        self.mob_kills.clear()
        self.recent_kills.clear()
        self.exp_ticks = 0
        self.last_exp_time = None
        self.total_looted = 0
        self.loot_records.clear()
        self.item_counts.clear()
        self.total_coin_messages = 0
        self.coin_totals.clear()
        self.coin_history.clear()

    def get_top_items(self, limit: int = 15) -> List[tuple]:
        """Return most frequently looted items."""
        return self.item_counts.most_common(limit)

    def get_top_mobs(self, limit: int = 15) -> List[tuple]:
        """Return most frequently slain mobs."""
        return self.mob_kills.most_common(limit)
