import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from garden_companion.core import parse_feed, parse_catalog
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

    def test_catalog_only_item_is_watchable_without_invented_quantity(self):
        c = self.controller
        catalog = parse_catalog(json.loads(Path(__file__).with_name('observed_catalog.json').read_text(encoding='utf-8-sig')))
        c.accept_catalog(catalog)
        c.window.search.setText('Frost Pear')
        self.assertEqual(c.window.table.rowCount(), 1)
        self.assertEqual(c.window.table.item(0, 4).text(), '—')
        self.assertEqual(c.window.table.item(0, 3).text(), 'Frost Fair')
        c.window.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        APP.processEvents()
        self.assertIn('event:Frost Pear', c.watched)
        self.assertNotIn('event:Frost Pear', c.snapshot.by_key)
        self.assertIn('event:Frost Pear', Preferences(self.preferences.path).values['catalog'])

    def test_traveler_watch_can_be_added_before_first_visit(self):
        c = self.controller
        c.window.search.setText('Carrot')
        c.window.table.selectRow(0)
        c.window.watch_with_traveler()
        self.assertIn('traveler:Carrot', c.watched)
        self.assertNotIn('traveler:Carrot', c.snapshot.by_key)
        self.assertIsNone(next(row[3] for row in c.watched_entries() if row[0] == 'traveler:Carrot'))

    def test_catalog_failure_preserves_live_status_and_saved_catalog(self):
        c = self.controller
        cached = dict(c.preferences.values['catalog'])
        c.catalog_failed('Test unavailable')
        self.assertEqual(c.short_status(), 'LIVE')
        self.assertEqual(c.preferences.values['catalog'], cached)
        self.assertIn('Catalog unavailable', c.window.catalog_status.text())

    def test_world_alert_preferences_persist_and_global_mute_applies(self):
        c = self.controller
        c.notify = Mock()
        c.window.world_panel.checks['weather_alerts'].setChecked(True)
        self.assertTrue(Preferences(self.preferences.path).values['weather_alerts'])
        self.data['weather']['name'] = 'New weather'
        c.accept_snapshot(parse_feed(self.data))
        c.notify.assert_called_once()
        c.notify.reset_mock()
        c.preferences.values['notifications'] = False
        self.data['weather']['name'] = 'Another weather'
        c.accept_snapshot(parse_feed(self.data))
        c.notify.assert_not_called()

    def test_world_timers_stale_labels_and_overlay_toggle(self):
        c = self.controller
        self.assertIn('Traveler', c.overlays['panel'].world_line.text())
        c.window.world_panel.checks['world_overlay'].setChecked(False)
        self.assertTrue(c.overlays['panel'].world_line.isHidden())
        c.feed_failed('Disconnected')
        self.assertIn('Last known', c.window.world_panel.status.text())

    def test_expired_response_does_not_send_world_alert(self):
        c = self.controller
        c.notify = Mock()
        c.preferences.values['weather_alerts'] = True
        self.data['weather']['name'] = 'Rain'
        self.data['nextChangeAt'] = self.data['now'] - 60
        c.accept_snapshot(parse_feed(self.data))
        self.assertEqual(c.short_status(), 'STALE')
        c.notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
