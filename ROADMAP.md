# Ekco Parse Roadmap

_Last reviewed: 2026-10-26. Status below reflects the repository's `main` branch at review time. Items remain open until the user-facing behavior is tested, not merely committed._

## Product goal

Ekco Parse aims to combine four proven use cases into a lightweight, **Project 1999 log-driven** desktop companion:

- **GINA-style timers and alerts:** spell, DoT, buff, cooldown, and configurable trigger timers.
- **GamParse-style combat analysis:** live DPS, encounter breakdowns, and tank mitigation/avoidance.
- **Standalone P99 map tracker:** `/loc` GPS radar, player-centered map view, landmarks, bearings, and breadcrumb trail.
- **Live kill and loot ledger:** kills, experience ticks, item drops, and respawn estimates.

These are product goals, not a claim that every feature of GINA or GamParse is already implemented. Use their established user-visible behavior as reference points when defining expected results. Keep the P99 implementation log-driven; do not add memory-reading or process-hooking approaches.

## Status key

- **Implemented:** code exists and is wired into the current user-facing path.
- **Partial / not wired:** some engine or widget code exists, but the feature is incomplete, unverified, or not displayed in the main dashboard.
- **Missing / planned:** the repository does not yet provide the complete user-facing behavior.

## What exists today

### Log ingestion and configuration — Implemented

- YAML configuration for character/server, log location and filename pattern, polling cadence, display settings, combat history, map settings, and custom triggers.
- Log-file tailing with handling for file rotation, truncation, and recreation.
- Timestamped parsing for combat actions, misses/defenses, heals, spell-cast start/resist/interrupt events, mob deaths, experience messages, item looting, coin-loot messages, zone messages, heading, and the standard `Your Location is Y, X, Z` output produced by `/loc`.
- Startup log catch-up for timer recovery in the main app and for recent location/zone state in the map app.
- A simulator entry point and automated tests for core parsing, map math/rendering, timers, DPS, and UI mounting.
- The intended data source is the client log file; code reviewed here does not attach to the game process or read game memory.

### Spell, buff, DoT and alert timers — Implemented / partial

- A timer engine, spell data, and timer categories for DoTs/debuffs/control effects, buffs/utilities, cooldowns, and respawn timers.
- Separate DoT and buff lists in the main dashboard, remaining-time display, progress bars, fade/recast warning states, and target-death cleanup.
- User-configurable regex triggers with custom timer duration, alert text, category, color, optional wear-off pattern, and sound flag.
- A live alert ticker that displays recent timer alerts or the latest log line.

**Gaps:** default trigger configuration is empty, so raid alerts depend on user configuration; a maintained, ready-to-use preset pack and broad spell/trigger coverage still need verification. Player-death and other parsed event types are not all routed through the main dashboard's event handler.

### Combat and DPS — Implemented / partial

- Active encounter tracking, combatant damage and DPS calculations, hit/miss and critical-hit counts, maximum hits, session damage totals, encounter history, healing totals, and damage taken/defensive event counters.
- The currently mounted DPS widget displays up to five combatants with DPS and a relative damage bar.

**Gaps:** the main dashboard does not yet show the complete GamParse-style breakdown. Damage share, accuracy, crit rate, max-hit comparison, pet/party filters, encounter history browsing/export, and clear multi-target semantics need to be completed and validated. The tank mitigation widget exists but is not mounted in the main dashboard.

### Standalone map / GPS — Implemented / partial

- A separate map window that consumes log updates, understands player location, zone changes and heading, and displays coordinates, travel speed, nearby points of interest, distances, and bearings.
- Vector map geometry and zone aliases, a player marker, breadcrumb trail, landmarks, manual zoom controls (1×–4×), zone cycling, breadcrumb clearing, and manual location input for testing.
- The map engine centers the view on the player while zoomed in.

**Gaps:** automatic first-fix zooming, manual zoom preservation, and clearing stale coordinates on zone changes are implemented. These behaviors still need broader real-log validation across zones and map-file variants.

### Kill, experience, loot and respawns — Partial / not wired

- The loot engine records kill totals and per-mob counts, recent kills, experience ticks, loot totals, item counts, and session-rate estimates (kills/hour and exp/hour).
- A kill/loot widget renders a session summary, recent loot, and frequently slain mobs.
- A spawn-timer database and respawn widget exist, and the timer engine can start respawn countdowns after a mob dies.

**Gaps:** the main dashboard currently does not mount the kill/loot or respawn widgets, so these features are not visible in the normal dashboard. The ledger also needs real-log validation for duplicate death messages, party attribution, coin-loot presentation, session resets, and rate calculations.

### Main dashboard and transparency — Partial

- The dashboard currently mounts the header, DoT list, DPS panel, alert ticker, and buff list.
- Textual CSS requests transparent backgrounds for the dashboard screen and panels.

**Gaps:** actual alpha transparency depends on the terminal emulator/compositor. The main app no longer forces the terminal background to black, and the README documents the terminal-side opacity settings. The mitigation, ledger, and respawn widgets still need to be laid out and mounted without making the overlay unwieldy.

## Prioritized roadmap

### P0 — Make the current feature set dependable

- [ ] Run the test suite and validate the merged transparency and auto-zoom behavior on a real P99 session, including startup with an existing log and a zone change.
- [ ] Add captured, anonymized real P99 log fixtures for location, zoning, spell fades, player death, coin loot, group combat, mob death, and item loot.
- [ ] Test the full startup sequence when the log file is missing, empty, already contains old data, or rotates while the app is running.
- [ ] Verify map coordinate orientation, zone aliases, and player centering against known in-game locations.
- [ ] Make event routing explicit so every parser event is either handled by an engine or intentionally ignored; connect player death and coin-loot handling where intended.

### P1 — Finish the promised core feature set

- [ ] Wire the existing **Tank Mitigation & Defense**, **Kill & Loot Ledger**, and **Respawns** widgets into the main dashboard; design a compact layout that still works in a narrow overlay.
- [ ] Complete the combat breakdown: per-combatant damage, DPS, share, accuracy, criticals, max hit, healing, incoming DPS, avoidance, and max damage taken, with formulas documented and tested.
- [ ] Improve encounter boundaries and attribution for pets, group members, multi-target fights, misses, heals, and mob-death messages.
- [ ] Ship useful default alert/trigger presets for high-value P99 events, and validate regexes against real logs. Preserve user override support and make sound behavior predictable.
- [ ] Validate the spell/timer data against P99 rules and actual log wording; document coverage and known exceptions instead of implying every spell is supported.
- [ ] Finish the loot ledger user experience: recent kills, per-mob counts, recent items and looter, coin, XP ticks, rate estimates, and a reliable session reset.
- [ ] Validate respawn estimates per zone/NPC type and clearly mark estimates versus observed spawn times.

### P2 — Improve usability and maintainability

- [ ] Add in-app or documented controls for enabling/disabling panels, resizing, compact mode, trigger editing, and safe log-path selection.
- [ ] Add robust terminal-launch options and document supported transparency / always-on-top behavior by terminal and compositor. Avoid silently changing the user's terminal colors.
- [ ] Add map controls for search/selection of nearby landmarks, breadcrumb persistence options, and a clear indication when location data becomes stale.
- [ ] Add import/export for encounters and loot summaries, with privacy-conscious local storage and no automatic log upload.
- [ ] Expand automated tests for malformed log lines, timestamp gaps, file rotation, unknown spells, zone changes, and numerical edge cases.
- [ ] Keep README claims synchronized with what is actually mounted, tested, and supported.

## Definition of done for feature parity

A feature is not considered complete solely because an engine or widget file exists. It should be wired into the intended UI, covered by representative automated tests, exercised against real P99 log samples, documented with its limitations, and verified not to rely on prohibited game-memory access.