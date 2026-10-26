"""Headless UI tests verifying Textual app composition and widget mounting."""

import unittest
from ekco_parse.config import load_config
from ekco_parse.ui.main_app import EkcoParseApp
from ekco_parse.ui.map_app import EkcoMapApp


class TestTextualUI(unittest.IsolatedAsyncioTestCase):

    async def test_main_app_mounts(self):
        config = load_config()
        app = EkcoParseApp(config=config)
        async with app.run_test() as pilot:
            # Check widgets exist
            header = app.query_one("#header-bar")
            self.assertIsNotNone(header)

            dps = app.query_one("#dps-panel")
            self.assertIsNotNone(dps)

            dot_panel = app.query_one("#dot-panel")
            self.assertIsNotNone(dot_panel)

            buff_panel = app.query_one("#buff-panel")
            self.assertIsNotNone(buff_panel)

            ticker = app.query_one("#ticker-panel")
            self.assertIsNotNone(ticker)

            # Trigger a tick update
            app._update_ui()
            await pilot.pause()

    async def test_map_app_mounts(self):
        config = load_config()
        app = EkcoMapApp(config=config, zone="East Commonlands")
        async with app.run_test() as pilot:
            header = app.query_one("#map-header")
            self.assertIsNotNone(header)

            radar = app.query_one("#radar-panel")
            self.assertIsNotNone(radar)

            poi = app.query_one("#poi-panel")
            self.assertIsNotNone(poi)

            app._refresh_ui()
            await pilot.pause()


if __name__ == "__main__":
    unittest.main()
