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


if __name__ == "__main__":
    unittest.main()
