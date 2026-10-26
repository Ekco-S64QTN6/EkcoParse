"""Log-driven vector map engine, Brewall map parser, and Braille subpixel wireframe renderer."""

import math
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional, Set, Tuple

from ekco_parse.models import Location
from ekco_parse.ui.theme import (
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_PURPLE,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_MUTED,
)


@dataclass
class MapPoint:
    """A Point of Interest (POI) or landmark in a zone."""
    name: str
    y: float                  # EQ /loc Y coordinate
    x: float                  # EQ /loc X coordinate
    z: float = 0.0            # EQ /loc Z coordinate
    category: str = "poi"     # "zoneline", "merchant", "trainer", "bank", "succor", "poi"
    symbol: str = "●"


@dataclass
class MapLine:
    """A vector line segment from Brewall map files."""
    x1: float
    y1: float
    z1: float
    x2: float
    y2: float
    z2: float
    layer: int = 0
    color_rgb: Tuple[int, int, int] = (100, 100, 100)


@dataclass
class ZoneData:
    """Cached vector map geometry and POIs for an EverQuest zone."""
    name: str
    short_name: str
    min_y: float
    max_y: float
    min_x: float
    max_x: float
    points: List[MapPoint] = field(default_factory=list)
    lines: List[MapLine] = field(default_factory=list)

    @property
    def width_x(self) -> float:
        return max(100.0, abs(self.max_x - self.min_x))

    @property
    def height_y(self) -> float:
        return max(100.0, abs(self.max_y - self.min_y))


# Zone name alias dictionary to map client zone strings to map filenames
ZONE_ALIASES: Dict[str, str] = {
    # Antonica
    "the arena": "arena", "arena": "arena",
    "ak`anon": "akanon", "akanon": "akanon",
    "befallen": "befallen",
    "gorge of king xorbb": "beholder", "beholder": "beholder",
    "blackburrow": "blackburrow",
    "west commonlands": "commons", "wcommons": "commons", "commons": "commons", "the commonlands": "commons",
    "east commonlands": "ecommons", "ecommons": "ecommons",
    "eastern plains of karana": "eastkarana", "east karana": "eastkarana",
    "everfrost peaks": "everfrost", "everfrost": "everfrost",
    "the feerrott": "feerrott", "feerrott": "feerrott",
    "east freeport": "freporte", "eastern freeport": "freporte",
    "north freeport": "freportn", "northern freeport": "freportn",
    "west freeport": "freportw", "western freeport": "freportw",
    "grobb": "grobb",
    "halas": "halas",
    "highpass hold": "highpass", "highpass": "highpass",
    "high keep": "highkeep", "highkeep": "highkeep",
    "innothule swamp": "innothule", "innothule": "innothule",
    "kithicor forest": "kithicor", "kithicor": "kithicor",
    "lake rathetear": "lakerathe", "lakerathe": "lakerathe",
    "lavastorm mountains": "lavastorm", "lavastorm": "lavastorm",
    "misty thicket": "misty", "misty": "misty",
    "najena": "najena",
    "nektulos forest": "nektulos", "nektulos": "nektulos",
    "neriak foreign quarter": "neriaka", "neriaka": "neriaka",
    "neriak commons": "neriakb", "neriakb": "neriakb",
    "neriak third gate": "neriakc", "neriakc": "neriakc",
    "northern plains of karana": "northkarana", "north karana": "northkarana",
    "northern desert of ro": "nro", "north ro": "nro", "nro": "nro",
    "oasis of marr": "oasis", "oasis": "oasis",
    "oggok": "oggok",
    "ocean of tears": "oot", "oot": "oot",
    "permafrost keep": "permafrost", "permafrost": "permafrost",
    "qeynos catacombs": "qcat", "qcat": "qcat",
    "western plains of karana": "qey2hh1", "west karana": "qey2hh1",
    "south qeynos": "qeynos", "qeynos": "qeynos",
    "north qeynos": "qeynos2", "qeynos2": "qeynos2",
    "qeynos hills": "qeytoqrg", "qeytoqrg": "qeytoqrg",
    "surefall glade": "qrg", "qrg": "qrg",
    "mountains of rathe": "rathemtn", "rathemtn": "rathemtn",
    "rivervale": "rivervale",
    "runnyeye citadel": "runnyeye", "clan runnyeye": "runnyeye", "runnyeye": "runnyeye",
    "solusek`s eye": "soldunga", "solusek a": "soldunga", "soldunga": "soldunga",
    "nagafen`s lair": "soldungb", "solusek b": "soldungb", "soldungb": "soldungb",
    "temple of solusek ro": "soltemple", "soltemple": "soltemple",
    "southern plains of karana": "southkarana", "south karana": "southkarana",
    "southern desert of ro": "sro", "south ro": "sro", "sro": "sro",
    "lair of the splitpaw": "splitpaw", "splitpaw": "splitpaw", "paw": "paw",
    "upper guk": "guktop", "guktop": "guktop",
    "lower guk": "gukbottom", "gukbottom": "gukbottom",
    # Faydwer
    "butcherblock mountains": "butcher", "butcherblock": "butcher", "butcher": "butcher",
    "dagnor`s cauldron": "cauldron", "cauldron": "cauldron",
    "crushbone": "crushbone",
    "northern felwithe": "felwithea", "felwithea": "felwithea",
    "southern felwithe": "felwitheb", "felwitheb": "felwitheb",
    "greater faydark": "gfaydark", "gfaydark": "gfaydark", "gfay": "gfaydark",
    "south kaladim": "kaladima", "kaladima": "kaladima",
    "north kaladim": "kaladimb", "kaladimb": "kaladimb",
    "kedge keep": "kedge", "kedge": "kedge",
    "lesser faydark": "lfaydark", "lfaydark": "lfaydark", "lfay": "lfaydark",
    "castle mistmoore": "mistmoore", "mistmoore": "mistmoore",
    "steamfont mountains": "steamfont", "steamfont": "steamfont",
    "estate of unrest": "unrest", "unrest": "unrest",
    # Odus
    "erudin": "erudnext", "erudnext": "erudnext",
    "erudin palace": "erudnint", "erudnint": "erudnint",
    "erud`s crossing": "erudsxing", "erudsxing": "erudsxing",
    "the hole": "hole", "hole": "hole",
    "kerra isle": "kerraridge", "kerra ridge": "kerraridge", "kerraridge": "kerraridge",
    "paineel": "paineel",
    "stonebrunt mountains": "stonebrunt", "stonebrunt": "stonebrunt",
    "toxxulia forest": "tox", "toxxulia": "tox", "tox": "tox",
    "the warrens": "warrens", "warrens": "warrens",
    # Planes
    "plane of sky": "airplane", "plane of air": "airplane", "airplane": "airplane",
    "plane of fear": "fearplane", "fearplane": "fearplane",
    "plane of hate": "hateplane", "hateplane": "hateplane",
    "plane of mischief": "mischiefplane", "mischiefplane": "mischiefplane",
    # Kunark
    "burning wood": "burningwood", "burningwood": "burningwood",
    "east cabilis": "cabeast", "cabeast": "cabeast",
    "west cabilis": "cabwest", "cabwest": "cabwest",
    "howling stones": "charasis", "charasis": "charasis",
    "chardok": "chardok",
    "city of mist": "citymist", "citymist": "citymist",
    "crypt of dalnir": "dalnir", "dalnir": "dalnir",
    "dreadlands": "dreadlands",
    "temple of droga": "droga", "droga": "droga",
    "emerald jungle": "emeraldjungle", "emeraldjungle": "emeraldjungle",
    "field of bone": "fieldofbone", "fieldofbone": "fieldofbone",
    "firiona vie": "firiona", "firiona": "firiona",
    "frontier mountains": "frontiermtns", "frontiermtns": "frontiermtns",
    "kaesora": "kaesora",
    "karnor`s castle": "karnor", "karnor": "karnor",
    "kurn`s tower": "kurn", "kurn": "kurn",
    "lake of ill omen": "lakeofillomen", "lakeofillomen": "lakeofillomen",
    "mines of nurga": "nurga", "nurga": "nurga",
    "the overthere": "overthere", "overthere": "overthere",
    "old sebilis": "sebilis", "sebilis": "sebilis",
    "skyfire mountains": "skyfire", "skyfire": "skyfire",
    "swamp of no hope": "swampofnohope", "swampofnohope": "swampofnohope",
    "timorous deep": "timorous", "timorous": "timorous",
    "trakanon`s teeth": "trakanon", "trakanon": "trakanon",
    "veeshan`s peak": "veeshan", "veeshan": "veeshan",
    "warsliks wood": "warslikswood", "warslikswood": "warslikswood",
    # Velious
    "cobalt scar": "cobaltscar", "cobaltscar": "cobaltscar",
    "crystal caverns": "crystal", "crystal": "crystal",
    "dragon necropolis": "dragonnec", "dragonnec": "dragonnec", "necropolis": "dragonnec",
    "eastern wastes": "eastwastes", "eastwastes": "eastwastes",
    "great divide": "greatdivide", "greatdivide": "greatdivide",
    "iceclad ocean": "iceclad", "iceclad": "iceclad",
    "kael drakkel": "kael", "kael": "kael",
    "siren`s grotto": "sirens", "sirens": "sirens",
    "skyshrine": "skyshrine",
    "sleeper`s tomb": "sleeper", "sleeper": "sleeper",
    "temple of veeshan": "templeveeshan", "templeveeshan": "templeveeshan",
    "thurgadin": "thurgadina", "thurgadina": "thurgadina",
    "icewell keep": "thurgadinb", "thurgadinb": "thurgadinb",
    "tower of frozen shadow": "tofs", "tofs": "tofs",
    "velketor`s labyrinth": "velketor", "velketor": "velketor",
    "the wakening land": "wakening", "wakening": "wakening",
    "western wastes": "westwastes", "westwastes": "westwastes",
}

# Bitmask table for 2x4 subpixel Braille dot matrix
BRAILLE_BITS = {
    (0, 0): 0x01,
    (0, 1): 0x02,
    (0, 2): 0x04,
    (0, 3): 0x40,
    (1, 0): 0x08,
    (1, 1): 0x10,
    (1, 2): 0x20,
    (1, 3): 0x80,
}


class BrailleCanvas:
    """Subpixel vector line drawing canvas using Unicode Braille (2x4 dots per character)."""

    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self.sub_w = cols * 2
        self.sub_h = rows * 4
        self.grid = [[0 for _ in range(cols)] for _ in range(rows)]

    def clear(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = 0

    def set_pixel(self, x: int, y: int) -> None:
        if 0 <= x < self.sub_w and 0 <= y < self.sub_h:
            c = x // 2
            r = y // 4
            bit = BRAILLE_BITS.get((x % 2, y % 4), 0)
            self.grid[r][c] |= bit

    def draw_line(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Bresenham's integer line algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.set_pixel(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy


class MapEngine:
    """Manages zone maps, coordinates, breadcrumbs, and vector wireframe rendering."""

    def __init__(
        self,
        maps_dir: Optional[Path] = None,
        default_zone: str = "Arena",
        max_breadcrumbs: int = 80,
    ):
        # Resolve map search directories (Priority: local project maps/ with Brewall pack, then P99 maps)
        base_dir = Path(__file__).resolve().parent.parent
        self.search_dirs: List[Path] = []
        if maps_dir:
            self.search_dirs.append(Path(maps_dir))
        self.search_dirs.append(base_dir / "maps")
        self.search_dirs.append(Path.home() / "Games" / "Project1999" / "maps")

        self.max_breadcrumbs = max_breadcrumbs
        self.active_zone_name: str = default_zone
        self.current_location: Optional[Location] = None
        self.current_heading: str = "North"
        self.breadcrumbs: Deque[Tuple[float, float, float]] = deque(maxlen=max_breadcrumbs)
        self.last_loc_time: Optional[datetime] = None
        self.current_speed: float = 0.0

        # Zone cache
        self.zones_cache: Dict[str, ZoneData] = {}
        self.load_active_zone(default_zone)

    def load_active_zone(self, zone_query: str) -> ZoneData:
        """Load complete multi-layer Brewall vector map data for zone."""
        key = zone_query.lower().strip()
        short_name = ZONE_ALIASES.get(key, key.replace(" ", "").replace("'", ""))

        if short_name in self.zones_cache and len(self.zones_cache[short_name].lines) > 0:
            self.active_zone_name = self.zones_cache[short_name].name
            return self.zones_cache[short_name]

        # Scan search directories for map files
        loaded = self._load_brewall_zone(short_name, zone_query)
        if loaded:
            self.zones_cache[short_name] = loaded
            self.active_zone_name = loaded.name
            return loaded

        # Fallback to Arena or basic bounds
        fb = ZoneData(
            name=zone_query.title(),
            short_name=short_name,
            min_y=-1000, max_y=1000,
            min_x=-1000, max_x=1000,
        )
        self.zones_cache[short_name] = fb
        self.active_zone_name = fb.name
        return fb

    def _load_brewall_zone(self, short_name: str, full_name: str) -> Optional[ZoneData]:
        """Load and merge all layers: <zone>.txt, <zone>_1.txt, <zone>_2.txt, <zone>_3.txt."""
        points: List[MapPoint] = []
        lines: List[MapLine] = []

        min_y, max_y = 999999.0, -999999.0
        min_x, max_x = 999999.0, -999999.0

        found_any = False

        for d in self.search_dirs:
            if not d.exists():
                continue

            # Look for base file and layers
            layer_files = [
                (d / f"{short_name}.txt", 0),
                (d / f"{short_name}_1.txt", 1),
                (d / f"{short_name}_2.txt", 2),
                (d / f"{short_name}_3.txt", 3),
            ]

            for file_path, layer_num in layer_files:
                if not file_path.exists() or file_path.stat().st_size == 0:
                    continue

                found_any = True
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            # Line segment: L x1, y1, z1, x2, y2, z2, r, g, b
                            if line.startswith("L "):
                                parts = [p.strip() for p in line[2:].split(",")]
                                if len(parts) >= 6:
                                    p0, p1 = float(parts[0]), float(parts[1])
                                    p3, p4 = float(parts[3]), float(parts[4])
                                    # Convert EQ map coords (-X, -Y) to /loc (X, Y)
                                    x1, y1 = -p0, -p1
                                    x2, y2 = -p3, -p4

                                    min_x = min(min_x, x1, x2)
                                    max_x = max(max_x, x1, x2)
                                    min_y = min(min_y, y1, y2)
                                    max_y = max(max_y, y1, y2)

                                    lines.append(MapLine(
                                        x1=x1, y1=y1, z1=float(parts[2]),
                                        x2=x2, y2=y2, z2=float(parts[5]),
                                        layer=layer_num,
                                    ))

                            # Point of Interest: P x, y, z, r, g, b, size, label
                            elif line.startswith("P "):
                                parts = [p.strip() for p in line[2:].split(",")]
                                if len(parts) >= 8:
                                    loc_x = -float(parts[0])
                                    loc_y = -float(parts[1])
                                    loc_z = float(parts[2])
                                    label = parts[7].replace("_", " ").strip()

                                    min_x = min(min_x, loc_x)
                                    max_x = max(max_x, loc_x)
                                    min_y = min(min_y, loc_y)
                                    max_y = max(max_y, loc_y)

                                    cat = "poi"
                                    lbl_low = label.lower()
                                    if "to " in lbl_low or "zone" in lbl_low or "lake" in lbl_low:
                                        cat = "zoneline"
                                    elif "merchant" in lbl_low or "spells" in lbl_low:
                                        cat = "merchant"
                                    elif "bank" in lbl_low or "soulbinder" in lbl_low:
                                        cat = "bank"
                                    elif "succor" in lbl_low:
                                        cat = "succor"

                                    points.append(MapPoint(
                                        name=label,
                                        y=loc_y,
                                        x=loc_x,
                                        z=loc_z,
                                        category=cat,
                                    ))
                except Exception as e:
                    print(f"[MapEngine] Error reading {file_path}: {e}")

            if found_any:
                break

        if found_any and (lines or points):
            return ZoneData(
                name=full_name.title(),
                short_name=short_name,
                min_y=min_y if min_y < max_y else -1000,
                max_y=max_y if min_y < max_y else 1000,
                min_x=min_x if min_x < max_x else -1000,
                max_x=max_x if min_x < max_x else 1000,
                points=points,
                lines=lines,
            )

        return None

    def update_location(self, loc: Location) -> None:
        """Process new /loc coordinate reading."""
        now = loc.timestamp or datetime.now()

        if self.current_location and self.last_loc_time:
            dt = (now - self.last_loc_time).total_seconds()
            if 0.1 <= dt <= 15.0:
                dy = loc.y - self.current_location.y
                dx = loc.x - self.current_location.x
                dist = math.sqrt(dx * dx + dy * dy)
                self.current_speed = round(dist / dt, 1)

        self.last_loc_time = now
        self.current_location = loc
        self.breadcrumbs.append((loc.y, loc.x, loc.z))

    def update_heading(self, heading: str) -> None:
        self.current_heading = heading.strip().capitalize()

    def set_zone(self, zone_name: str) -> None:
        self.load_active_zone(zone_name)
        self.breadcrumbs.clear()

    def get_nearby_pois(self, limit: int = 10) -> List[Tuple[MapPoint, float, str]]:
        """Return POIs sorted by distance to player with bearing."""
        zone = self.zones_cache.get(
            ZONE_ALIASES.get(self.active_zone_name.lower(), self.active_zone_name.lower()),
        )
        if not zone or not zone.points:
            return []

        py = self.current_location.y if self.current_location else 0.0
        px = self.current_location.x if self.current_location else 0.0

        results = []
        for p in zone.points:
            dy = p.y - py
            dx = p.x - px
            dist = math.sqrt(dy * dy + dx * dx)
            bearing = self._calc_bearing(dy, dx)
            results.append((p, dist, bearing))

        results.sort(key=lambda item: item[1])
        return results[:limit]

    def _calc_bearing(self, dy: float, dx: float) -> str:
        """Calculate compass bearing (N, NE, E, SE, S, SW, W, NW)."""
        angle = math.degrees(math.atan2(-dx, dy))
        if angle < 0:
            angle += 360

        compass_sectors = [
            (22.5, "N"), (67.5, "NE"), (112.5, "E"), (157.5, "SE"),
            (202.5, "S"), (247.5, "SW"), (292.5, "W"), (337.5, "NW"),
            (360.0, "N"),
        ]
        for limit, name in compass_sectors:
            if angle <= limit:
                return name
        return "N"

    def render_vector_wireframe(
        self,
        cols: int = 60,
        rows: int = 22,
        zoom: float = 1.0,
    ) -> List[str]:
        """
        Renders true vector wireframe structural map using subpixel Braille dots.
        Eliminates solid white raster backgrounds entirely for a dark vector look.
        """
        zone = self.zones_cache.get(
            ZONE_ALIASES.get(self.active_zone_name.lower(), self.active_zone_name.lower()),
        )
        if not zone:
            return ["[grey37]No vector geometry loaded for this zone.[/]"]

        canvas = BrailleCanvas(cols=cols, rows=rows)
        sub_w = canvas.sub_w
        sub_h = canvas.sub_h

        min_y, max_y = zone.min_y, zone.max_y
        min_x, max_x = zone.min_x, zone.max_x

        # Zoom centering on player
        if self.current_location and zoom > 1.0:
            span_y = (max_y - min_y) / zoom
            span_x = (max_x - min_x) / zoom
            center_y, center_x = self.current_location.y, self.current_location.x
            min_y = center_y - span_y / 2
            max_y = center_y + span_y / 2
            min_x = center_x - span_x / 2
            max_x = center_x + span_x / 2

        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)

        def to_subpixel(x: float, y: float) -> Tuple[int, int]:
            # EQ coordinates: +Y is North (top), +X is West (left in in-game map coordinates)
            # In our loc conversion: loc_x is West, so smaller x is East
            sx = int(((x - min_x) / span_x) * (sub_w - 1))
            sy = int(((max_y - y) / span_y) * (sub_h - 1))
            return sx, sy

        def to_char_cell(x: float, y: float) -> Optional[Tuple[int, int]]:
            c = int(((x - min_x) / span_x) * (cols - 1))
            r = int(((max_y - y) / span_y) * (rows - 1))
            if 0 <= r < rows and 0 <= c < cols:
                return r, c
            return None

        # 1. Rasterize vector line segments (walls, coliseum, tunnels, perimeters)
        for ml in zone.lines:
            sx1, sy1 = to_subpixel(ml.x1, ml.y1)
            sx2, sy2 = to_subpixel(ml.x2, ml.y2)
            canvas.draw_line(sx1, sy1, sx2, sy2)

        # 2. Draw breadcrumb subpixels
        for by, bx, _ in self.breadcrumbs:
            bsx, bsy = to_subpixel(bx, by)
            canvas.set_pixel(bsx, bsy)

        # 3. Locate character-cell overlays for POIs and Player
        overlays: Dict[Tuple[int, int], str] = {}

        # POI markers
        for idx, pt in enumerate(zone.points):
            coords = to_char_cell(pt.x, pt.y)
            if coords:
                r, c = coords
                if pt.category == "zoneline":
                    overlays[(r, c)] = f"[bold {COLOR_CYAN}]Z[/]"
                elif pt.category == "merchant":
                    overlays[(r, c)] = f"[bold {COLOR_AMBER}]M[/]"
                elif pt.category == "bank":
                    overlays[(r, c)] = f"[bold {COLOR_GREEN}]B[/]"
                elif pt.category == "succor":
                    overlays[(r, c)] = f"[bold {COLOR_PURPLE}]S[/]"
                else:
                    overlays[(r, c)] = f"[bold {COLOR_MAGENTA}]●[/]"

        # Player location marker
        if self.current_location:
            coords = to_char_cell(self.current_location.x, self.current_location.y)
            if coords:
                overlays[coords] = f"[bold {COLOR_GREEN} on #05070D]@[/]"

        # 4. Convert Braille subpixel grid to Rich markup rows
        rendered_rows = []
        for r in range(rows):
            row_items = []
            for c in range(cols):
                if (r, c) in overlays:
                    row_items.append(overlays[(r, c)])
                else:
                    bits = canvas.grid[r][c]
                    if bits > 0:
                        ch = chr(0x2800 + bits)
                        row_items.append(f"[bold {COLOR_CYAN}]{ch}[/]")
                    else:
                        row_items.append(" ")
            rendered_rows.append("".join(row_items))

        return rendered_rows
