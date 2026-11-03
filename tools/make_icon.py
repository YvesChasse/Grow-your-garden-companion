"""Generate a native vector-drawn app icon; no external images needed."""
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtWidgets import QApplication
from garden_companion.ui import make_icon

app = QApplication([])
target = Path(__file__).resolve().parents[1] / "assets" / "garden.ico"
target.parent.mkdir(exist_ok=True)
if not make_icon(256).pixmap(256, 256).save(str(target), "ICO"):
    raise RuntimeError("Could not write Windows icon")
print(target)
