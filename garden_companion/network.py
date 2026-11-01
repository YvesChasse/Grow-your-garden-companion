"""Asynchronous Qt HTTPS client; no browser, cookies, API key or credentials."""
import json
import random
import time

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .core import FEED_URL, FeedError, parse_feed, poll_delay


class StockClient(QObject):
    received = pyqtSignal(object)
    failed = pyqtSignal(str)
    fetching = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.refresh)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self._timeout)
        self.reply = None
        self.failures = 0
        self.last_attempt = -100.0
        self.retry_not_before = 0.0
        self.stopped = False
        self.abort_reason = ""

    def refresh(self):
        if self.stopped or self.reply is not None:
            return
        # Rate-limit even repeated clicks. Scheduled retries also respect this floor.
        remaining = max(5 - (time.monotonic() - self.last_attempt), self.retry_not_before - time.monotonic())
        if remaining > 0:
            self.timer.start(int(remaining * 1000) + 1)
            return
        self.timer.stop()
        self.last_attempt = time.monotonic()
        self.abort_reason = ""
        request = QNetworkRequest(QUrl(FEED_URL))
        request.setTransferTimeout(15000)
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.SameOriginRedirectPolicy)
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                             QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        request.setRawHeader(b"Accept", b"application/json")
        request.setRawHeader(b"Cache-Control", b"no-cache")
        request.setRawHeader(b"User-Agent", b"GrowYourGardenCompanion/1.0 (Windows desktop)")
        self.reply = self.manager.get(request)
        self.reply.finished.connect(self._finished)
        self.reply.downloadProgress.connect(self._progress)
        self.deadline.start(20000)
        self.fetching.emit()

    def _progress(self, received, total):
        if max(received, total) > 2_000_000 and self.reply:
            self.abort_reason = "The feed response exceeded the size limit."
            self.reply.abort()

    def _timeout(self):
        if self.reply:
            self.abort_reason = "The feed request timed out."
            self.reply.abort()

    def _finished(self):
        reply, self.reply = self.reply, None
        self.deadline.stop()
        if self.stopped:
            reply.deleteLater()
            return
        retry_after = bytes(reply.rawHeader(b"Retry-After")).decode("ascii", errors="ignore")
        try:
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if reply.error() != QNetworkReply.NetworkError.NoError or status != 200:
                raise FeedError(self.abort_reason or f"HTTP {status}: {reply.errorString()}" if status else
                                self.abort_reason or reply.errorString())
            body = bytes(reply.readAll())
            if len(body) > 2_000_000:
                raise FeedError("The feed response exceeded the size limit.")
            snapshot = parse_feed(json.loads(body))
            self.failures = 0
            self.retry_not_before = 0.0
            self.timer.start(int(poll_delay(snapshot, random.uniform(0, 2)) * 1000))
            self.received.emit(snapshot)
        except (ValueError, TypeError, OverflowError) as error:
            self.failures += 1
            delay = min(60, self.failures * 5)
            if retry_after.isdigit():
                delay = max(delay, min(3600, int(retry_after)))
            self.retry_not_before = time.monotonic() + delay
            self.timer.start(delay * 1000)
            self.failed.emit(f"{error} Retrying in {delay}s.")
        finally:
            reply.deleteLater()

    def stop(self):
        self.stopped = True
        self.timer.stop()
        self.deadline.stop()
        if self.reply:
            self.reply.abort()
