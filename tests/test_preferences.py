import json
from pathlib import Path
import tempfile
import unittest

from garden_companion.preferences import Preferences


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "settings.json"

    def tearDown(self):
        self.directory.cleanup()

    def test_roundtrip(self):
        p = Preferences(self.path)
        p.values["watchlist"] = ["eggs:Rare Egg", "event:Starfruit"]
        p.values["panel_geometry"] = [-500, 20, 365, 490]
        p.values["opacity"] = 72
        self.assertTrue(p.save())
        loaded = Preferences(self.path)
        self.assertEqual(loaded.values, p.values)
        self.assertFalse(self.path.with_suffix(".tmp").exists())

    def test_corrupt_file_is_recoverable(self):
        self.path.write_text("{broken", encoding="utf-8")
        p = Preferences(self.path)
        self.assertTrue(p.warning)
        self.assertEqual(p.values["watchlist"], [])
        self.assertTrue(p.save())

    def test_validation(self):
        self.path.write_text(json.dumps({"watchlist": [None, 4, "seeds:Carrot", "seeds:Carrot"],
                                         "opacity": 900, "panel_visible": "yes",
                                         "bar_geometry": [1, 2, "bad", 4]}))
        p = Preferences(self.path)
        self.assertEqual(p.values["watchlist"], ["seeds:Carrot"])
        self.assertEqual(p.values["opacity"], 100)
        self.assertTrue(p.values["panel_visible"])
        self.assertEqual(p.values["bar_geometry"], [])

    def test_independent_defaults(self):
        first, second = Preferences(self.path), Preferences(self.path)
        first.values["catalog"]["seed:test"] = {}
        self.assertEqual(second.values["catalog"], {})


if __name__ == "__main__":
    unittest.main()
