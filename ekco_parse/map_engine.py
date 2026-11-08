"""Log-driven vector map engine, Brewall map parser, and Braille subpixel wireframe renderer."""

import math
import os
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional, Set, Tuple

import yaml
from rich.markup import escape

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
    key: str = ""             # wiki map-key marker ("1", "A", "Z"); drawn on the radar


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


# Named colors a waypoint file may use for spots and shapes.
MARK_COLORS: Dict[str, str] = {
    "red": COLOR_RED,
    "amber": COLOR_AMBER,
    "green": COLOR_GREEN,
    "cyan": COLOR_CYAN,
    "magenta": COLOR_MAGENTA,
    "purple": COLOR_PURPLE,
    "blue": "#4D7CFF",
    "white": "#FFFFFF",
    "muted": COLOR_MUTED,
}


def _mark_color(name: object, default: str) -> str:
    return MARK_COLORS.get(str(name or "").strip().lower(), MARK_COLORS[default])


@dataclass
class MapSpot:
    """A small hand-placed dot (e.g. a known rare spawn spot), smaller than a waypoint."""
    name: str
    y: float
    x: float
    color: str = COLOR_RED


@dataclass
class MapShape:
    """An outline drawn over the map: a circle or an axis-aligned box, in /loc units."""
    kind: str                 # "circle" or "rect"
    color: str
    name: str = ""
    y: float = 0.0            # circle centre
    x: float = 0.0
    radius: float = 0.0
    north: float = 0.0        # rect edges: north/south are /loc Y, west/east are /loc X
    south: float = 0.0
    west: float = 0.0
    east: float = 0.0

    def polyline(self, units_per_dot: float) -> List[Tuple[float, float]]:
        """Closed outline as (x, y) world points; circles get enough sides to look round."""
        if self.kind == "rect":
            return [
                (self.west, self.north), (self.east, self.north),
                (self.east, self.south), (self.west, self.south), (self.west, self.north),
            ]
        r_dots = self.radius / max(units_per_dot, 1e-6)
        n = int(min(720, max(24, 2 * math.pi * r_dots / 3)))
        return [
            (self.x + self.radius * math.cos(2 * math.pi * i / n),
             self.y + self.radius * math.sin(2 * math.pi * i / n))
            for i in range(n + 1)
        ]


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
    spots: List[MapSpot] = field(default_factory=list)
    shapes: List[MapShape] = field(default_factory=list)

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
    "lair of the splitpaw": "paw", "splitpaw": "paw", "paw": "paw",
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
    "dragon necropolis": "necropolis", "dragonnec": "necropolis", "necropolis": "necropolis",
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
        """Load and merge all layers: <zone>.txt, <zone>_1.txt, <zone>_2.txt, <zone>_3.txt.

        Brewall packs ship a legend layer (compass rose, scale bar, credits and
        a mob list drawn as line-art below the map); that layer is skipped, as
        are ground-spawn and credit labels. The zone's bounds come from its
        walls only, so stray labels never shrink the map.
        """
        points: List[MapPoint] = []
        lines: List[MapLine] = []
        found_any = False

        for d in self.search_dirs:
            if not d.exists():
                continue

            for layer_num, suffix in enumerate(("", "_1", "_2", "_3")):
                file_path = d / f"{short_name}{suffix}.txt"
                if not file_path.exists() or file_path.stat().st_size == 0:
                    continue
                found_any = True
                try:
                    file_lines, file_points = _parse_map_file(file_path, layer_num)
                except OSError as e:
                    print(f"[MapEngine] Error reading {file_path}: {e}")
                    continue
                if _is_legend_layer(file_points):
                    continue
                lines.extend(file_lines)
                points.extend(p for p in file_points if not _is_junk_label(p.name))

            if found_any:
                break

        curated = load_waypoints(short_name)
        if curated is not None:
            points = curated
        spots, shapes = load_markings(short_name)

        if not (found_any and (lines or points)):
            return None

        xs = [v for ml in lines for v in (ml.x1, ml.x2)] or [p.x for p in points]
        ys = [v for ml in lines for v in (ml.y1, ml.y2)] or [p.y for p in points]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        if lines:
            # Drop labels that sit outside the walls (legend lists, credits).
            pad = 0.05 * max(max_x - min_x, max_y - min_y)
            points = [
                p for p in points
                if min_x - pad <= p.x <= max_x + pad and min_y - pad <= p.y <= max_y + pad
            ]
        return ZoneData(
            name=full_name.title(),
            short_name=short_name,
            min_y=min_y if min_y < max_y else -1000,
            max_y=max_y if min_y < max_y else 1000,
            min_x=min_x if min_x < max_x else -1000,
            max_x=max_x if min_x < max_x else 1000,
            points=points,
            lines=lines,
            spots=spots,
            shapes=shapes,
        )

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
        zone = self._active_zone_data()
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

    # Closest allowed view: this many world units per Braille dot. At 0.5 a
    # 56-column radar is ~56 units across — tight enough for dungeon corridors.
    MIN_UNITS_PER_DOT = 0.5

    def _active_zone_data(self) -> Optional[ZoneData]:
        return self.zones_cache.get(
            ZONE_ALIASES.get(self.active_zone_name.lower(), self.active_zone_name.lower()),
        )

    def fit_units_per_dot(self, cols: int, rows: int) -> float:
        """World units per Braille dot when the whole zone fits the radar (zoom 1x)."""
        zone = self._active_zone_data()
        if not zone:
            return 10.0
        sub_w, sub_h = max(2, cols * 2), max(4, rows * 4)
        # Braille dots are roughly square (2x4 per ~1:2 cell), so one uniform
        # scale keeps the zone's true shape instead of stretching each axis.
        return max(zone.width_x / (sub_w - 1), zone.height_y / (sub_h - 1))

    def max_zoom(self, cols: int, rows: int) -> float:
        return max(1.0, self.fit_units_per_dot(cols, rows) / self.MIN_UNITS_PER_DOT)

    def view_width_units(self, cols: int, rows: int, zoom: float) -> float:
        """How many world units the radar spans left-to-right at this zoom."""
        return self.fit_units_per_dot(cols, rows) / max(1.0, zoom) * cols * 2

    def render_vector_wireframe(
        self,
        cols: int = 60,
        rows: int = 22,
        zoom: float = 1.0,
    ) -> List[str]:
        """
        Renders the zone as a vector wireframe using subpixel Braille dots.

        North is up and east is right, like the in-game map. Zoom 1x fits the
        whole zone; above that the view is centred on the player.
        """
        zone = self._active_zone_data()
        if not zone:
            return ["[grey37]No vector geometry loaded for this zone.[/]"]

        canvas = BrailleCanvas(cols=cols, rows=rows)
        sub_w = canvas.sub_w
        sub_h = canvas.sub_h

        zoom = min(max(1.0, zoom), self.max_zoom(cols, rows))
        upd = self.fit_units_per_dot(cols, rows) / zoom  # world units per dot

        if self.current_location and zoom > 1.0:
            center_y, center_x = self.current_location.y, self.current_location.x
        else:
            center_y = (zone.min_y + zone.max_y) / 2
            center_x = (zone.min_x + zone.max_x) / 2

        # /loc X grows to the WEST, so screen-right (east) is decreasing X.
        left_x = center_x + upd * (sub_w - 1) / 2
        top_y = center_y + upd * (sub_h - 1) / 2
        inv = 1.0 / upd

        def to_sub(x: float, y: float) -> Tuple[float, float]:
            return (left_x - x) * inv, (top_y - y) * inv

        def to_char_cell(x: float, y: float) -> Optional[Tuple[int, int]]:
            fx, fy = to_sub(x, y)
            c, r = int(round(fx)) // 2, int(round(fy)) // 4
            if 0 <= r < rows and 0 <= c < cols and fx >= -0.5 and fy >= -0.5:
                return r, c
            return None

        max_x, max_y = sub_w - 1, sub_h - 1

        # 1. Rasterize vector line segments, clipped to the view so zoomed-in
        #    renders never walk thousands of off-screen dots.
        for ml in zone.lines:
            x0, y0 = to_sub(ml.x1, ml.y1)
            x1, y1 = to_sub(ml.x2, ml.y2)
            clipped = _clip_segment(x0, y0, x1, y1, max_x, max_y)
            if clipped:
                a, b, c, d = clipped
                canvas.draw_line(int(round(a)), int(round(b)), int(round(c)), int(round(d)))

        # Outlines (circles, boxes) go on their own canvases so they keep
        # their color instead of blending into the cyan walls.
        shape_layers: List[Tuple[str, BrailleCanvas]] = []
        layer_by_color: Dict[str, BrailleCanvas] = {}
        for sh in zone.shapes:
            layer = layer_by_color.get(sh.color)
            if layer is None:
                layer = layer_by_color[sh.color] = BrailleCanvas(cols=cols, rows=rows)
                shape_layers.append((sh.color, layer))
            pts = [to_sub(x, y) for x, y in sh.polyline(upd)]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                clipped = _clip_segment(x0, y0, x1, y1, max_x, max_y)
                if clipped:
                    a, b, c, d = clipped
                    layer.draw_line(int(round(a)), int(round(b)), int(round(c)), int(round(d)))

        # 2. Draw breadcrumb subpixels
        for by, bx, _ in self.breadcrumbs:
            fx, fy = to_sub(bx, by)
            canvas.set_pixel(int(round(fx)), int(round(fy)))

        # 3. Locate character-cell overlays for POIs and Player
        overlays: Dict[Tuple[int, int], str] = {}

        # Spots first, so waypoints and the player marker win a shared cell.
        for sp in zone.spots:
            coords = to_char_cell(sp.x, sp.y)
            if coords:
                overlays[coords] = f"[{sp.color}]•[/]"

        for pt in zone.points:
            coords = to_char_cell(pt.x, pt.y)
            if coords:
                if pt.key and pt.category != "zoneline":
                    # Wiki map-key marker; "12" spills into the next cell.
                    r, c = coords
                    for i, ch in enumerate(pt.key[:2]):
                        if c + i < cols:
                            overlays[(r, c + i)] = f"[bold {COLOR_MAGENTA}]{escape(ch)}[/]"
                elif pt.category == "zoneline":
                    overlays[coords] = f"[bold {COLOR_CYAN}]Z[/]"
                elif pt.category == "merchant":
                    overlays[coords] = f"[bold {COLOR_AMBER}]M[/]"
                elif pt.category == "bank":
                    overlays[coords] = f"[bold {COLOR_GREEN}]B[/]"
                elif pt.category == "succor":
                    overlays[coords] = f"[bold {COLOR_PURPLE}]S[/]"
                else:
                    overlays[coords] = f"[bold {COLOR_MAGENTA}]●[/]"

        if self.current_location:
            coords = to_char_cell(self.current_location.x, self.current_location.y)
            if coords:
                overlays[coords] = f"[bold {COLOR_GREEN} on #05070D]@[/]"

        # 4. Convert the Braille grid to Rich markup, one tag per run of
        #    same-colored glyphs rather than one per character. A cell an
        #    outline passes through takes the outline's color.
        rendered_rows = []
        for r in range(rows):
            parts: List[str] = []
            run: List[str] = []
            run_color: Optional[str] = None
            grid_row = canvas.grid[r]
            for c in range(cols):
                ov = overlays.get((r, c))
                bits = grid_row[c]
                color = COLOR_CYAN
                for shape_color, layer in shape_layers:
                    if layer.grid[r][c]:
                        bits |= layer.grid[r][c]
                        color = shape_color
                        break
                if ov is None and bits:
                    if run and color != run_color:
                        parts.append(f"[bold {run_color}]{''.join(run)}[/]")
                        run = []
                    run_color = color
                    run.append(chr(0x2800 + bits))
                    continue
                if run:
                    parts.append(f"[bold {run_color}]{''.join(run)}[/]")
                    run = []
                parts.append(ov if ov is not None else " ")
            if run:
                parts.append(f"[bold {run_color}]{''.join(run)}[/]")
            rendered_rows.append("".join(parts))

        return rendered_rows


# Curated waypoints, one YAML file per zone, built from the P99 wiki's Map
# Location Keys. When a zone has one, it replaces the map files' own labels.
WAYPOINTS_DIR = Path(__file__).resolve().parent.parent / "maps" / "waypoints"

# Labels in community map packs that are never worth a waypoint: ground
# spawns, map credits, crafting stations, traps and post-Velious content.
_JUNK_LABEL = re.compile(
    r"^(gs:|ground spawn)|eqmaps|roteguild|brewall|original map|revised map"
    r"|height filter|^\W*$|^\d+$|^(lvl|from)$|plane of knowledge|priest of discord"
    r"|\(research\)|^(forge|oven|kiln|loom|brew(ing)? barrel|pottery wheel)$"
    r"|^trap\b|fake (wall|floor)",
    re.IGNORECASE,
)
# A legend layer carries the map credits; real layers never do.
_LEGEND_LABEL = re.compile(r"eqmaps\.info|brewall|original map|revised map|height filter", re.IGNORECASE)


def _is_junk_label(name: str) -> bool:
    return bool(_JUNK_LABEL.search(name.strip()))


def _is_legend_layer(points: List[MapPoint]) -> bool:
    return any(_LEGEND_LABEL.search(p.name) for p in points)


def _label_category(label: str) -> str:
    low = label.lower()
    if low.startswith("to ") or " zone" in low:
        return "zoneline"
    if "bank" in low:
        return "bank"
    if "succor" in low:
        return "succor"
    return "poi"


def _parse_map_file(file_path: Path, layer_num: int) -> Tuple[List[MapLine], List[MapPoint]]:
    """Parse one Brewall/EQ map file. Map coords are (-/loc X, -/loc Y)."""
    lines: List[MapLine] = []
    points: List[MapPoint] = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            raw = raw.strip()
            try:
                # Line segment: L x1, y1, z1, x2, y2, z2, r, g, b
                if raw.startswith("L "):
                    parts = raw[2:].split(",")
                    if len(parts) >= 6:
                        lines.append(MapLine(
                            x1=-float(parts[0]), y1=-float(parts[1]), z1=float(parts[2]),
                            x2=-float(parts[3]), y2=-float(parts[4]), z2=float(parts[5]),
                            layer=layer_num,
                        ))
                # Point of Interest: P x, y, z, r, g, b, size, label
                elif raw.startswith("P "):
                    parts = raw[2:].split(",", 7)
                    if len(parts) >= 8:
                        label = parts[7].replace("_", " ").strip()
                        points.append(MapPoint(
                            name=label,
                            x=-float(parts[0]), y=-float(parts[1]), z=float(parts[2]),
                            category=_label_category(label),
                        ))
            except ValueError:
                continue
    return lines, points


def load_waypoints(short_name: str, directory: Optional[Path] = None) -> Optional[List[MapPoint]]:
    """Curated waypoints for a zone, or None if the zone has no waypoint file.

    Each entry is {key, name, y, x} in /loc coordinates; key "Z" marks a zone
    line, anything else (1, 2, A...) is the wiki map key's marker.
    """
    path = (directory or WAYPOINTS_DIR) / f"{short_name}.yaml"
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"[MapEngine] Error reading {path}: {e}")
        return None
    points: List[MapPoint] = []
    for wp in data.get("waypoints") or []:
        try:
            key = str(wp.get("key", "")).strip()
            points.append(MapPoint(
                name=str(wp["name"]),
                y=float(wp["y"]),
                x=float(wp["x"]),
                category="zoneline" if key == "Z" else "poi",
                key=key,
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return points


def load_markings(
    short_name: str, directory: Optional[Path] = None
) -> Tuple[List[MapSpot], List[MapShape]]:
    """Read a zone's optional `spots:` and `shapes:` from its waypoint YAML.

    spots:  [{name, y, x, color?}]  small dots, drawn in file order (later wins a cell)
    shapes: [{kind: circle, y, x, radius, color?}]
            [{kind: rect, north, south, west, east, color?}]  north/south are /loc Y,
            west/east are /loc X
    """
    path = (directory or WAYPOINTS_DIR) / f"{short_name}.yaml"
    if not path.exists():
        return [], []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return [], []
    spots: List[MapSpot] = []
    for sp in data.get("spots") or []:
        try:
            spots.append(MapSpot(
                name=str(sp.get("name", "")),
                y=float(sp["y"]),
                x=float(sp["x"]),
                color=_mark_color(sp.get("color"), "red"),
            ))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    shapes: List[MapShape] = []
    for sh in data.get("shapes") or []:
        try:
            kind = str(sh.get("kind", "")).strip().lower()
            color = _mark_color(sh.get("color"), "amber")
            name = str(sh.get("name", ""))
            if kind == "circle":
                shapes.append(MapShape(
                    kind=kind, color=color, name=name,
                    y=float(sh["y"]), x=float(sh["x"]), radius=abs(float(sh["radius"])),
                ))
            elif kind == "rect":
                shapes.append(MapShape(
                    kind=kind, color=color, name=name,
                    north=float(sh["north"]), south=float(sh["south"]),
                    west=float(sh["west"]), east=float(sh["east"]),
                ))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return spots, shapes


def _clip_segment(
    x0: float, y0: float, x1: float, y1: float, max_x: float, max_y: float
) -> Optional[Tuple[float, float, float, float]]:
    """Liang–Barsky clip of a segment to the rectangle [0, max_x] x [0, max_y]."""
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0), (dx, max_x - x0), (-dy, y0), (dy, max_y - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            if t > t1:
                return None
            t0 = max(t0, t)
        else:
            if t < t0:
                return None
            t1 = min(t1, t)
    return x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy
