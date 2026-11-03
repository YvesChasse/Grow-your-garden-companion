import copy
import json
from pathlib import Path
import unittest

from garden_companion.core import (CATALOG_URL, FEED_URL, FeedError, WorldAlertTracker,
                                    parse_catalog, parse_feed, world_countdown)


class ApiV1Tests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(Path(__file__).with_name('observed_v1_live.json').read_text(encoding='utf-8-sig'))
        self.catalog = json.loads(Path(__file__).with_name('observed_catalog.json').read_text(encoding='utf-8-sig'))

    def test_documented_endpoints_and_real_responses(self):
        self.assertEqual(FEED_URL, 'https://garden.orpine.app/api/v1/live')
        self.assertEqual(CATALOG_URL, 'https://garden.orpine.app/api/v1/items')
        feed, catalog = parse_feed(self.data), parse_catalog(self.catalog)
        self.assertEqual(len(catalog.items), 60)
        self.assertEqual(feed.weather_until, self.data['weather']['until'])
        self.assertEqual(feed.event_end, self.data['event']['end'])
        self.assertEqual(feed.next_event, 'Frost Fair')
        self.assertEqual(feed.by_key['seeds:Carrot'].currency, 'Sheckles')
        self.assertTrue(any(i.name == 'Frost Pear' for i in catalog.items))
        self.assertNotIn('event:Frost Pear', feed.by_key)

    def test_catalog_does_not_invent_stock_or_traveler_membership(self):
        catalog = parse_catalog(self.catalog)
        self.assertFalse(any(i.category == 'traveler' for i in catalog.items))
        self.assertFalse(hasattr(catalog.items[0], 'stock'))

    def test_catalog_rejects_invalid_and_duplicate_rows(self):
        bad = copy.deepcopy(self.catalog)
        bad['items'].append(bad['items'][0])
        with self.assertRaises(FeedError):
            parse_catalog(bad)
        bad = copy.deepcopy(self.catalog)
        bad['items'][0]['group'] = 'invented-shop'
        with self.assertRaises(FeedError):
            parse_catalog(bad)
        with self.assertRaises(FeedError):
            parse_catalog({'items': [], 'weather': [42]})

    def test_absent_bonus_and_next_event(self):
        self.data['nextEvent'] = None
        s = parse_feed(self.data)
        self.assertEqual(s.sell_multiplier, 1)
        self.assertIsNone(s.bonus_until)
        self.assertEqual(s.next_event, '')

    def test_long_event_timer_is_readable(self):
        self.assertEqual(world_countdown(172800+3660, 0), '2d 1h 1m')
        self.assertEqual(world_countdown(30, 0), '00:30')

    def test_bonus_and_bad_bonus(self):
        self.data['bonus'] = {'sellMultiplier': 2, 'until': self.data['now']+600}
        self.assertEqual(parse_feed(self.data).sell_multiplier, 2)
        for bad in (True, -1, float('nan')):
            self.data['bonus']['sellMultiplier'] = bad
            with self.assertRaises(FeedError):
                parse_feed(self.data)


class WorldAlertsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(Path(__file__).with_name('observed_v1_live.json').read_text(encoding='utf-8-sig'))
        self.tracker = WorldAlertTracker()

    def update(self, **options):
        return self.tracker.update(parse_feed(self.data), **({'weather': True, 'traveler': True, 'bonus': True} | options))

    def test_initial_and_unchanged_state_are_quiet(self):
        self.data['bonus'] = {'sellMultiplier': 2, 'until': self.data['now']+600}
        self.data['traveler']['open'] = True
        self.assertEqual(self.update(), [])
        self.assertEqual(self.update(), [])

    def test_weather_change_once_and_opt_out(self):
        self.update()
        self.data['weather']['name'] = 'Rain'
        self.assertEqual(len(self.update()), 1)
        self.assertEqual(self.update(), [])
        self.data['weather']['name'] = 'Clear'
        self.assertEqual(self.update(weather=False), [])
        self.assertEqual(self.update(), [])

    def test_traveler_arrival_new_visit_and_no_departure_alert(self):
        self.update()
        self.data['traveler']['open'] = True
        self.assertEqual(len(self.update()), 1)
        self.assertEqual(self.update(), [])
        self.data['traveler']['changesAt'] += 1000
        self.assertEqual(len(self.update()), 1)
        self.data['traveler']['open'] = False
        self.assertEqual(self.update(), [])

    def test_bonus_activation_change_and_expired_bonus(self):
        self.update()
        self.data['bonus'] = {'sellMultiplier': 2, 'until': self.data['now']+600}
        self.assertEqual(len(self.update()), 1)
        self.assertEqual(self.update(), [])
        self.data['bonus']['sellMultiplier'] = 3
        self.assertEqual(len(self.update()), 1)
        self.data['bonus']['until'] = self.data['now']-1
        self.assertEqual(self.update(), [])

    def test_disabled_alerts_still_establish_baseline(self):
        self.update(weather=False, traveler=False, bonus=False)
        self.data['weather']['name'] = 'Rain'
        self.data['traveler']['open'] = True
        self.data['bonus'] = {'sellMultiplier': 2, 'until': self.data['now']+600}
        self.assertEqual(self.update(weather=False, traveler=False, bonus=False), [])
        self.assertEqual(self.update(), [])


if __name__ == '__main__':
    unittest.main()
