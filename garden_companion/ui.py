"""Desktop windows, overlays and tray controller."""
from datetime import datetime
import time

from PyQt6.QtCore import QEvent, QPointF, QRect, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton, QScrollArea, QSizeGrip,
    QSlider, QSystemTrayIcon, QMenu, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from .core import AlertTracker, CATEGORIES, Snapshot, countdown
from .network import StockClient

STYLE = """
QWidget { background: #141020; color: #efeaf9; font-family: 'Segoe UI'; font-size: 13px; }
QFrame#card, QFrame#overlayRoot { background: #211932; border: 1px solid #3b2c51; border-radius: 14px; }
QFrame#card QLabel, QFrame#overlayRoot QLabel { background: transparent; border: none; }
QLabel#title { font-size: 25px; font-weight: 700; color: #faf6ff; }
QLabel#eyebrow { font-size: 10px; letter-spacing: 2px; font-weight: 700; color: #b69bde; }
QLabel#muted { color: #b4a6c8; }
QLabel#big { font-size: 25px; font-weight: 600; color: #dcbdff; }
QLabel#live { color: #94ecc2; font-weight: 600; }
QLabel#stale { color: #f1bd7c; font-weight: 600; }
QPushButton { background: #302242; border: 1px solid #4c3764; border-radius: 8px; padding: 8px 13px; }
QPushButton:hover { background: #48305f; border-color: #ab80dc; }
QPushButton:pressed { background: #583a75; }
QPushButton#primary { background: #b58aeb; color: #1c122a; border: none; font-weight: 700; }
QPushButton#small { padding: 4px 9px; font-size: 12px; }
QPushButton:disabled { color: #81728f; }
QLineEdit, QComboBox { background: #211932; border: 1px solid #49345f; border-radius: 8px; padding: 9px; }
QLineEdit:focus { border-color: #b58aeb; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #211932; selection-background-color: #51346f; }
QTabWidget::pane { border: none; }
QTabBar::tab { color: #ad9bbf; padding: 12px 18px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #e0c2ff; border-bottom: 2px solid #bb8af4; }
QTableWidget { background: #191325; alternate-background-color: #20182e; border: 1px solid #3b2c51; border-radius: 8px; gridline-color: #30233e; selection-background-color: #3c2954; }
QTableWidget::item { padding: 5px; border: none; }
QHeaderView::section { background: #2a1e3b; color: #beacd3; border: none; padding: 9px 5px; font-size: 11px; font-weight: 600; }
QCheckBox { spacing: 9px; background: transparent; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #70518e; border-radius: 5px; background: #20172e; }
QCheckBox::indicator:checked { background: #b789ec; border: 2px solid #e4ccff; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #1a1325; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #5b4274; border-radius: 4px; min-height: 24px; }
QScrollBar:horizontal { background: #1a1325; height: 8px; margin: 0; }
QScrollBar::handle:horizontal { background: #5b4274; border-radius: 3px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QSlider::groove:horizontal { height: 6px; background: #39294c; border-radius: 3px; }
QSlider::handle:horizontal { background: #c49af7; width: 16px; margin: -5px 0; border-radius: 8px; }
QMenu { background: #211932; border: 1px solid #5a4175; padding: 6px; }
QMenu::item { padding: 8px 24px; }
QMenu::item:selected { background: #49315f; border-radius: 5px; }
QToolTip { background: #352345; color: #fff; border: 1px solid #80609e; padding: 6px; }
"""


def label(text="", name=None):
    widget = QLabel(str(text))
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, small=False, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if small or primary:
        widget.setObjectName("primary" if primary else "small")
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def make_icon(size=64):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 64, size / 64)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#322147"))
    painter.drawRoundedRect(0, 0, 64, 64, 17, 17)
    painter.setPen(QPen(QColor("#d2afff"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(32, 49, 32, 30)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#c09af2"))
    left = QPainterPath(QPointF(31, 36))
    left.cubicTo(10, 35, 12, 16, 13, 16)
    left.cubicTo(30, 15, 34, 26, 31, 36)
    painter.drawPath(left)
    painter.setBrush(QColor("#9ce6bd"))
    right = QPainterPath(QPointF(33, 29))
    right.cubicTo(31, 13, 44, 10, 51, 12)
    right.cubicTo(52, 24, 44, 31, 33, 29)
    painter.drawPath(right)
    painter.end()
    return QIcon(pixmap)


def clamp_geometry(widget, stored, default_size, top=False):
    screens = QApplication.screens()
    available = QApplication.primaryScreen().availableGeometry()
    if len(stored) == 4:
        rect = QRect(*stored)
        match = next((s.availableGeometry() for s in screens if s.availableGeometry().contains(rect.center())), None)
        if match:
            available = match
    else:
        width, height = default_size
        rect = QRect(available.center().x() - width // 2,
                     available.top() + 12 if top else available.center().y() - height // 2,
                     width, height)
    width = min(max(widget.minimumWidth(), rect.width()), available.width())
    height = min(max(widget.minimumHeight(), rect.height()), available.height())
    x = min(max(rect.x(), available.left()), available.right() - width + 1)
    y = min(max(rect.y(), available.top()), available.bottom() - height + 1)
    widget.setGeometry(x, y, width, height)


class Overlay(QWidget):
    def __init__(self, controller, mode):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.controller = controller
        self.mode = mode
        self.ready = False
        self.drag_offset = None
        self.time_labels = []
        self.setWindowTitle(f"Garden Companion · {mode.title()}")
        self.setWindowIcon(controller.icon)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(650, 116) if mode == "bar" else self.setMinimumSize(310, 300)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.root = QFrame()
        self.root.setObjectName("overlayRoot")
        outer.addWidget(self.root)
        layout = QVBoxLayout(self.root)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(7)
        header = QHBoxLayout()
        title = label("⠿  GARDEN", "eyebrow")
        title.setCursor(Qt.CursorShape.SizeAllCursor)
        title.installEventFilter(self)
        title.setToolTip("Drag to move this overlay")
        header.addWidget(title)
        self.status = label("CONNECTING", "muted")
        self.status.setStyleSheet("font-size: 10px;")
        header.addWidget(self.status)
        header.addStretch()
        swap = button("Panel" if mode == "bar" else "Bar", lambda: controller.switch_overlay(mode), True)
        swap.setToolTip("Switch to the other overlay layout")
        header.addWidget(swap)
        header.addWidget(button("Manage", controller.show_window, True))
        hide = button("×", lambda: controller.set_overlay(mode, False), True)
        hide.setToolTip("Hide overlay; restore it from the tray or Preferences")
        header.addWidget(hide)
        layout.addLayout(header)
        self.clock_line = label("Waiting for the public stock feed…", "muted")
        self.clock_line.setStyleSheet("font-size: 11px;")
        if mode == "panel":
            layout.addWidget(self.clock_line)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if mode == "bar" else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff if mode == "bar" else Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self.scroll, 1)
        footer = QHBoxLayout()
        if mode == "bar":
            footer.addWidget(self.clock_line)
        else:
            footer.addWidget(label("Your watchlist, wherever you garden.", "muted"))
        footer.addStretch()
        footer.addWidget(QSizeGrip(self))
        layout.addLayout(footer)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.remember)
        self.ready = True
        self.rebuild()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            return True
        if event.type() == QEvent.Type.MouseMove and self.drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            return True
        if event.type() == QEvent.Type.MouseButtonRelease and self.drag_offset is not None:
            self.drag_offset = None
            self.remember()
            return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.ready:
            self.save_timer.start(400)

    def remember(self):
        g = self.geometry()
        self.controller.preferences.values[f"{self.mode}_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.controller.save()

    def closeEvent(self, event):
        if self.controller.quitting:
            event.accept()
        else:
            event.ignore()
            self.controller.set_overlay(self.mode, False)

    def rebuild(self):
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        rows = QHBoxLayout(content) if self.mode == "bar" else QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 3, 0)
        rows.setSpacing(8)
        self.time_labels = []
        entries = self.controller.watched_entries()
        if not entries:
            empty = label("Make this space yours.\nChoose items in Manage → Watchlist.", "muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rows.addWidget(empty)
        for key, name, category, item in entries:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet("QFrame#card { background: #291e3a; border-color: #49335f; border-radius: 10px; }")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(11, 8, 11, 8)
            text = QVBoxLayout()
            text.setSpacing(3)
            name_label = label(name)
            name_label.setStyleSheet("font-weight: 600;")
            text.addWidget(name_label)
            timer_label = label("", "muted")
            timer_label.setStyleSheet("font-size: 10px;")
            text.addWidget(timer_label)
            self.time_labels.append((timer_label, category, item))
            card_layout.addLayout(text, 1)
            quantity = label(f"×{item.stock}" if item else "—")
            quantity.setStyleSheet("font-size: 21px; font-weight: 600; color: " +
                                  ("#94ecc2" if item and item.stock > 0 else "#8c7b9e") + ";")
            card_layout.addWidget(quantity)
            card.setToolTip(f"{CATEGORIES.get(category, category)} · {name}\n" +
                            (f"Last received quantity: {item.stock}" if item else "Not in the current feed; watch remains saved."))
            if self.mode == "bar":
                card.setMinimumWidth(180)
            rows.addWidget(card)
        rows.addStretch()
        previous = self.scroll.takeWidget()
        if previous:
            previous.deleteLater()
        self.scroll.setWidget(content)
        self.tick()

    def tick(self):
        c = self.controller
        self.status.setText(c.short_status())
        self.status.setStyleSheet("font-size: 10px; color: " + ("#94ecc2" if c.is_fresh() else "#f1bd7c") + ";")
        self.status.setToolTip(c.status_detail())
        if c.snapshot:
            now = c.server_now()
            prefix = "" if c.is_fresh() else "Last known • "
            self.clock_line.setText(prefix + "Seeds + gear " + countdown(c.snapshot.deadlines["seeds"], now) +
                                    "  ·  Eggs " + countdown(c.snapshot.deadlines["eggs"], now))
            for widget, category, item in self.time_labels:
                if item:
                    clock = countdown(item.restock_at, now)
                    widget.setText(f"{CATEGORIES[category]} · {'leaves' if category == 'traveler' else 'restock'} {clock}")
                else:
                    widget.setText(f"{CATEGORIES.get(category, category)} · not offered now")


class MainWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.updating = False
        self.row_keys = []
        self.setWindowTitle("Grow Your Garden Companion")
        self.setWindowIcon(controller.icon)
        self.setMinimumSize(850, 650)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 23, 28, 18)
        layout.setSpacing(17)
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(controller.icon.pixmap(54, 54))
        header.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(label("GROW YOUR GARDEN", "eyebrow"))
        titles.addWidget(label("A little closer to your garden.", "title"))
        header.addLayout(titles, 1)
        self.status = label("● CONNECTING", "stale")
        header.addWidget(self.status)
        layout.addLayout(header)
        layout.addWidget(label("Your favorite finds. Live shop stock. A quiet companion that stays with you.", "muted"))
        summaries = QHBoxLayout()
        self.summary_values = []
        for caption, detail in [("SEEDS + GEAR", "Next restock"), ("EGG SHOP", "Next restock"), ("YOUR WATCHLIST", "Available right now")]:
            card = QFrame()
            card.setObjectName("card")
            box = QVBoxLayout(card)
            box.setContentsMargins(17, 13, 17, 13)
            box.addWidget(label(caption, "eyebrow"))
            value = label("—", "big")
            box.addWidget(value)
            box.addWidget(label(detail, "muted"))
            self.summary_values.append(value)
            summaries.addWidget(card)
        layout.addLayout(summaries)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.stock_tab = QWidget()
        stock_layout = QVBoxLayout(self.stock_tab)
        stock_layout.setContentsMargins(0, 16, 0, 0)
        stock_layout.setSpacing(12)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search seeds, eggs, gear and more…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.populate)
        filters.addWidget(self.search, 1)
        self.category = QComboBox()
        self.category.addItem("All shops", "all")
        for key, title in CATEGORIES.items():
            self.category.addItem(title, key)
        self.category.currentIndexChanged.connect(self.populate)
        filters.addWidget(self.category)
        self.watched_only = QCheckBox("Watched only")
        self.watched_only.toggled.connect(self.populate)
        filters.addWidget(self.watched_only)
        stock_layout.addLayout(filters)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["WATCH", "ITEM", "SHOP", "RARITY", "STOCK", "PRICE", "RESTOCK"])
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(47)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.watch_changed)
        stock_layout.addWidget(self.table, 1)
        self.empty = label("Connecting to garden.orpine.app…", "muted")
        self.empty.setWordWrap(True)
        stock_layout.addWidget(self.empty)
        stock_layout.addWidget(label("Check an item to watch it. Event and traveler items appear when their shops are open.", "muted"))
        self.tabs.addTab(self.stock_tab, "Watchlist")
        self.tabs.addTab(self.build_preferences(), "Preferences")
        bottom = QHBoxLayout()
        self.detail = label("Connecting to the public stock feed…", "muted")
        self.detail.setWordWrap(True)
        bottom.addWidget(self.detail, 1)
        bottom.addWidget(button("Refresh", controller.client.refresh))
        bottom.addWidget(button("Hide to tray", self.hide_to_tray, primary=True))
        layout.addLayout(bottom)

    def build_preferences(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 16, 0, 0)
        grid = QGridLayout()
        self.checks = {}
        sections = [
            ("YOUR OVERLAYS", [("bar_visible", "Show compact top-screen bar"),
                               ("panel_visible", "Show floating mini-panel")]),
            ("NOTIFICATIONS", [("notifications", "Desktop stock alerts"), ("sound", "Play a sound with alerts"),
                                ("repeat_alerts", "Alert again each restock, even if still in stock")]),
            ("IN THE BACKGROUND", [("start_in_tray", "Start with the main window hidden")]),
        ]
        for row, (heading, choices) in enumerate(sections):
            card = QFrame()
            card.setObjectName("card")
            box = QVBoxLayout(card)
            box.setContentsMargins(17, 15, 17, 15)
            box.addWidget(label(heading, "eyebrow"))
            for key, text in choices:
                check = QCheckBox(text)
                check.setChecked(self.controller.preferences.values[key])
                check.toggled.connect(lambda checked, k=key: self.preference_changed(k, checked))
                box.addWidget(check)
                self.checks[key] = check
            grid.addWidget(card, row // 2, row % 2)
        opacity_card = QFrame()
        opacity_card.setObjectName("card")
        box = QVBoxLayout(opacity_card)
        box.setContentsMargins(17, 15, 17, 15)
        self.opacity_label = label("", "eyebrow")
        box.addWidget(self.opacity_label)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(55, 100)
        slider.setValue(self.controller.preferences.values["opacity"])
        slider.valueChanged.connect(self.opacity_changed)
        box.addWidget(slider)
        self.opacity_label.setText(f"OVERLAY OPACITY · {slider.value()}%")
        box.addWidget(button("Reset overlay positions", self.controller.reset_positions))
        grid.addWidget(opacity_card, 1, 1)
        layout.addLayout(grid)
        note = label("The tray keeps monitoring when windows are hidden. Right-click its leaf icon to restore a window or quit.\n"
                     "Alerts start after the first successful update; your current stock will not trigger a startup burst.\n"
                     "Windows notification settings and Do Not Disturb may silence desktop alerts.", "muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QHBoxLayout()
        buttons.addWidget(button("Test notification", lambda: self.controller.notify("Garden Companion", "Your garden alerts are ready.", test=True)))
        buttons.addWidget(button("Quit companion", self.controller.quit))
        buttons.addStretch()
        layout.addLayout(buttons)
        self.pref_path = label(f"Saved locally: {self.controller.preferences.path}", "muted")
        self.pref_path.setWordWrap(True)
        self.pref_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.pref_path)
        layout.addStretch()
        return page

    def preference_changed(self, key, value):
        if key.endswith("_visible"):
            self.controller.set_overlay(key.removesuffix("_visible"), value)
        else:
            self.controller.preferences.values[key] = value
            self.controller.save()

    def opacity_changed(self, value):
        self.opacity_label.setText(f"OVERLAY OPACITY · {value}%")
        self.controller.preferences.values["opacity"] = value
        for overlay in self.controller.overlays.values():
            overlay.setWindowOpacity(value / 100)
        self.controller.save()

    def populate(self):
        c = self.controller
        current = c.snapshot.by_key if c.snapshot else {}
        watched = c.watched
        catalog = c.preferences.values["catalog"]
        keys = set(current) | set(catalog) | watched
        rows = []
        for key in keys:
            item = current.get(key)
            cached = catalog.get(key, {})
            category = item.category if item else cached.get("category", key.partition(":")[0])
            name = item.name if item else cached.get("name", key.partition(":")[2] or key)
            if self.category.currentData() not in ("all", category):
                continue
            if self.watched_only.isChecked() and key not in watched:
                continue
            if self.search.text().casefold() not in f"{name} {category}".casefold():
                continue
            rows.append((key, name, category, item))
        order = list(CATEGORIES)
        rows.sort(key=lambda r: (r[0] not in watched, order.index(r[2]) if r[2] in order else 9,
                                not (r[3] and r[3].stock), r[1].casefold()))
        self.updating = True
        self.table.setRowCount(len(rows))
        self.row_keys = []
        for row, (key, name, category, item) in enumerate(rows):
            self.row_keys.append(key)
            watch = QTableWidgetItem()
            watch.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            watch.setCheckState(Qt.CheckState.Checked if key in watched else Qt.CheckState.Unchecked)
            watch.setData(Qt.ItemDataRole.UserRole, key)
            watch.setToolTip(f"Watch {name}")
            self.table.setItem(row, 0, watch)
            values = [name, CATEGORIES.get(category, category), item.rarity if item else "—",
                      str(item.stock) if item else "—",
                      f"{item.price:,.0f}" + (f" {item.currency}" if item.currency != "Coins" else "") if item else "—", ""]
            for column, text in enumerate(values, 1):
                cell = QTableWidgetItem(text)
                cell.setToolTip(text if item else "Not in the current feed. The watch remains saved.")
                if column == 4:
                    cell.setForeground(QColor("#94ecc2" if item and item.stock else "#9e8ab6"))
                    cell.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
                self.table.setItem(row, column, cell)
        self.updating = False
        self.empty.setVisible(not rows)
        self.empty.setText("No items match your filters." if keys else "Waiting for the first successful feed response. Items will appear automatically.")
        self.tick()

    def watch_changed(self, item):
        if self.updating or item.column() != 0:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        watched = self.controller.watched
        if item.checkState() == Qt.CheckState.Checked:
            watched.add(key)
        else:
            watched.discard(key)
        self.controller.preferences.values["watchlist"] = sorted(watched)
        self.controller.save()
        for overlay in self.controller.overlays.values():
            overlay.rebuild()
        # Defer rebuilding until the itemChanged callback has returned.
        QTimer.singleShot(0, self.populate)

    def tick(self):
        c = self.controller
        self.status.setText("● " + c.short_status())
        self.status.setStyleSheet("color: " + ("#94ecc2" if c.is_fresh() else "#f1bd7c") + "; font-weight: 600;")
        self.detail.setText(c.preferences.warning or c.status_detail())
        if c.snapshot:
            now = c.server_now()
            self.summary_values[0].setText(countdown(c.snapshot.deadlines["seeds"], now))
            self.summary_values[1].setText(countdown(c.snapshot.deadlines["eggs"], now))
            available = sum(i.stock > 0 and i.key in c.watched for i in c.snapshot.items)
            self.summary_values[2].setText(f"{available} / {len(c.watched)}" + (" · stale" if not c.is_fresh() else ""))
            current = c.snapshot.by_key
            for row, key in enumerate(self.row_keys):
                item = current.get(key)
                self.table.item(row, 6).setText(("Leaves " if item and item.category == "traveler" else "") +
                                              countdown(item.restock_at, now) if item else "Not offered")

    def hide_to_tray(self):
        if self.controller.tray_available:
            self.hide()
        else:
            self.showMinimized()

    def closeEvent(self, event):
        if self.controller.quitting:
            event.accept()
        elif self.controller.tray_available:
            event.ignore()
            self.hide()
            self.controller.save_window_geometry()
        else:
            self.controller.quit()
            event.accept()


class Controller:
    def __init__(self, app, preferences, *, network=True, tray=True):
        self.app = app
        self.preferences = preferences
        self.snapshot: Snapshot | None = None
        self.received_at = 0.0
        self.last_update = ""
        self.error = ""
        self.quitting = False
        self.alerts = AlertTracker()
        self.icon = make_icon()
        self.app.setWindowIcon(self.icon)
        self.app.setStyleSheet(STYLE)
        self.app.setQuitOnLastWindowClosed(False)
        self.client = StockClient()
        self.client.received.connect(self.accept_snapshot)
        self.client.failed.connect(self.feed_failed)
        self.tray_available = tray and QSystemTrayIcon.isSystemTrayAvailable()
        self.overlays = {}
        self.window = MainWindow(self)
        for mode in ("bar", "panel"):
            self.overlays[mode] = Overlay(self, mode)
        self.tray = QSystemTrayIcon(self.icon)
        self.tray.setToolTip("Grow Your Garden Companion")
        menu = QMenu()
        menu.addAction("Open watchlist", self.show_window)
        self.tray_actions = {}
        for mode, title in [("bar", "Top-screen bar"), ("panel", "Floating mini-panel")]:
            action = QAction(title, menu)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, m=mode: self.set_overlay(m, checked))
            menu.addAction(action)
            self.tray_actions[mode] = action
        menu.addAction("Reset overlay positions", self.reset_positions)
        menu.addSeparator()
        menu.addAction("Refresh stock", self.client.refresh)
        menu.addAction("Quit", self.quit)
        self.tray.setContextMenu(menu)
        self.tray_menu = menu
        self.tray.activated.connect(self.tray_activated)
        self.tray.messageClicked.connect(self.show_window)
        if self.tray_available:
            self.tray.show()
        self.restore_positions()
        for mode, overlay in self.overlays.items():
            overlay.setWindowOpacity(preferences.values["opacity"] / 100)
            self.set_overlay(mode, preferences.values[f"{mode}_visible"], persist=False)
        if not preferences.values["start_in_tray"] or not self.tray_available:
            self.window.show()
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.app.aboutToQuit.connect(self.cleanup)
        if network:
            QTimer.singleShot(0, self.client.refresh)

    @property
    def watched(self):
        return set(self.preferences.values["watchlist"])

    def server_now(self):
        return self.snapshot.now + time.monotonic() - self.received_at if self.snapshot else time.time()

    def is_fresh(self):
        return bool(self.snapshot and not self.error and time.monotonic() - self.received_at < 315
                    and self.server_now() <= self.snapshot.next_change_at + 15)

    def short_status(self):
        if self.is_fresh():
            return "LIVE"
        if self.snapshot:
            return "STALE"
        return "OFFLINE" if self.error else "CONNECTING"

    def status_detail(self):
        if self.error:
            return "Offline · last known quantities shown. " + self.error if self.snapshot else "Offline · " + self.error
        if self.snapshot:
            return ("Updated " if self.is_fresh() else "Awaiting refresh · last update ") + self.last_update + \
                f"  ·  {self.snapshot.weather}  ·  {self.snapshot.event_name}"
        return "Connecting to garden.orpine.app · no account or browser required"

    def accept_snapshot(self, snapshot):
        # Detect a cached/frozen response against the monotonic server clock.
        if self.snapshot and snapshot.now < self.server_now() - 30:
            self.feed_failed("The server returned an older snapshot. Waiting for current data.")
            self.client.timer.start(15000)
            return
        self.snapshot = snapshot
        self.received_at = time.monotonic()
        self.last_update = datetime.now().strftime("%I:%M:%S %p").lstrip("0")
        self.error = ""
        for item in snapshot.items:
            self.preferences.values["catalog"][item.key] = {"name": item.name, "category": item.category}
        self.save()
        alerts = self.alerts.update(snapshot, self.watched, self.preferences.values["repeat_alerts"])
        self.window.populate()
        for overlay in self.overlays.values():
            overlay.rebuild()
        if alerts and self.preferences.values["notifications"]:
            message = ", ".join(f"{item.name} ×{item.stock}" for item in alerts[:5])
            if len(alerts) > 5:
                message += f" and {len(alerts) - 5} more"
            self.notify("Your garden finds are in stock", message)

    def feed_failed(self, message):
        self.error = message
        self.tick()

    def watched_entries(self):
        items = self.snapshot.by_key if self.snapshot else {}
        entries = []
        for key in self.watched:
            item = items.get(key)
            cached = self.preferences.values["catalog"].get(key, {})
            entries.append((key, item.name if item else cached.get("name", key.partition(":")[2]),
                            item.category if item else cached.get("category", key.partition(":")[0]), item))
        return sorted(entries, key=lambda row: (not (row[3] and row[3].stock > 0), row[1].casefold()))

    def notify(self, title, message, test=False):
        if self.tray_available:
            self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 8000)
        else:
            self.window.detail.setText(f"{title}: {message}")
        if self.preferences.values["sound"]:
            if not test and not self.preferences.values["notifications"]:
                return
            QApplication.beep()

    def tick(self):
        self.window.tick()
        for overlay in self.overlays.values():
            overlay.tick()
        self.tray.setToolTip(f"Garden Companion · {self.short_status()} · {len(self.watched)} watched")

    def set_overlay(self, mode, visible, persist=True):
        self.preferences.values[f"{mode}_visible"] = visible
        overlay = self.overlays[mode]
        overlay.setVisible(visible)
        if visible:
            overlay.raise_()
        for check in (self.window.checks[f"{mode}_visible"], self.tray_actions[mode]):
            check.blockSignals(True)
            check.setChecked(visible)
            check.blockSignals(False)
        if persist:
            self.save()

    def switch_overlay(self, source):
        self.set_overlay(source, False)
        self.set_overlay("panel" if source == "bar" else "bar", True)

    def show_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def restore_positions(self):
        clamp_geometry(self.window, self.preferences.values["window_geometry"], (1080, 810))
        for mode, overlay in self.overlays.items():
            clamp_geometry(overlay, self.preferences.values[f"{mode}_geometry"],
                           (1050, 160) if mode == "bar" else (365, 490), mode == "bar")

    def reset_positions(self):
        for mode, overlay in self.overlays.items():
            self.preferences.values[f"{mode}_geometry"] = []
            clamp_geometry(overlay, [], (1050, 160) if mode == "bar" else (365, 490), mode == "bar")
        self.save()

    def save_window_geometry(self):
        rect = self.window.normalGeometry() if self.window.isMaximized() else self.window.geometry()
        self.preferences.values["window_geometry"] = [rect.x(), rect.y(), rect.width(), rect.height()]

    def save(self):
        self.preferences.save()

    def cleanup(self):
        self.client.stop()
        self.timer.stop()
        self.save_window_geometry()
        for overlay in self.overlays.values():
            overlay.remember()
        self.save()
        self.tray.hide()

    def quit(self):
        self.quitting = True
        self.app.quit()
