import copy
import json
from pathlib import Path
import unittest

from garden_companion.core import AlertTracker, FeedError, countdown, parse_feed, poll_delay

FIXTURE = Path(__file__).with_name("observed_feed.json")


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))

    def test_observed_response(self):
        snapshot = parse_feed(self.data)
        self.assertEqual(len(snapshot.items), 45)
        self.assertEqual(snapshot.by_key["seeds:Carrot"].stock, 22)
        self.assertEqual(snapshot.by_key["event:Starfruit"].currency, "Stardust")
        self.assertEqual(snapshot.deadlines["eggs"], self.data["eggs"]["restockAt"])

    def test_missing_inventory_is_not_zero_stock(self):
        del self.data["shop"]["seeds"]
        with self.assertRaises(FeedError):
            parse_feed(self.data)

    def test_invalid_quantities(self):
        for invalid in [None, "3", True, -1, 1.5, float("nan"), float("inf")]:
            with self.subTest(invalid=invalid):
                self.data["shop"]["seeds"][0]["stock"] = invalid
                with self.assertRaises(FeedError):
                    parse_feed(self.data)

    def test_duplicate_identity(self):
        self.data["shop"]["seeds"].append(self.data["shop"]["seeds"][0])
        with self.assertRaises(FeedError):
            parse_feed(self.data)

    def test_optional_event_and_closed_traveler(self):
        self.data["event"] = None
        snapshot = parse_feed(self.data)
        self.assertNotIn("event", snapshot.deadlines)
        self.assertFalse(any(i.category in {"event", "traveler"} for i in snapshot.items))

    def test_open_traveler(self):
        self.data["traveler"]["open"] = True
        self.data["traveler"]["offers"] = [{"name": "Visitor Item", "stock": 2, "price": 50}]
        snapshot = parse_feed(self.data)
        self.assertEqual(snapshot.by_key["traveler:Visitor Item"].restock_at, self.data["traveler"]["changesAt"])

    def test_shop_scopes_identity(self):
        self.data["event"]["shop"][0]["name"] = "Carrot"
        snapshot = parse_feed(self.data)
        self.assertIn("event:Carrot", snapshot.by_key)
        self.assertIn("seeds:Carrot", snapshot.by_key)

    def test_countdowns_and_polling(self):
        self.assertEqual(countdown(4601, 1000), "1:00:01")
        self.assertEqual(countdown(1020, 1000), "00:20")
        self.assertEqual(countdown(999, 1000), "Refreshing…")
        self.assertEqual(countdown(None, 1000), "—")
        self.data["nextChangeAt"] = self.data["now"] + 9999
        self.assertEqual(poll_delay(parse_feed(self.data)), 300)
        self.data["nextChangeAt"] = self.data["now"] - 5
        self.assertEqual(poll_delay(parse_feed(self.data)), 1)


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
        self.tracker = AlertTracker()
        self.watched = {"seeds:Carrot"}

    def update(self, repeat=True):
        return self.tracker.update(parse_feed(self.data), self.watched, repeat)

    def test_startup_and_unchanged_are_quiet(self):
        self.assertEqual(self.update(), [])
        self.assertEqual(self.update(), [])

    def test_zero_to_positive_alerts_once(self):
        self.data["shop"]["seeds"][0]["stock"] = 0
        self.update()
        self.data["shop"]["seeds"][0]["stock"] = 5
        self.assertEqual(len(self.update()), 1)
        self.assertEqual(self.update(), [])
        self.data["shop"]["seeds"][0]["stock"] = 0
        self.update()
        self.data["shop"]["seeds"][0]["stock"] = 5
        self.assertEqual(self.update(), [])

    def test_new_cycle_alert_and_opt_out(self):
        self.update()
        self.data["shop"]["restockAt"] += 300
        self.assertEqual(len(self.update()), 1)
        self.data["shop"]["restockAt"] += 300
        self.assertEqual(self.update(repeat=False), [])

    def test_new_watch_does_not_alert_immediately(self):
        self.watched = set()
        self.update()
        self.watched = {"seeds:Carrot"}
        self.assertEqual(self.update(), [])

    def test_returning_event_item(self):
        event = copy.deepcopy(self.data["event"])
        self.watched = {"event:Starfruit"}
        self.data["event"] = None
        self.update()
        self.data["event"] = event
        self.assertEqual(len(self.update()), 1)

    def test_unwatched_restock_is_quiet(self):
        self.watched = {"seeds:Not Present"}
        self.update()
        self.data["shop"]["restockAt"] += 300
        self.assertEqual(self.update(), [])


if __name__ == "__main__":
    unittest.main()
