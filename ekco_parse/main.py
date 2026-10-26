"""Command line entry point for Ekco Parse."""

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from ekco_parse.config import load_config
from ekco_parse.simulator import LogSimulator
from ekco_parse.ui.main_app import EkcoParseApp
from ekco_parse.ui.map_app import EkcoMapApp


def detect_terminal() -> Optional[str]:
    """Find installed terminal emulator."""
    for term in ["kitty", "alacritty", "wezterm", "foot", "konsole", "xterm"]:
        if shutil.which(term):
            return term
    return None


def spawn_in_terminal(title: str, command: str) -> None:
    """Launch command in a dedicated terminal window."""
    term = detect_terminal()
    if not term:
        subprocess.Popen(["bash", "-lc", command])
        return

    if term == "kitty":
        subprocess.Popen(["kitty", "--title", title, "--", "bash", "-lc", command])
    elif term == "xterm":
        subprocess.Popen(["xterm", "-title", title, "-e", "bash", "-lc", command])
    elif term == "alacritty":
        subprocess.Popen(["alacritty", "-t", title, "-e", "bash", "-lc", command])
    else:
        subprocess.Popen([term, "-e", "bash", "-lc", command])


def main():
    parser = argparse.ArgumentParser(description="Ekco Parse - Project 1999 EverQuest Desktop Companion")
    parser.add_argument("--config", "-c", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--map", "-m", action="store_true", help="Launch standalone map window")
    parser.add_argument("--all", "-a", action="store_true", help="Launch both dashboard and standalone map window in separate terminals")
    parser.add_argument("--simulate", "-s", action="store_true", help="Run with simulated P99 combat/DoT/loc log stream")
    parser.add_argument("--zone", "-z", type=str, default=None, help="Initial zone name for map")

    args = parser.parse_args()
    config = load_config(args.config)

    # If simulation is requested, spin up a background generator writing to test log
    if args.simulate:
        sim_log = Path("/tmp/eqlog_Ekco_project1999_sim.txt")
        config.log_dir = Path("/tmp")
        config.filename_pattern = "eqlog_Ekco_project1999_sim.txt"
        config.start_at_end = False

        sim = LogSimulator(character_name=config.character_name)
        sim_thread = threading.Thread(target=sim.run_to_file, args=(sim_log, 0.8), daemon=True)
        sim_thread.start()
        print(f"[Simulator] Writing simulated P99 log events to {sim_log}")
        time.sleep(0.5)

    if args.all:
        py_bin = sys.executable
        # Spawn map window
        spawn_in_terminal("Ekco Map GPS", f"'{py_bin}' -m ekco_parse.main --map")
        # Run dashboard in current terminal
        app = EkcoParseApp(config=config)
        app.run()
        return

    if args.map:
        app = EkcoMapApp(config=config, zone=args.zone)
        app.run()
        return

    # Default: Run Main Companion Dashboard
    app = EkcoParseApp(config=config)
    app.run()


if __name__ == "__main__":
    main()
