"""Realistic Project 1999 log simulator for testing and offline demonstrations."""

import random
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, List


class LogSimulator:
    """Generates authentic EverQuest P99 log streams."""

    def __init__(self, character_name: str = "Ekco"):
        self.character_name = character_name
        self.cur_y = -130.0
        self.cur_x = -1580.0
        self.cur_z = 3.75
        self.heading = "Northwest"

    def format_line(self, message: str) -> str:
        """Wrap message with P99 log timestamp."""
        ts = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        return f"[{ts}] {message}"

    def generate_encounter_events(self, mob: str = "a hill giant") -> List[str]:
        """Generate a realistic combat sequence."""
        lines = []
        lines.append(self.format_line(f"You begin casting Ice Comet."))
        lines.append(self.format_line(f"{mob} slashes YOU for {random.randint(60, 115)} points of damage."))
        lines.append(self.format_line(f"{mob} tries to kick YOU, but YOU dodge!"))
        lines.append(self.format_line(f"You hit {mob} for {random.randint(550, 820)} points of non-melee damage."))
        lines.append(self.format_line(f"Your pet bites {mob} for {random.randint(28, 45)} points of damage."))
        lines.append(self.format_line(f"Drippin healed you for 300 points of damage."))
        lines.append(self.format_line(f"{mob} tries to bash YOU, but misses!"))
        
        # Chance for mob enrage
        if random.random() < 0.4:
            lines.append(self.format_line(f"{mob} looks very angry!"))

        lines.append(self.format_line(f"You slash {mob} for {random.randint(35, 95)} points of damage. (critical)"))
        lines.append(self.format_line(f"You have slain {mob}!"))
        lines.append(self.format_line(f"You gain experience!!"))
        lines.append(self.format_line(f"--You have looted a Fine Steel Longsword.--"))
        lines.append(self.format_line(f"You receive 12 platinum, 4 gold, and 8 silver from the corpse."))
        return lines

    def generate_loc_event(self) -> str:
        """Simulate walking movement and /loc command."""
        self.cur_y += random.uniform(-15.0, 25.0)
        self.cur_x += random.uniform(-20.0, 15.0)
        self.cur_z += random.uniform(-1.0, 1.0)
        return self.format_line(f"Your Location is {self.cur_y:.2f}, {self.cur_x:.2f}, {self.cur_z:.2f}")

    def generate_buff_event(self) -> str:
        """Simulate buff landing."""
        buffs = [
            "You feel the spirit of the wolf enter you.",
            "You feel a sudden rush of adrenaline.",
            "Your feet leave the ground.",
            "Your skin sprouts sharp thorns.",
            "You feel much faster.",
        ]
        return self.format_line(random.choice(buffs))

    def run_to_file(self, target_path: Path, delay_sec: float = 1.0) -> None:
        """Continuously write simulated events to target log file."""
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        mobs = ["a hill giant", "a sand giant", "an orc legionnaire", "Taegria Fe`Dhar", "Guard Wextr"]

        with open(target_path, "a", encoding="utf-8") as f:
            f.write(self.format_line("Welcome to EverQuest!\n"))
            f.write(self.format_line("You have entered East Commonlands.\n"))
            f.flush()

            while True:
                time.sleep(delay_sec)
                # Randomly produce combat, /loc, or buff event
                choice = random.random()
                if choice < 0.45:
                    events = self.generate_encounter_events(random.choice(mobs))
                    for ev in events:
                        f.write(ev + "\n")
                        f.flush()
                        time.sleep(0.4)
                elif choice < 0.8:
                    ev = self.generate_loc_event()
                    f.write(ev + "\n")
                    f.flush()
                else:
                    ev = self.generate_buff_event()
                    f.write(ev + "\n")
                    f.flush()
