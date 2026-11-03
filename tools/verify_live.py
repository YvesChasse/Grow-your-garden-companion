"""Opt-in live integration check using the same HTTPS client as the application.

python tools/verify_live.py --output work/live-check
Writes a small report and screenshots; does not touch your personal preferences.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication
from garden_companion.core import FEED_URL, CATALOG_URL
from garden_companion.preferences import Preferences
from garden_companion.ui import Controller


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("work/live-check"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    # Qt's offscreen Windows plugin does not discover system fonts itself.
    for filename in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "seguisym.ttf"):
        font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    directory = tempfile.TemporaryDirectory()
    preferences = Preferences(Path(directory.name) / "preferences.json")
    preferences.values["watchlist"] = ["seeds:Carrot", "seeds:Coconut", "eggs:Rare Egg",
                                        "gear:Basic Sprinkler", "event:Starfruit", "seeds:Bone Blossom"]
    controller = Controller(app, preferences, tray=False)
    result = {"endpoint": FEED_URL, "catalog_endpoint": CATALOG_URL, "ok": False}
    catalog_ready = False
    finished = False

    def capture():
        if not controller.snapshot or not catalog_ready or finished:
            return
        snapshot = controller.snapshot
        controller.client.timer.stop()
        controller.catalog_client.timer.stop()
        result.update(ok=True, server_now=snapshot.now, next_change_at=snapshot.next_change_at,
                      item_count=len(snapshot.items), categories=sorted({i.category for i in snapshot.items}),
                      status=controller.short_status())
        (args.output / "snapshot.json").write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")
        controller.window.resize(1080, 810)
        controller.overlays["bar"].resize(1050, 160)
        controller.overlays["panel"].resize(365, 490)
        controller.set_overlay("bar", True)
        app.processEvents()
        controller.window.grab().save(str(args.output / "watchlist.png"))
        controller.window.tabs.setCurrentIndex(1)
        app.processEvents()
        controller.window.grab().save(str(args.output / "world.png"))
        controller.window.tabs.setCurrentIndex(2)
        app.processEvents()
        controller.window.grab().save(str(args.output / "preferences.png"))
        for name, overlay in controller.overlays.items():
            overlay.grab().save(str(args.output / f"{name}.png"))
        finish()

    def fail(message):
        result["error"] = message
        finish()

    def finish():
        nonlocal finished
        if finished:
            return
        finished = True
        (args.output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
        controller.quit()

    def got_catalog(catalog):
        nonlocal catalog_ready
        catalog_ready = True
        result['catalog_count'] = len(catalog.items)
        result['weather_types'] = len(catalog.weather)
        capture()

    controller.client.received.connect(lambda _: capture())
    controller.catalog_client.received.connect(got_catalog)
    controller.client.failed.connect(fail)
    controller.catalog_client.failed.connect(fail)
    QTimer.singleShot(30000, lambda: fail("Live verification timed out"))
    app.exec()
    directory.cleanup()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
