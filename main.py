"""Windows entry point. Run with Python 3.11+ and PyQt6 installed."""
import argparse
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

from PyQt6.QtCore import QLockFile, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from garden_companion.preferences import Preferences, preferences_path
from garden_companion.ui import Controller


def main():
    parser = argparse.ArgumentParser(description="Grow Your Garden Companion")
    parser.add_argument("--settings", type=Path, help="Use an alternate preferences file")
    parser.add_argument("--smoke-test", type=Path, metavar="REPORT", help="Check startup without network or visible windows")
    args = parser.parse_args()
    if args.smoke_test:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GardenCompanion.Desktop.1")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Grow Your Garden Companion")
    app.setOrganizationName("GardenCompanion")
    path = args.settings or preferences_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        QMessageBox.critical(None, "Cannot save preferences", str(error))
        return 1
    handler = RotatingFileHandler(path.parent / "companion.log", maxBytes=500000, backupCount=2, encoding="utf-8")
    logging.basicConfig(handlers=[handler], level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    lock = QLockFile(str(path.with_suffix(".lock")))
    # Qt can detect a dead process; avoid treating a long-running active app as stale.
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None, "Already running", "Garden Companion is already running. Open the leaf icon in the system tray.")
        return 0

    def exception_hook(kind, value, traceback):
        logging.critical("Unhandled exception", exc_info=(kind, value, traceback))
        if not args.smoke_test:
            QMessageBox.critical(None, "Garden Companion", f"An unexpected error occurred.\n{value}\n\nDetails are saved in companion.log.")
        app.exit(1)

    sys.excepthook = exception_hook
    controller = Controller(app, Preferences(path), network=not args.smoke_test, tray=not args.smoke_test)
    if args.smoke_test:
        def finish_smoke():
            import json
            args.smoke_test.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_test.write_text(json.dumps({"startup": "ok", "overlays": list(controller.overlays),
                                                   "qt": True, "frozen": bool(getattr(sys, "frozen", False))}), encoding="utf-8")
            controller.quit()
        QTimer.singleShot(250, finish_smoke)
    result = app.exec()
    lock.unlock()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
