"""Test parsing real user log lines from /home/ekco/Games/Project1999/Logs/eqlog_Ekco_project1999.txt."""

import unittest
from pathlib import Path
from ekco_parse.dps_engine import DpsEngine
from ekco_parse.loot_engine import LootEngine
from ekco_parse.models import CombatAction, Location, LootRecord
from ekco_parse.parser import LogParser
from ekco_parse.timer_engine import TimerEngine


class TestRealLogFile(unittest.TestCase):

    def test_parse_real_ekco_log_lines(self):
        log_path = Path("/home/ekco/Games/Project1999/Logs/eqlog_Ekco_project1999.txt")
        if not log_path.exists():
            self.skipTest("Real log file not present")

        parser = LogParser(character_name="Ekco")
        dps = DpsEngine(character_name="Ekco")
        timers = TimerEngine()
        loot = LootEngine()

        parsed_events_count = 0

        # Read last 300 lines of user's real log
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
        print(f"[RealLogTest] Successfully parsed {parsed_events_count} live events from user log!")


if __name__ == "__main__":
    unittest.main()
