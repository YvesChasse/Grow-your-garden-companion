"""World timers and opt-in alerts, driven only by the public live response."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from .core import countdown, world_countdown


def label(text='', name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


class WorldPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        self.status = label('Waiting for live world information…', 'muted')
        layout.addWidget(self.status)
        grid = QGridLayout()
        self.values, self.details = {}, {}
        for index, (key, title) in enumerate([('weather', 'WEATHER'), ('traveler', 'TRAVELER'),
                                             ('bonus', 'SELL BONUS'), ('event', 'CURRENT EVENT')]):
            card = QFrame()
            card.setObjectName('card')
            box = QVBoxLayout(card)
            box.setContentsMargins(17, 13, 17, 13)
            box.addWidget(label(title, 'eyebrow'))
            self.values[key] = label('—', 'big')
            self.details[key] = label('Waiting for the feed', 'muted')
            box.addWidget(self.values[key])
            box.addWidget(self.details[key])
            grid.addWidget(card, index//2, index%2)
        layout.addLayout(grid)
        self.next_event = label('', 'muted')
        layout.addWidget(self.next_event)
        layout.addWidget(label('LET ME KNOW WHEN…', 'eyebrow'))
        self.checks = {}
        for key, text in [('weather_alerts', 'The weather changes'),
                          ('traveler_alerts', 'The Traveler arrives'),
                          ('bonus_alerts', 'A global sell bonus starts or changes'),
                          ('world_overlay', 'Show weather, Traveler and bonus status in my overlays')]:
            check = QCheckBox(text)
            check.setChecked(controller.preferences.values[key])
            check.toggled.connect(lambda value, k=key: self.changed(k, value))
            self.checks[key] = check
            layout.addWidget(check)
        layout.addWidget(label('World alerts are optional and follow the Desktop alerts setting in Preferences. '
                               'The first update is quiet; countdowns do not predict future weather or stock.', 'muted'))
        layout.addStretch()

    def changed(self, key, value):
        self.controller.preferences.values[key] = value
        self.controller.save()
        self.controller.tick()

    def tick(self):
        c = self.controller
        if not c.snapshot:
            self.status.setText('World information unavailable. ' + c.short_status())
            return
        s, now = c.snapshot, c.server_now()
        self.status.setText('Live world status' if c.is_fresh() else 'Last known world status — awaiting a fresh update')
        self.values['weather'].setText(s.weather)
        self.details['weather'].setText('Changes in ' + countdown(s.weather_until, now))
        self.values['traveler'].setText('Here now' if s.traveler_open else 'Away')
        self.details['traveler'].setText(('Leaves in ' if s.traveler_open else 'Arrives in ') + countdown(s.deadlines['traveler'], now))
        active = s.sell_multiplier > 1 and s.bonus_until is not None and s.bonus_until > s.now
        self.values['bonus'].setText(f'×{s.sell_multiplier:g} selling' if active else 'No active bonus')
        self.details['bonus'].setText('Ends in ' + countdown(s.bonus_until, now) if active else 'Watching for the next global bonus')
        self.values['event'].setText(s.event_name)
        self.details['event'].setText('Ends in ' + world_countdown(s.event_end, now) if s.event_end is not None else 'No event deadline announced')
        self.next_event.setText(f'Next event: {s.next_event} · starts in {world_countdown(s.next_event_start, now)}' if s.next_event else 'No next event announced')
