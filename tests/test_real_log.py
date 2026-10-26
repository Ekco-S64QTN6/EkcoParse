"""Integration smoke test against the configured local EQ log, when available."""

import unittest

from ekco_parse.config import load_config
from ekco_parse.dps_engine import DpsEngine
from ekco_parse.loot_engine import LootEngine
from ekco_parse.models import CombatAction, LootRecord
from ekco_parse.parser import LogParser
from ekco_parse.timer_engine import TimerEngine


class TestRealLogFile(unittest.TestCase):

    def test_parse_configured_real_log_lines(self):
        config = load_config()
        log_path = config.resolve_log_path()
        if not log_path.is_file():
            self.skipTest("Configured EQ log file not present")

        parser = LogParser(character_name=config.character_name)
        dps = DpsEngine(character_name=config.character_name)
        timers = TimerEngine()
        loot = LootEngine()

        parsed_events_count = 0

        # Read the most recent 300 lines of the configured log.
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-300:]

        for line in lines:
            res = parser.parse_line(line)
            if not res:
                continue
            log_line, event = res
            timers.process_line(log_line.message, log_line.timestamp)
            if event:
                parsed_events_count += 1
                if isinstance(event, CombatAction):
                    dps.process_combat_action(event)
                elif isinstance(event, LootRecord):
                    loot.record_loot(event)
                elif isinstance(event, dict) and event.get("type") == "death":
                    dps.on_mob_death(event.get("mob", ""))
                    loot.record_kill(event.get("mob", ""), event.get("slayer", ""))

        self.assertGreater(parsed_events_count, 0)
        print(f"[RealLogTest] Successfully parsed {parsed_events_count} events from configured log.")


if __name__ == "__main__":
    unittest.main()
