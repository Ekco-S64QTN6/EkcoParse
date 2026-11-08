"""Standalone Map Overlay Application for Project 1999 EverQuest."""

import asyncio
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual import events
from textual.widgets import Static
from rich.markup import escape

from ekco_parse.config import Config, active_log_switch, character_from_log, initial_log, load_config
from ekco_parse.map_engine import MapEngine
from ekco_parse.models import Location
from ekco_parse.parser import LogParser
from ekco_parse.tailer import LogTailer
from ekco_parse.ui.theme import (
    COLOR_BG,
    COLOR_PANEL_BG,
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_PURPLE,
    COLOR_GREEN,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_MUTED,
)


def map_pidfile() -> Path:
    """Where a running map records its PID, so ``run.sh --map-toggle`` can close it."""
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return Path(runtime) / "ekco-map.pid"


class MapHeaderWidget(Static):
    """Clean, bannerless telemetry header for standalone map window."""

    def update_info(
        self,
        zone: str,
        loc: Optional[Location],
        heading: str,
        speed: float,
        is_tailing: bool,
        zoom: float,
        view_units: float = 0.0,
        character: str = "",
    ) -> None:
        tail_status = (
            f"[bold {COLOR_GREEN}]● LIVE GPS[/]" if is_tailing
            else f"[bold {COLOR_RED}]▲ SCANNING[/]"
        )

        if loc:
            coords_str = (
                f"[bold white]Y:[/] [bold {COLOR_GREEN}]{loc.y:>8.1f}[/]  "
                f"[bold white]X:[/] [bold {COLOR_GREEN}]{loc.x:>8.1f}[/]  "
                f"[bold white]Z:[/] [bold {COLOR_GREEN}]{loc.z:>6.1f}[/]"
            )
        else:
            coords_str = f"[{COLOR_MUTED}]Waiting for /loc in game...[/]"

        line1 = (
            f"[bold {COLOR_CYAN}]ZONE:[/] [bold white]{escape(zone)}[/]  |  "
            f"[bold {COLOR_CYAN}]HEADING:[/] [bold {COLOR_AMBER}]{heading}[/]  |  "
            f"[bold {COLOR_CYAN}]SPEED:[/] [bold white]{speed} u/s[/]  |  "
            f"[bold {COLOR_CYAN}]ZOOM:[/] [bold {COLOR_PURPLE}]{zoom:.1f}x[/]"
            f" [{COLOR_MUTED}]({view_units:,.0f}u wide)[/]  |  "
            f"{tail_status}"
        )
        who = f"[bold {COLOR_CYAN}]{escape(character)}[/]  " if character else ""
        line2 = f"{who}[bold {COLOR_CYAN}]COORDINATES:[/] {coords_str}"

        self.update(f"{line1}\n{line2}\n───────────────────────────────────────────────────────────────────────────────")


class MapCanvasWidget(Static):
    """ASCII / Braille 2D radar grid display."""

    def on_mount(self) -> None:
        self.border_title = "ZONE RADAR (LOG-DRIVEN)"

    def update_radar(self, radar_rows: list[str]) -> None:
        self.update("\n".join(radar_rows))


class PoiRadarWidget(Static):
    """Nearby Points of Interest with bearings and distances."""

    def on_mount(self) -> None:
        self.border_title = "WAYPOINT RADAR & BEARINGS"

    def update_pois(self, pois: list) -> None:
        if not pois:
            self.update(f"  [{COLOR_MUTED}]No landmarks or POIs registered for this zone.[/]")
            return

        lines = [
            f"[bold {COLOR_CYAN}]WAYPOINT[/]                        [bold {COLOR_AMBER}]BEARING[/]   [bold {COLOR_GREEN}]DISTANCE[/]\n"
            f"───────────────────────────────────────────────────────"
        ]

        for pt, dist, bearing in pois:
            name = pt.name if len(pt.name) <= 26 else pt.name[:25] + "…"
            name_padded = escape(f"{name:<26}")

            # Bearing tag
            b_tag = f"[bold {COLOR_AMBER}]{bearing:>4}[/]"
            d_tag = f"[bold {COLOR_GREEN}]{int(dist):>5}m[/]"

            cat_icon = " ●"
            if pt.key and pt.category != "zoneline":
                cat_icon = f"[bold {COLOR_MAGENTA}]{escape(pt.key[:2]):>2}[/]"
            elif pt.category == "zoneline":
                cat_icon = f"[bold {COLOR_CYAN}] Z[/]"
            elif pt.category == "merchant":
                cat_icon = f"[bold {COLOR_AMBER}] M[/]"
            elif pt.category == "bank":
                cat_icon = f"[bold {COLOR_GREEN}] B[/]"

            lines.append(f" {cat_icon} {name_padded}  {b_tag}    {d_tag}")

        self.update("\n".join(lines))


class EkcoMapApp(App):
    """Standalone EverQuest Map Companion Window."""

    # Each zoom step multiplies/divides the scale, so deep zoom is a few presses.
    ZOOM_STEP = 1.5
    # Fallback radar size before the first layout pass reports the real one.
    DEFAULT_CANVAS = (56, 22)
    FOLLOW_CHECK_SEC = 2.0

    CSS = f"""
    Screen {{
        background: {COLOR_BG};
        padding: 1;
    }}

    #map-main {{
        layout: vertical;
        height: 100%;
    }}

    #map-header {{
        height: 6;
        background: {COLOR_PANEL_BG};
        color: white;
        border: solid {COLOR_GREEN};
        padding: 0 1;
        margin-bottom: 1;
    }}

    #map-body {{
        layout: grid;
        grid-size: 2;
        grid-columns: 62% 38%;
        height: 1fr;
    }}

    #radar-panel {{
        background: {COLOR_PANEL_BG};
        border: solid {COLOR_GREEN};
        padding: 0 1;
        height: 100%;
        overflow-y: hidden;
    }}

    #poi-panel {{
        background: {COLOR_PANEL_BG};
        border: solid {COLOR_CYAN};
        padding: 1;
        margin-left: 1;
        height: 100%;
        overflow-y: auto;
    }}
    """

    BINDINGS = [
        ("q", "quit", "Quit Map"),
        ("escape", "quit", "Quit Map"),
        ("z", "cycle_zone", "Cycle Zone"),
        ("plus,equals_sign,right_square_bracket,i", "zoom_in", "Zoom In"),
        ("minus,underscore,left_square_bracket,o", "zoom_out", "Zoom Out"),
        ("0", "zoom_fit", "Whole Zone"),
        ("b", "clear_breadcrumbs", "Clear Trail"),
        ("l", "manual_loc", "Enter /loc"),
    ]

    def __init__(self, config: Optional[Config] = None, zone: Optional[str] = None):
        super().__init__()
        self.config = config or load_config()
        initial_zone = zone or self.config.default_zone
        self.map_engine = MapEngine(
            maps_dir=self.config.maps_dir,
            default_zone=initial_zone,
            max_breadcrumbs=self.config.max_breadcrumbs,
        )
        self.parser = LogParser(character_name=self.config.character_name)
        self.tailer: Optional[LogTailer] = None
        self.log_path: Optional[Path] = None
        self.zoom: float = 1.0
        self.is_tailing: bool = False
        self._dirty = True
        self._last_follow_check = 0.0
        self._last_canvas: Optional[tuple] = None

    def compose(self) -> ComposeResult:
        yield Container(
            MapHeaderWidget(id="map-header"),
            Grid(
                MapCanvasWidget(id="radar-panel"),
                PoiRadarWidget(id="poi-panel"),
                id="map-body",
            ),
            id="map-main",
        )

    def on_mount(self) -> None:
        # The toggle hotkey closes the map with SIGTERM: exit through Textual so
        # the terminal is restored and run_map() removes its pidfile.
        try:
            asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, self.exit)
        except (NotImplementedError, RuntimeError, ValueError):
            pass
        # Same log the HUD/dashboard picks: whoever you are playing right now,
        # not just the character named in config.yaml.
        self._open_log(initial_log(self.config))
        # Poll fast and repaint only when something changed, so a /loc shows
        # up within ~50ms without burning CPU while you stand still.
        poll = min(0.1, max(0.03, float(self.config.poll_interval_sec or 0.05)))
        self.set_interval(poll, self._tick)
        self._refresh_ui()

    def _open_log(self, path: Path) -> None:
        self.log_path = Path(path)
        name = character_from_log(self.log_path)
        if name:
            self.parser.character_name = name
        self.catchup_zone(self.log_path)
        if self.tailer:
            self.tailer.close()
        self.tailer = LogTailer(
            filepath=self.log_path,
            start_at_end=True,
            poll_interval_sec=self.config.poll_interval_sec,
        )
        self.is_tailing = self.tailer.open()
        self._dirty = True

    def _follow_active_log(self) -> None:
        now = time.monotonic()
        if now - self._last_follow_check < self.FOLLOW_CHECK_SEC:
            return
        self._last_follow_check = now
        latest = active_log_switch(self.config, self.log_path)
        if latest:
            self.map_engine.current_location = None
            self.map_engine.breadcrumbs.clear()
            self._open_log(latest)

    def on_unmount(self) -> None:
        try:
            sys.stdout.write("\033]111\007")
            sys.stdout.flush()
        except Exception:
            pass

    def catchup_zone(self, target_log: Path) -> None:
        """Scan recent log history on startup to load the player's active zone and loc."""
        if not target_log.exists():
            return
        try:
            with open(target_log, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 350000), 0)
                lines = f.readlines()
            for line in lines:
                self._process_map_log_line(line)
        except Exception:
            pass

    def _process_map_log_line(self, line: str) -> None:
        """Apply one parsed log event. A /loc never changes the zoom: the view
        stays wherever the player left it (whole zone by default)."""
        parsed = self.parser.parse_line(line)
        if not parsed:
            return

        _, event = parsed
        if isinstance(event, Location):
            self.map_engine.update_location(event)
            self._dirty = True
        elif isinstance(event, dict):
            if event.get("type") == "zone_change":
                self._switch_zone(event["zone"])
                self._dirty = True
            elif event.get("type") == "heading":
                self.map_engine.update_heading(event["heading"])
                self._dirty = True

    # ── zoom ─────────────────────────────────────────────────────────────
    def _canvas_size(self) -> tuple:
        """Radar size in character cells, taken from the panel's real size."""
        try:
            size = self.query_one("#radar-panel", MapCanvasWidget).content_size
            if size.width >= 10 and size.height >= 5:
                return size.width, size.height
        except Exception:
            pass
        return self.DEFAULT_CANVAS

    @property
    def max_zoom(self) -> float:
        cols, rows = self._canvas_size()
        return self.map_engine.max_zoom(cols, rows)

    def _switch_zone(self, zone_name: str) -> None:
        """Switch zones without carrying stale coordinates into the new zone."""
        self.map_engine.set_zone(zone_name)
        self.map_engine.current_location = None
        self.map_engine.last_loc_time = None
        self.map_engine.current_speed = 0.0
        self.zoom = 1.0
        self._dirty = True

    def _tick(self) -> None:
        """Poll new log lines; repaint only if something changed."""
        self._follow_active_log()
        if self.tailer:
            for line in self.tailer.read_available_lines():
                self._process_map_log_line(line)
            active = bool(self.tailer._is_active)
            if active != self.is_tailing:
                self.is_tailing = active
                self._dirty = True

        if self._dirty or self._canvas_size() != self._last_canvas:
            self._refresh_ui()

    def _refresh_ui(self) -> None:
        if not self.is_mounted or not self.is_running:
            return
        self._dirty = False
        cols, rows = self._last_canvas = self._canvas_size()
        self.zoom = min(self.zoom, self.map_engine.max_zoom(cols, rows))

        # Update Header
        self.query_one("#map-header", MapHeaderWidget).update_info(
            zone=self.map_engine.active_zone_name,
            loc=self.map_engine.current_location,
            heading=self.map_engine.current_heading,
            speed=self.map_engine.current_speed,
            is_tailing=bool(self.tailer and self.tailer._is_active),
            zoom=self.zoom,
            view_units=self.map_engine.view_width_units(cols, rows, self.zoom),
            character=self.parser.character_name,
        )

        # Update Radar Grid with Vector Wireframe
        radar_rows = self.map_engine.render_vector_wireframe(
            cols=cols,
            rows=rows,
            zoom=self.zoom,
        )
        self.query_one("#radar-panel", MapCanvasWidget).update_radar(radar_rows)

        # Update POI Radar
        nearby = self.map_engine.get_nearby_pois(limit=10)
        self.query_one("#poi-panel", PoiRadarWidget).update_pois(nearby)

    def action_zoom_in(self) -> None:
        self.zoom = min(self.max_zoom, self.zoom * self.ZOOM_STEP)
        self._refresh_ui()

    def action_zoom_out(self) -> None:
        self.zoom = max(1.0, self.zoom / self.ZOOM_STEP)
        self._refresh_ui()

    def action_zoom_fit(self) -> None:
        self.zoom = 1.0
        self._refresh_ui()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self.action_zoom_in()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self.action_zoom_out()

    def action_clear_breadcrumbs(self) -> None:
        self.map_engine.breadcrumbs.clear()
        self._refresh_ui()

    def action_cycle_zone(self) -> None:
        zones = [
            "Arena",
            "East Commonlands",
            "Oasis of Marr",
            "Crushbone",
            "Upper Guk",
            "Lower Guk",
            "Skyshrine",
            "West Freeport",
            "Lake Rathetear",
            "Kedge Keep",
        ]
        cur = self.map_engine.active_zone_name
        try:
            next_idx = (zones.index(cur) + 1) % len(zones)
        except ValueError:
            next_idx = 0
        self._switch_zone(zones[next_idx])
        self._refresh_ui()

    def action_manual_loc(self) -> None:
        # Step through simulated test coordinate
        if self.map_engine.current_location:
            new_y = self.map_engine.current_location.y + 50.0
            new_x = self.map_engine.current_location.x - 30.0
            new_z = self.map_engine.current_location.z
        else:
            new_y = -130.0
            new_x = -1580.0
            new_z = 3.75
        self.map_engine.update_location(Location(y=new_y, x=new_x, z=new_z, timestamp=datetime.now()))
        self._refresh_ui()


def run_map(app: "EkcoMapApp") -> None:
    """Run the map, advertising its PID for the toggle hotkey while it is open."""
    pidfile = map_pidfile()
    try:
        pidfile.write_text(str(os.getpid()))
    except OSError:
        pidfile = None
    try:
        app.run()
    finally:
        try:
            if pidfile and pidfile.read_text().strip() == str(os.getpid()):
                pidfile.unlink()
        except OSError:
            pass


def main():
    config = load_config()
    run_map(EkcoMapApp(config=config))


if __name__ == "__main__":
    main()
