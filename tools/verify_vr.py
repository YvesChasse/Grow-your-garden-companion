"""Offline rendering and native Windows capture-target checks; uses isolated settings."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from garden_companion.core import parse_feed
from garden_companion.preferences import Preferences
from garden_companion.ui import Controller


def native_window_check(widget):
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    hwnd = int(widget.winId())
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def collect(candidate, _):
        found.append(candidate)
        return True

    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    if not user32.EnumWindows(collect, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title, len(title))
    extended = user32.GetWindowLongW(hwnd, -20)
    result = {
        'title': title.value,
        'enumerated_top_level': hwnd in found,
        'visible': bool(user32.IsWindowVisible(hwnd)),
        'minimized': bool(user32.IsIconic(hwnd)),
        'tool_window': bool(extended & 0x80),
        'layered': bool(extended & 0x80000),
    }
    assert result['enumerated_top_level'] and result['visible'], result
    assert not any(result[k] for k in ('minimized', 'tool_window', 'layered')), result
    assert result['title'] == widget.windowTitle(), result
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work' / 'vr-check')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    with tempfile.TemporaryDirectory(prefix='garden-vr-check-') as temp:
        preferences = Preferences(Path(temp) / 'preferences.json')
        preferences.values.update(panel_visible=False, vr_bar_visible=True, vr_panel_visible=True,
                                  watchlist=['seeds:Carrot', 'gear:Watering Can', 'eggs:Rare Egg'])
        controller = Controller(app, preferences, network=False, tray=False)
        fixture = json.loads((ROOT / 'tests' / 'observed_feed.json').read_text(encoding='utf-8-sig'))
        controller.accept_snapshot(parse_feed(fixture))
        controller.window.tabs.setCurrentIndex(controller.window.tabs.count() - 1)
        report = {'stock': 'Historical offline fixture; not current inventory',
                  'headset_capture_tested': False, 'windows': {}}

        def verify():
            try:
                for mode in ('vr_bar', 'vr_panel'):
                    window = controller.overlays[mode]
                    assert window.screen().availableGeometry().contains(window.frameGeometry()), window.frameGeometry()
                    screenshot = window.grab()
                    assert not screenshot.isNull()
                    assert screenshot.save(str(args.output / f'{mode}.png'))
                    if sys.platform == 'win32' and os.environ.get('QT_QPA_PLATFORM', 'windows') == 'windows':
                        report['windows'][mode] = native_window_check(window)
                    else:
                        report['windows'][mode] = {'native_check': 'skipped: Windows native platform required'}
                controller.window.grab().save(str(args.output / 'preferences.png'))
                report['result'] = 'passed'
            except Exception as error:
                report['result'] = 'failed'
                report['error'] = repr(error)
            finally:
                (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                controller.quit()

        QTimer.singleShot(750, verify)
        app.exec()
        print(json.dumps(report, indent=2))
        return 0 if report.get('result') == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
