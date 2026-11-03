import json
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import QApplication
from garden_companion.network import StockClient

APP = QCoreApplication.instance() or QApplication([])


class Reply:
    def __init__(self, body, status=200, retry=b""):
        self.body, self.status, self.retry = body, status, retry
        self.deleted = False

    def rawHeader(self, name):
        return self.retry

    def attribute(self, name):
        return self.status

    def error(self):
        return QNetworkReply.NetworkError.NoError

    def errorString(self):
        return "Test HTTP error"

    def readAll(self):
        return self.body

    def deleteLater(self):
        self.deleted = True


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.client = StockClient()
        self.received, self.errors = [], []
        self.client.received.connect(self.received.append)
        self.client.failed.connect(self.errors.append)

    def tearDown(self):
        self.client.stop()

    def complete(self, reply):
        self.client.reply = reply
        self.client._finished()
        self.assertTrue(reply.deleted)

    def test_valid_response_schedules_next_change(self):
        body = Path(__file__).with_name("observed_feed.json").read_bytes()
        self.complete(Reply(body))
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.errors, [])
        self.assertGreater(self.client.timer.interval(), 1000)
        self.assertLessEqual(self.client.timer.interval(), 300000)

    def test_http_error_retries_without_empty_inventory(self):
        self.complete(Reply(b"unavailable", 503))
        self.assertEqual(self.received, [])
        self.assertIn("HTTP 503", self.errors[0])
        self.assertEqual(self.client.timer.interval(), 5000)

    def test_bad_json_and_schema_are_errors(self):
        for body in [b"<html>maintenance</html>", b'{"shop": null}']:
            self.complete(Reply(body))
        self.assertEqual(len(self.errors), 2)
        self.assertEqual(self.received, [])
        self.assertEqual(self.client.timer.interval(), 10000)

    def test_rate_limit_retry_after_cannot_be_bypassed_with_refresh(self):
        self.complete(Reply(b"", 429, b"120"))
        self.assertEqual(self.client.timer.interval(), 120000)
        self.client.refresh()
        self.assertIsNone(self.client.reply)
        self.assertGreater(self.client.timer.interval(), 119000)

    def test_oversized_response(self):
        self.complete(Reply(b" " * 2_000_001))
        self.assertIn("size limit", self.errors[0])
        self.assertEqual(self.received, [])


if __name__ == "__main__":
    unittest.main()
