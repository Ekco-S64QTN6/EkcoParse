"""Unit tests for Log-driven Map engine and ASCII radar."""

import unittest
from datetime import datetime
from ekco_parse.map_engine import MapEngine
from ekco_parse.models import Location


class TestMapEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MapEngine(default_zone="East Commonlands")

    def test_zone_load(self):
        zone = self.engine.load_active_zone("East Commonlands")
        self.assertEqual(zone.name, "East Commonlands")
        self.assertGreater(len(zone.points), 0)

    def test_loc_update_and_breadcrumbs(self):
        t0 = datetime(2026, 10, 26, 12, 0, 0)
        loc1 = Location(y=-130.0, x=-1580.0, z=3.75, timestamp=t0)
        self.engine.update_location(loc1)

        self.assertIsNotNone(self.engine.current_location)
        self.assertEqual(len(self.engine.breadcrumbs), 1)

        # Move 100 units North in 5 seconds
        t1 = datetime(2026, 10, 26, 12, 0, 5)
        loc2 = Location(y=-30.0, x=-1580.0, z=3.75, timestamp=t1)
        self.engine.update_location(loc2)

        self.assertEqual(len(self.engine.breadcrumbs), 2)
        # Speed: 100 units / 5 sec = 20.0 u/s
        self.assertAlmostEqual(self.engine.current_speed, 20.0)

    def test_bearing_calculation(self):
        # Standing at origin (0, 0)
        # Point at North (+Y, 0)
        b_north = self.engine._calc_bearing(dy=100.0, dx=0.0)
        self.assertEqual(b_north, "N")

        # Point at South (-Y, 0)
        b_south = self.engine._calc_bearing(dy=-100.0, dx=0.0)
        self.assertEqual(b_south, "S")

        # Point at East in EQ (-dx is East)
        b_east = self.engine._calc_bearing(dy=0.0, dx=-100.0)
        self.assertEqual(b_east, "E")

        # Point at West in EQ (+dx is West)
        b_west = self.engine._calc_bearing(dy=0.0, dx=100.0)
        self.assertEqual(b_west, "W")

    def test_nearby_pois(self):
        loc = Location(y=-130.0, x=-1580.0, z=3.75)
        self.engine.update_location(loc)
        nearby = self.engine.get_nearby_pois(limit=3)

        self.assertGreater(len(nearby), 0)
        closest_poi, dist, bearing = nearby[0]
        self.assertIsNotNone(closest_poi.name)
        self.assertGreater(dist, 0.0)
        self.assertIn(bearing, ["N", "NE", "E", "SE", "S", "SW", "W", "NW"])

    def test_render_vector_wireframe(self):
        zone = self.engine.load_active_zone("Arena")
        self.assertEqual(zone.name, "Arena")
        self.assertGreater(len(zone.lines), 0)

        loc = Location(y=-100.0, x=0.0, z=5.0)
        self.engine.update_location(loc)
        rows = self.engine.render_vector_wireframe(cols=50, rows=20)

        self.assertEqual(len(rows), 20)
        # Check that player symbol @ is rendered in radar grid
        rendered_text = "".join(rows)
        self.assertIn("@", rendered_text)


    def _cell_of(self, rows, needle):
        import re
        for r, row in enumerate(rows):
            plain = re.sub(r"\[[^\]]*\]", "", row)
            c = plain.find(needle)
            if c >= 0:
                return r, c
        return None

    def test_east_is_right_and_north_is_up(self):
        """/loc X grows westward, so a point with smaller X must draw further right."""
        from ekco_parse.map_engine import MapLine, ZoneData
        zone = ZoneData(name="Test", short_name="test", min_y=-500, max_y=500, min_x=-500, max_x=500,
                        lines=[MapLine(-500, -500, 0, 500, 500, 0)])
        self.engine.zones_cache["test"] = zone
        self.engine.active_zone_name = "test"
        # Player to the east (x=-400) and north (y=+400) of centre.
        self.engine.update_location(Location(y=400.0, x=-400.0, z=0.0))
        r, c = self._cell_of(self.engine.render_vector_wireframe(cols=40, rows=20), "@")
        self.assertGreater(c, 20)
        self.assertLess(r, 10)

    def test_render_keeps_true_proportions(self):
        """A square zone must not be stretched to fill a wide radar."""
        from ekco_parse.map_engine import ZoneData, MapLine
        zone = ZoneData(name="Sq", short_name="sq", min_y=0, max_y=1000, min_x=0, max_x=1000,
                        lines=[MapLine(0, 0, 0, 0, 1000, 0), MapLine(1000, 0, 0, 1000, 1000, 0)])
        self.engine.zones_cache["sq"] = zone
        self.engine.active_zone_name = "sq"
        rows = self.engine.render_vector_wireframe(cols=60, rows=15)
        import re
        plain = [re.sub(r"\[[^\]]*\]", "", row) for row in rows]
        cols_with_ink = [c for c in range(60) if any(p[c] != " " for p in plain)]
        # 1000x1000 in a 120x60-dot canvas spans ~60 dots = ~30 cells, not 60.
        self.assertLess(max(cols_with_ink) - min(cols_with_ink), 35)

    def test_deep_zoom_is_fast_and_clipped(self):
        import time
        self.engine.load_active_zone("East Commonlands")
        self.engine.update_location(Location(y=-130.0, x=-1580.0, z=3.75))
        zoom = self.engine.max_zoom(56, 22)
        self.assertGreater(zoom, 50)
        t = time.perf_counter()
        rows = self.engine.render_vector_wireframe(cols=56, rows=22, zoom=zoom)
        self.assertLess(time.perf_counter() - t, 0.05)
        self.assertEqual(len(rows), 22)
        self.assertIn("@", "".join(rows))


class TestMapCleanup(unittest.TestCase):
    """Map packs carry legends, credits and ground spawns; only real waypoints should show."""

    def test_curated_waypoints_replace_map_labels(self):
        engine = MapEngine(default_zone="The Wakening Land")
        zone = engine.load_active_zone("The Wakening Land")
        names = [p.name for p in zone.points]
        self.assertFalse([n for n in names if n.startswith("GS")], "ground spawns leaked")
        self.assertIn("Unicorn Valley", names)
        keys = {p.key for p in zone.points if p.category != "zoneline"}
        self.assertEqual(keys, {str(n) for n in range(1, 10)})

    def test_legend_layer_does_not_stretch_the_map(self):
        # The Brewall legend sat ~2000 units south of The Wakening Land's walls.
        engine = MapEngine(default_zone="The Wakening Land")
        zone = engine.load_active_zone("The Wakening Land")
        self.assertGreater(zone.min_y, -4500)
        self.assertFalse([p for p in zone.points if "eqmaps" in p.name.lower()])

    def test_legend_and_junk_labels_are_recognised(self):
        from ekco_parse.map_engine import MapPoint, _is_junk_label, _is_legend_layer
        for junk in ("GS: Yew Leaf", "http://www.eqmaps.info", "Forge", "TRAP: Pit",
                     "to The Plane of Knowledge (Click Book)", "Priest of Discord"):
            self.assertTrue(_is_junk_label(junk), junk)
        for keep in ("to Skyshrine", "Druid Ring", "Bank of Erudin", "Lady Vox"):
            self.assertFalse(_is_junk_label(keep), keep)
        self.assertTrue(_is_legend_layer([MapPoint("Revised Map: Brewall Rainsinger", 0, 0)]))
        self.assertFalse(_is_legend_layer([MapPoint("to Skyshrine", 0, 0)]))

    def test_every_waypoint_file_loads_and_stays_on_the_map(self):
        from ekco_parse.map_engine import WAYPOINTS_DIR, load_waypoints
        engine = MapEngine(default_zone="Arena")
        files = sorted(WAYPOINTS_DIR.glob("*.yaml"))
        self.assertGreater(len(files), 100)
        for path in files:
            short = path.stem
            curated = load_waypoints(short)
            self.assertIsNotNone(curated, short)
            zone = engine._load_brewall_zone(short, short)
            self.assertIsNotNone(zone, short)
            # Anything outside the walls is dropped by the loader; none should be.
            self.assertEqual(len(zone.points), len(curated), short)

    def test_radar_draws_the_map_key_numbers(self):
        import re
        engine = MapEngine(default_zone="The Wakening Land")
        rows = engine.render_vector_wireframe(cols=70, rows=28)
        plain = "".join(re.sub(r"\[[^\]]*\]", "", r) for r in rows)
        for key in "123456789":
            self.assertIn(key, plain)


if __name__ == "__main__":
    unittest.main()
