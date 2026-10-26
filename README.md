# Ekco Parse

**High-Performance Terminal Desktop Companion for Project 1999 EverQuest**

Ekco Parse is a lightweight, zero-latency Linux terminal companion application designed specifically for **Project 1999 EverQuest**. It unites the core capabilities of **GINA** (spell, buff, and DoT timers & alerts), **GamParse** (live DPS, combat breakdowns, and tank mitigation), a **100% P99-compliant log-driven standalone map tracker** (`/loc` GPS radar), and a **live kill & loot ledger** into an ultra-fast monospace dashboard.

Designed following the visual aesthetics, dark color palette, and high-density dashboard layouts of `dwarffortress-antfarm`, Ekco Parse is engineered to run in borderless terminal windows (e.g. Kitty, XTerm) pinned "Always on Top" next to your P99 client or captured cleanly as a streaming overlay.

---

## Key Features

### 1. GINA Clone: Running Clocks & Dual Lists
- **DoT & CC Rotation Clock (Sorted Soonest-to-Fade First)**:
  - Specially tailored for a **Level 60 Necromancer** running multi-DoT rotations.
  - Built-in exact tick & duration data for **Splurt** (96s), **Funeral Pyre of Kelador** (42s), **Cascading Darkness** (90s), **Cessation of Cor** (54s), **Asystole** (72s), **Envenomed Bolt** (66s), **Boil Blood** (54s), **Ignite Blood** (60s), **Plague** (108s), **Bond of Death** (24s), **Paralyzing Earth** (180s), and **Screaming Terror** (18s).
  - Displays a live running clock (`MM:SS`) strictly ordered by which spell will expire first so you know the exact recast priority.
  - Recast warnings: Changes to high-contrast red at `< 10s` (`▲ RECAST SOON`) and pulses `! RECAST NOW !` on fade.
  - Auto-wear-off detection and instant DoT purging when the target dies.
- **Separate Buffs & Cooldowns List**:
  - Maintained as a **separate list on the TUI** to keep combat rotations clear.
  - Tracks self and pet buffs: **Arch Lich** (20.5m), **Demi Lich** (144m), **Dead Man Floating** (72m), **Shield of the Undertaker** (36m), **Diamondskin** (72m), **Spirit of Wolf** (36m), **Clarity / Breeze** (24m), and **Haste**.
  - Displays duration remaining, visual progress bar (`████░░░░`), and early warning when fading.

### 2. GamParse Clone: Live DPS & Tank Mitigation
- **Combat Breakdown**:
  - Live DPS calculation across active encounters (`DPS = Damage / Active Seconds`).
  - Real-time ASCII sparklines showing damage trends.
  - Ranked combatants table: Player, Pet, and Party/Raid members with Damage, Share %, DPS, Accuracy %, Crits, and Max Hit.
- **Tank Mitigation & Avoidance**:
  - Tracks incoming damage dealt to `YOU`.
  - Calculates defensive avoidance percentage: Dodges, Parries, Blocks, Ripostes, and Enemy Misses.
  - Real-time incoming DPS and max hit taken tracking.

### 3. Standalone Map Window (`/loc` Radar & GPS)
- **100% P99 Compliant**: Reads purely from client log file updates when `/loc` is invoked (no memory scanning or hooks).
- **Runs as its own Standalone Window**: Designed to float anywhere on screen or over the game window.
- **Real In-Game Map Geometry**: Directly loads map files (`L` and `P` lines) from your EverQuest directory (`/home/ekco/Games/Project1999/maps/`) or built-in fallbacks.
- **Live 2D Radar Canvas**:
  - High-resolution ASCII/Unicode radar grid with player marker `[@]`, breadcrumb trail (`░`), and zone lines (`[Z]`), merchants (`[M]`), banks (`[B]`).
  - Live coordinates (`Y: 1234.5 | X: -567.8 | Z: 12.0`), travel speed (`u/s`), and compass rose heading.
  - POI radar table displaying all nearby landmarks, distances in meters, and bearings (`[NW]`, `[E]`, etc.).
  - Zoom levels (`1x`, `2x`, `4x`) and zone switching.

### 4. Kill & Loot Ledger
- Slain mob counters and real-time **Kills / Hour** calculation.
- Experience ticks milestone tracker and **Exp / Hour**.
- Item drop logging parsing `--You have looted a ...--` with item counts and looter history.

### 5. Urgent Alert Ticker / Story Card
- High-contrast alert card at bottom for peripheral vision scanning.
- Instant warnings for mob **Enrage** (`STOP MELEE!`), **Dragon Roar** (AE Fear), **Deathtouch** timers, and rare loot drops.

---

## Visual Design & Aesthetics

Follows the aesthetic specifications of `/github/dwarffortress-antfarm/`:
- **Dark Void Screen**: `#05070D`
- **Slate Navy Panels**: `#0D1120`
- **Primary Borders / Cyan**: `#00F5FF`
- **Secondary Borders / Pink**: `#FF2D95`
- **Header Accent / Violet**: `#B64CFF`
- **Status Green / Success**: `#59FF8E`
- **Warning Gold / Buffs**: `#FFC857`
- **Alert Red / Danger**: `#FF4040`
- High-contrast block progress bars (`████░░░░`) and unicode sparklines (` ▂▃▄▅▆▇█`).

### Transparent dashboard background

The main dashboard's Textual screen and panels use transparent backgrounds. The application deliberately does not override the terminal background color, so your terminal's own opacity/transparency settings can show the game behind it. Actual alpha transparency is provided by the terminal emulator and compositor, not by Textual CSS alone.

For Kitty, configure a suitable value in `kitty.conf`, for example:

```conf
background_opacity 0.20
```

The appropriate value depends on your setup. Terminals without background-alpha support need their own compositor/profile configuration; otherwise their default terminal background may still appear opaque.

---

## Installation & Quick Start

Ekco Parse requires Python 3.10+ and uses `uv` or `pip` to install dependencies (`textual`, `rich`, `pyyaml`).

### Setup

```bash
cd "/home/ekco/github/Ekco Parse"

# Initialize virtual environment and install dependencies
uv venv .venv
uv pip install -r requirements.txt --python .venv/bin/python
```

### Launch Modes

```bash
# 1. Launch Main Companion Dashboard
./run.sh

# 2. Launch Standalone Map Window
./run.sh --map

# 3. Launch Both Dashboard & Map in separate terminal windows (Kitty/XTerm)
./run.sh --all

# 4. Launch with Realistic P99 Log Simulator (offline testing & demo)
./run.sh --sim

# 5. Run Test Suite
./run.sh --test
```

---

## Configuration (`config.yaml`)

Configuration is stored in `config.yaml` with safe defaults:

```yaml
character:
  name: "Ekco"
  server: "green"         # green, blue, red, or project1999
  class: "Necromancer"

log_tailer:
  log_dir: "/home/ekco/Games/Project1999/Logs"
  filename_pattern: "eqlog_{character}_{server}.txt"
  poll_interval_sec: 0.1
  start_at_end: true

combat:
  encounter_timeout_sec: 12.0
  history_limit: 50

map:
  default_zone: "East Commonlands"
  max_breadcrumbs: 60

triggers:
  - name: "Mob Enraged"
    pattern: "^(?P<mob>.+?) (?:looks very angry!|has become ENRAGED\\.)"
    timer_seconds: 10
    alert_text: "URGENT: {mob} is ENRAGED! STOP MELEE!"
    category: "raid"
    color: "#FF4040"
    sound: true
```

---

## Keybindings

### Main Dashboard
| Key | Action |
|:---:|:---|
| `q` | Quit application |
| `m` | Launch Standalone Map Window in dedicated terminal |
| `r` | Conclude and reset current combat encounter |
| `c` | Clear all active timers |
| `s` | Toggle audible terminal bell on alerts |
| `t` | Inject simulated Necromancer DoT test sequence |

### Standalone Map Window
| Key | Action |
|:---:|:---|
| `q` | Quit map window |
| `z` | Cycle / switch active zone |
| `+` | Zoom in (up to 4.0x) |
| `-` | Zoom out (down to 1.0x) |
| `b` | Clear breadcrumb trail |
| `l` | Manually advance test `/loc` coordinates |

---

## Testing & Verification

Run the full automated test suite verifying parsing, combat mathematics, DoT timers, and map rendering:

```bash
./run.sh --test
```
