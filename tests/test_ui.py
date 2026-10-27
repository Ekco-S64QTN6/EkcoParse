"""Headless UI tests verifying Textual app composition and widget mounting."""

import unittest
from textual.widgets import TabbedContent

from ekco_parse.config import load_config
from ekco_parse.ui.main_app import EkcoParseApp
from ekco_parse.ui.map_app import EkcoMapApp
from ekco_parse.ui.widgets.respawn_panel import RespawnWidget


class TestTextualUI(unittest.IsolatedAsyncioTestCase):

    async def test_main_app_mounts(self):
        config = load_config()
        app = EkcoParseApp(config=config)
        self.assertTrue(
            app.ansi_color,
            "Dashboard must preserve ANSI default backgrounds for terminal transparency",
        )
        async with app.run_test() as pilot:
            # The compact overlay starts directly with the DoT panel:
            # the status header is gone and the tab strip is hidden.
            self.assertEqual(len(app.query("#header-bar")), 0)
            tabs = app.query_one("#dashboard-tabs", TabbedContent)
            content_tabs = app.query_one("#dashboard-tabs > ContentTabs")
            self.assertEqual(content_tabs.styles.display, "none")

            dps = app.query_one("#dps-panel")
            self.assertIsNotNone(dps)

            dot_panel = app.query_one("#dot-panel")
            self.assertIsNotNone(dot_panel)

            buff_panel = app.query_one("#buff-panel")
            self.assertIsNotNone(buff_panel)

            # The live overlay should contain only the four requested panels.
            self.assertEqual(len(app.query("#ticker-panel")), 0)
            self.assertIsNotNone(app.query_one("#respawn-live-panel"))

            # Panels that were previously implemented but not part of the main UI
            # should now be mounted and wired to the shared engines.
            mitigation = app.query_one("#mitigation-panel")
            self.assertIsNotNone(mitigation)

            loot = app.query_one("#loot-panel")
            self.assertIsNotNone(loot)

            respawns = app.query_one("#respawn-panel")
            self.assertIsNotNone(respawns)

            # Respawn countdown must be visible in Live, not only on the hidden-tab Ledger view.
            live_respawns = app.query_one("#respawn-live-panel", RespawnWidget)
            self.assertEqual(live_respawns.parent.id, "tab-live")
            app.timer_engine.add_respawn_timer("a decaying skeleton", "Lower Guk")
            app._update_ui()
            rendered = live_respawns.render()
            rendered_text = getattr(rendered, "plain", str(rendered))
            self.assertIn("a decaying skeleton", rendered_text)
            self.assertRegex(rendered_text, r"\d{2}:\d{2}")

            # Trigger a tick update
            app._update_ui()
            await pilot.pause()

            # Numeric shortcuts make all three views usable without a mouse.
            await pilot.press("2")
            self.assertEqual(app.query_one("#dashboard-tabs", TabbedContent).active, "tab-defense")
            await pilot.press("3")
            self.assertEqual(app.query_one("#dashboard-tabs", TabbedContent).active, "tab-ledger")
            await pilot.press("1")
            self.assertEqual(app.query_one("#dashboard-tabs", TabbedContent).active, "tab-live")

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

    async def test_map_auto_zooms_on_first_loc_and_respects_manual_zoom(self):
        app = EkcoMapApp(config=load_config(), zone="East Commonlands")

        app._process_map_log_line(
            "[Mon Oct 26 12:00:00 2026] Your Location is -130.0, -1580.0, 3.75"
        )
        self.assertEqual(app.zoom, app.AUTO_ZOOM_LEVEL)
        self.assertFalse(app._auto_zoom_pending)
        self.assertIsNotNone(app.map_engine.current_location)

        # Later /loc updates should track the player without overriding their zoom choice.
        app.zoom = 2.0
        app._process_map_log_line(
            "[Mon Oct 26 12:00:05 2026] Your Location is -120.0, -1580.0, 3.75"
        )
        self.assertEqual(app.zoom, 2.0)

        # Manual zoom should continue past the old 4x ceiling and stop at the
        # new limit without unbounded zooming or allowing values below 1x.
        for _ in range(40):
            app.action_zoom_in()
        self.assertEqual(app.zoom, app.MAX_ZOOM_LEVEL)
        self.assertGreater(app.zoom, 4.0)

        for _ in range(40):
            app.action_zoom_out()
        self.assertEqual(app.zoom, 1.0)


if __name__ == "__main__":
    unittest.main()
