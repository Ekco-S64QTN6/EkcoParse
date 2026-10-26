# Ekco Parse

**A Linux-first, log-driven companion for EverQuest: Project 1999.**

<p>
  <a href="https://github.com/Ekco-S64QTN6/EkcoParse/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/Ekco-S64QTN6/EkcoParse?style=flat"></a>
  <a href="https://github.com/Ekco-S64QTN6/EkcoParse/issues"><img alt="Open issues" src="https://img.shields.io/github/issues/Ekco-S64QTN6/EkcoParse?style=flat"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="Platform Linux" src="https://img.shields.io/badge/platform-Linux-lightgrey?logo=linux&logoColor=white">
  <img alt="Target game Project 1999" src="https://img.shields.io/badge/game-EverQuest%20P99-blue">
  <img alt="Project status: in development" src="https://img.shields.io/badge/status-in%20development-orange">
</p>

Ekco Parse brings several useful EverQuest tools into a compact terminal dashboard and a separate map window. It watches your local client log to track spell timers, buffs, combat activity, and player location.

The map uses the coordinates printed by `/loc` and compatible zone-map files. Ekco Parse does **not** read game memory, inject into the client, or attach to the game process.

> **Project status:** actively being developed. See the [roadmap](ROADMAP.md) for an honest breakdown of what is connected, what is partial, and what remains.

## Features

| Area | Available now |
| --- | --- |
| **Spell and buff timers** | Separate DoT/CC and buff lists, countdowns, progress bars, fade/recast states, and configurable log triggers. Spell coverage and ready-to-use trigger presets are still evolving. |
| **Combat DPS** | Live encounter damage and DPS with per-combatant contributions. Additional combat and tank-mitigation calculations exist but are not all exposed in the main dashboard yet. |
| **Standalone map and GPS** | Log-driven `/loc` coordinates, zone geometry, a player marker, breadcrumb trail, heading and speed display, nearby points of interest, distances, and bearings. The first valid location centers the map and opens a 4× view; zoom can then be adjusted manually. |
| **Kills, experience, loot, and respawns** | Tracking engines and widgets are present, but the kill/loot and respawn panels still need to be fully connected to the main dashboard. See the roadmap for remaining work. |
| **Alerts** | A compact ticker shows recent trigger alerts and recent log activity. Custom triggers can define patterns, timers, messages, colors, and sound behavior. |

The project favors a dense, readable terminal interface with high-contrast colors and bordered panels. It is designed to sit beside your game rather than replace the client.

## Requirements

- Linux
- Python 3.10 or newer
- A Project 1999 client installation that writes its log file
- A terminal emulator; Kitty is the best-supported option for the transparent overlay

## Installation and first launch

Clone the repository, copy the example configuration, and edit it to match your character and local P99 installation:

```bash
git clone https://github.com/Ekco-S64QTN6/EkcoParse.git
cd EkcoParse
cp config.example.yaml config.yaml
```

Open `config.yaml` and set at least the character name, server, and log directory. For example:

```yaml
character:
  name: "YourCharacter"
  server: "green" # green, blue, red, etc.

log_tailer:
  log_dir: "~/Games/Project1999/Logs"
  filename_pattern: "eqlog_{character}_{server}.txt"

map:
  default_zone: "East Commonlands"
  max_breadcrumbs: 60
```

The exact log path depends on your installation. The launcher creates a local `.venv` and installs the required Python packages the first time it runs, if needed.

```bash
./run.sh
```

If the dashboard does not find your log, double-check the filename, character/server values, and `log_dir`. The map updates when location output appears in the log, so use `/loc` in game and ensure logging is enabled.

## Launch options

| Command | Purpose |
| --- | --- |
| `./run.sh` | Start the main dashboard/overlay. |
| `./run.sh --overlay` | Explicitly launch the dashboard overlay. |
| `./run.sh --map` | Launch the standalone map window. |
| `./run.sh --all` | Launch the dashboard and map in separate windows where supported. |
| `./run.sh --sim` | Run with a simulated log stream for offline demonstration. |
| `./run.sh --test` | Run the automated test suite. |

The main dashboard also provides these keyboard shortcuts:

| Key | Action |
| --- | --- |
| `q` | Quit |
| `m` | Open the standalone map |
| `r` | End/reset the current encounter |
| `c` | Clear active timers |
| `s` | Toggle the terminal bell for alerts |
| `t` | Run the simulated Necromancer DoT sequence |

In the map window:

| Key | Action |
| --- | --- |
| `q` | Quit |
| `z` | Cycle through supported zones |
| `+` / `-` | Zoom in / out |
| `b` | Clear the breadcrumb trail |
| `l` | Add a test location step |

## Overlay transparency

The default launcher starts the dashboard in Kitty with `background_opacity=0.55`. To make the game more visible through the overlay, change the `background_opacity` value in `KITTY_OVERLAY_OPTS` near the top of `run.sh`; lower values are more transparent. The dashboard itself uses transparent Textual backgrounds and no longer forces the terminal background color.

Transparency depends on terminal and compositor support. If you launch in a terminal other than Kitty, use that terminal's own transparency settings. The standalone map window intentionally uses a dark panel background for map readability.

## Tests and roadmap

Run the test suite with:

```bash
./run.sh --test
```

Tests cover core log parsing, combat calculations, timer behavior, map math/rendering, and Textual UI mounting. Real-log validation and broader feature coverage are still ongoing.

See [ROADMAP.md](ROADMAP.md) for implementation status, known gaps, and prioritized follow-up work.

## Acknowledgements

A sincere thank-you to the **Project 1999 developers, staff, volunteers, wiki contributors, mapmakers, and players**. Your work keeps the classic EverQuest experience alive and gives projects like this a world worth building tools for. Thanks as well to the wider EverQuest emulation and preservation community for years of shared research, documentation, and tooling.

Ekco Parse is an independent, community-made companion. It is not an official Project 1999 tool and is not affiliated with or endorsed by Project 1999 or Daybreak Game Company. EverQuest and related game names and assets belong to their respective rights holders.

## References and project influences

The projects and resources below are useful references for the problem space, implementation research, or dependencies. They are listed to credit the work and documentation the project draws on; Ekco Parse is independent and is not affiliated with the tools or communities listed.

### EverQuest tools

- **[GINA](https://eq.gimasoft.com/gina/Default.aspx)** — a reference for log-triggered alerts, timers, and player-configurable triggers.
- **[GamParse](https://gambosoft.eqresource.com/downloads.php)** — a reference for combat-log analysis, DPS reporting, and tanking/defense statistics.
- **[nParse](https://github.com/nomns/nparse)** — an open-source Project 1999 companion that reads player logs for location and spell tracking; a useful point of comparison for log-driven map behavior.

### Project 1999, emulation, and map resources

- **[Project 1999](https://project1999.com/)** — the server and community this project is built to support. Thanks to the team and players for maintaining it.
- **[Project 1999 Wiki](https://wiki.project1999.com/)** — community-maintained reference material for zones, NPCs, spells, game mechanics, and technical topics. The wiki is community-run and is not an official staff-maintained source.
- **[EQEmulator](https://eqemulator.org/)** and its **[documentation](https://docs.eqemu.dev/)** — resources from the broader EverQuest emulation community.
- **[Brewall's EverQuest Maps](https://www.eqmaps.info/)** and the **[EverQuest Map Preserve](https://steveprutz.com/eq/index.html)** — community mapmaking and historical map references. Map files remain the work of their respective creators; follow their terms and attribution requirements wherever applicable.

### Interface and libraries

- **[Textual](https://github.com/Textualize/textual)** — the terminal UI framework.
- **[Rich](https://github.com/Textualize/rich)** — terminal styling and formatted text.
- **[PyYAML](https://github.com/yaml/pyyaml)** — YAML configuration loading.

Thanks to everyone who builds, documents, tests, and shares tools for the EverQuest community.
