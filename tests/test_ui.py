import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from garden_companion.core import parse_feed
from garden_companion.preferences import Preferences
from garden_companion.ui import Controller, clamp_geometry

APP = QApplication.instance() or QApplication([])


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.preferences = Preferences(Path(self.directory.name) / "settings.json")
        self.controller = Controller(APP, self.preferences, network=False, tray=False)
        self.controller.timer.stop()
        self.data = json.loads(Path(__file__).with_name("observed_feed.json").read_text(encoding="utf-8-sig"))
        self.controller.accept_snapshot(parse_feed(self.data))
        APP.processEvents()

    def tearDown(self):
        c = self.controller
        c.cleanup()
        c.window.hide()
        c.window.deleteLater()
        for overlay in c.overlays.values():
            overlay.save_timer.stop()
            overlay.hide()
            overlay.deleteLater()
        APP.processEvents()
        self.directory.cleanup()

    def test_feed_populates_table_and_filter(self):
        window = self.controller.window
        self.assertEqual(window.table.rowCount(), 45)
        window.search.setText("Carrot")
        self.assertEqual(window.table.rowCount(), 1)
        self.assertEqual(window.table.item(0, 1).text(), "Carrot")

    def test_watch_checkbox_updates_saved_preferences_and_overlays(self):
        window = self.controller.window
        window.search.setText("Carrot")
        window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        APP.processEvents()
        self.assertIn("seeds:Carrot", self.controller.watched)
        self.assertIn("seeds:Carrot", Preferences(self.preferences.path).values["watchlist"])
        self.assertEqual(len(self.controller.overlays["panel"].time_labels), 1)

    def test_both_overlays_and_switch(self):
        c = self.controller
        c.set_overlay("bar", True)
        c.set_overlay("panel", True)
        self.assertTrue(c.overlays["bar"].isVisible())
        self.assertTrue(c.overlays["panel"].isVisible())
        c.switch_overlay("bar")
        self.assertFalse(c.overlays["bar"].isVisible())
        self.assertTrue(c.overlays["panel"].isVisible())

    def test_error_preserves_stock_but_marks_stale(self):
        c = self.controller
        c.feed_failed("Test disconnection")
        self.assertEqual(c.short_status(), "STALE")
        self.assertEqual(c.snapshot.by_key["seeds:Carrot"].stock, 22)
        self.assertIn("last known", c.status_detail())

    def test_frozen_response_rejected(self):
        c = self.controller
        c.received_at -= 100
        c.accept_snapshot(parse_feed(self.data))
        self.assertIn("older snapshot", c.error)

    def test_elapsed_feed_is_stale_without_error(self):
        c = self.controller
        c.received_at -= 500
        self.assertEqual(c.short_status(), "STALE")

    def test_unavailable_item_watch_survives(self):
        c = self.controller
        c.preferences.values["watchlist"] = ["event:Starfruit"]
        self.data["event"] = None
        c.accept_snapshot(parse_feed(self.data))
        self.assertEqual(c.watched_entries()[0][1], "Starfruit")
        self.assertIsNone(c.watched_entries()[0][3])

    def test_offscreen_geometry_is_recovered(self):
        window = self.controller.overlays["panel"]
        clamp_geometry(window, [99999, 99999, 365, 490], (365, 490))
        self.assertTrue(APP.primaryScreen().availableGeometry().contains(window.geometry()))


if __name__ == "__main__":
    unittest.main()
