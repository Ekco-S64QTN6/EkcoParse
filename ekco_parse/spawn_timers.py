"""Zone spawn timer database for Project 1999 EverQuest.

Data sourced from https://wiki.project1999.com/Zone_Spawn_Timer
Timers are in seconds. Each zone maps to its default NPC respawn time.
"""

from typing import Dict, Optional


# Zone name (as it appears in-game / log) -> default respawn time in seconds
# Organized by continent per the P99 wiki
ZONE_SPAWN_TIMERS: Dict[str, int] = {
    # ── Antonica ──────────────────────────────────────────────────
    "East Commonlands": 400,           # 6:40
    "West Commonlands": 400,           # 6:40
    "North Freeport": 1440,            # 24:00
    "West Freeport": 1440,             # 24:00
    "East Freeport": 1440,             # 24:00
    "Freeport": 1440,                  # 24:00
    "Northern Plains of Karana": 400,   # 6:40
    "Southern Plains of Karana": 360, # 6:00
    "Western Plains of Karana": 400,    # 6:40
    "Eastern Plains of Karana": 400,    # 6:40
    "Qeynos Hills": 400,               # 6:40
    "North Qeynos": 400,          # 6:40
    "South Qeynos": 400,          # 6:40
    "Surefall Glade": 400,        # 6:40
    "Halas": 1440,                     # 24:00
    "Everfrost Peaks": 400,            # 6:40
    "Blackburrow": 1320,               # 22:00
    "Highpass Hold": 400,               # 6:40
    "High Keep": 600,                   # 10:00 (varies by area)
    "Kithicor Forest": 400,            # 6:40
    "Rivervale": 1320,            # 22:00
    "Misty Thicket": 400,              # 6:40
    "Runnyeye Citadel": 1320,          # 22:00
    "Befallen": 1140,                  # 19:00
    "Gorge of King Xorbb": 400,        # 6:40 (Beholder's Maze)
    "Rathe Mountains": 400,            # 6:40
    "Lake Rathetear": 400,             # 6:40
    "Arena": 400,                      # 6:40
    "Lavastorm Mountains": 400,        # 6:40
    "Solusek's Eye": 1080,             # 18:00 (Sol A)
    "Nagafen's Lair": 1320,            # 22:00 (Sol B)
    "Permafrost Keep": 1320,           # 22:00
    "Najena": 1110,                    # 18:30
    "South Ro": 400,                   # 6:40
    "North Ro": 400,                   # 6:40
    "Oasis of Marr": 990,         # 16:30
    "Innothule Swamp": 400,            # 6:40
    "Grobb": 1440,                     # 24:00
    "Oggok": 1440,                     # 24:00
    "Feerrott": 400,                   # 6:40
    "Cazic-Thule": 1320,               # 22:00
    "Neriak Foreign Quarter": 1440,    # 24:00
    "Neriak Commons": 1440,            # 24:00
    "Neriak Third Gate": 1440,         # 24:00
    "Nektulos Forest": 400,            # 6:40
    "Upper Guk": 990,                  # 16:30
    "Lower Guk": 1680,                 # 28:00
    "Unrest": 1320,                    # 22:00
    "Estate of Unrest": 1320,          # 22:00
    "Infected Paw": 1320,              # 22:00
    "Splitpaw Lair": 1320,             # 22:00
    "Plane of Fear": 28800,       # 8:00:00
    "Plane of Hate": 28800,       # 8:00:00
    "Plane of Sky": 28800,        # 8:00:00
    "Plane of Air": 1680,              # 28:00

    # ── Faydwer ───────────────────────────────────────────────────
    "Greater Faydark": 425,       # 7:05
    "Lesser Faydark": 390,        # 6:30
    "Butcherblock Mountains": 400,     # 6:40
    "Ocean of Tears": 360,        # 6:00
    "Felwithe": 1440,                  # 24:00
    "Kaladim": 400,               # 6:40
    "Ak'Anon": 400,               # 6:40
    "Steamfont Mountains": 400,        # 6:40
    "Crushbone": 540,             # 9:00
    "Castle Mistmoore": 1320,          # 22:00
    "Kedge Keep": 1320,                # 22:00
    "Dagnor's Cauldron": 400,          # 6:40

    # ── Odus ──────────────────────────────────────────────────────
    "Erudin": 1500,                    # 25:00
    "Erudin Palace": 1500,             # 25:00
    "Toxxulia Forest": 400,            # 6:40
    "Paineel": 630,                    # 10:30
    "The Hole": 1290,             # 21:30
    "Stonebrunt Mountains": 670,  # 11:10
    "Warrens": 400,               # 6:40

    # ── Kunark ────────────────────────────────────────────────────
    "Firiona Vie": 400,                # 6:40
    "Field of Bone": 400,              # 6:40
    "Cabilis East": 400,          # 6:40
    "Cabilis West": 400,          # 6:40
    "Swamp of No Hope": 400,           # 6:40
    "Lake of Ill Omen": 400,           # 6:40
    "Warsliks Woods": 400,             # 6:40
    "Frontier Mountains": 400,         # 6:40
    "Overthere": 400,                  # 6:40
    "Dreadlands": 400,                 # 6:40
    "Burning Wood": 400,               # 6:40
    "Trakanon's Teeth": 400,           # 6:40
    "Emerald Jungle": 400,             # 6:40
    "City of Mist": 1320,              # 22:00
    "Kurn's Tower": 1100,         # 18:20
    "Kaesora": 1080,              # 18:00
    "Mines of Nurga": 1230,       # 20:30
    "Temple of Droga": 1230,      # 20:30
    "Chardok": 1080,              # 18:00
    "Howling Stones": 1230,       # 20:30
    "Charasis": 1230,             # 20:30
    "Old Sebilis": 1620,          # 27:00
    "Sebilis": 1620,              # 27:00
    "Veeshan's Peak": 1680,            # 28:00

    # ── Velious ───────────────────────────────────────────────────
    "Iceclad Ocean": 400,              # 6:40
    "Eastern Wastes": 400,             # 6:40
    "Great Divide": 640,          # 10:40
    "Cobalt Scar": 1200,          # 20:00
    "Wakening Land": 400,              # 6:40
    "Skyshrine": 1800,            # 30:00
    "Kael Drakkal": 1680,         # 28:00
    "Thurgadin": 420,             # 7:00
    "Icewell Keep": 1260,         # 21:00
    "Crystal Caverns": 885,       # 14:45
    "Velketor's Labyrinth": 1970, # 32:50
    "Tower of Frozen Shadow": 1200, # 20:00
    "Dragon Necropolis": 1620,    # 27:00
    "Siren's Grotto": 1680,       # 28:00
    "Western Wastes": 400,             # 6:40
    "Temple of Veeshan": 259200,  # 72:00:00
    "Sleeper's Tomb": 28800,      # 8:00:00
    "Plane of Growth": 43200,     # 12:00:00
    "Plane of Mischief": 4210,    # 1:10:10
}

# Aliases for zone name normalization
ZONE_ALIASES: Dict[str, str] = {
    "sol a": "Solusek's Eye",
    "sol b": "Nagafen's Lair",
    "guk": "Lower Guk",
    "lguk": "Lower Guk",
    "uguk": "Upper Guk",
    "hate": "Plane of Hate",
    "fear": "Plane of Fear",
    "sky": "Plane of Sky",
    "ct": "Cazic-Thule",
    "mistmoore": "Castle Mistmoore",
    "mm": "Castle Mistmoore",
    "hs": "Howling Stones",
    "seb": "Old Sebilis",
    "chardok": "Chardok",
    "kael": "Kael Drakkal",
    "tov": "Temple of Veeshan",
    "nt": "Neriak Third Gate",
    "nro": "North Ro",
    "sro": "South Ro",
    "ec": "East Commonlands",
    "wc": "West Commonlands",
    "nk": "Northern Plains of Karana",
    "sk": "Southern Plains of Karana",
    "wk": "Western Plains of Karana",
    "ek": "Eastern Plains of Karana",
    "oot": "Ocean of Tears",
    "bb": "Butcherblock Mountains",
    "gfay": "Greater Faydark",
    "lfay": "Lesser Faydark",
    "sfm": "Steamfont Mountains",
    "cb": "Crushbone",
    "hk": "High Keep",
    "sol b": "Nagafen's Lair",
    "vp": "Veeshan's Peak",
}


def get_zone_respawn_seconds(zone_name: str) -> int:
    """Get the default respawn timer in seconds for a zone.

    Returns 400 (6:40 outdoor default) if zone is unknown.
    """
    if not zone_name:
        return 400

    # Exact match first
    if zone_name in ZONE_SPAWN_TIMERS:
        return ZONE_SPAWN_TIMERS[zone_name]

    # Case-insensitive match
    zone_low = zone_name.strip().lower()
    for zname, timer in ZONE_SPAWN_TIMERS.items():
        if zname.lower() == zone_low:
            return timer

    # Check aliases
    if zone_low in ZONE_ALIASES:
        alias_name = ZONE_ALIASES[zone_low]
        return ZONE_SPAWN_TIMERS.get(alias_name, 400)

    # Partial match
    for zname, timer in ZONE_SPAWN_TIMERS.items():
        if zone_low in zname.lower() or zname.lower() in zone_low:
            return timer

    # Default outdoor timer
    return 400


def format_spawn_time(seconds: int) -> str:
    """Format seconds as MM:SS for display."""
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"
