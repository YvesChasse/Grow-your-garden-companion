"""Feed model and alert rules. No GUI or network dependencies."""
from dataclasses import dataclass
import math
from typing import Any

API_URL = "https://garden.orpine.app/api/v1"
FEED_URL = API_URL + "/live"
CATALOG_URL = API_URL + "/items"
SITE_URL = "https://garden.orpine.app/"
CATEGORIES = {"seeds": "Seeds", "eggs": "Eggs", "gear": "Gear",
              "event": "Event shop", "traveler": "Traveler"}


class FeedError(ValueError):
    pass


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise FeedError(f"Invalid {label}")
    if value < 0:
        raise FeedError(f"Negative {label}")
    return float(value)


def object_value(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise FeedError(f"Missing or invalid {label}")
    return value


@dataclass(frozen=True)
class Item:
    category: str
    name: str
    stock: int
    rarity: str
    price: float
    currency: str
    restock_at: float | None
    cycle: str

    @property
    def key(self) -> str:
        # Mirrors the website's shop:name identity; event names do not break watchlists.
        return f"{self.category}:{self.name}"


@dataclass(frozen=True)
class CatalogItem:
    category: str
    name: str
    rarity: str

    @property
    def key(self):
        return f"{self.category}:{self.name}"


@dataclass(frozen=True)
class Catalog:
    items: tuple[CatalogItem, ...]
    weather: tuple[str, ...]


def text_value(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise FeedError(f"Invalid {label}")
    return value


def parse_catalog(payload):
    data = object_value(payload, "catalog")
    rows, weather = data.get("items"), data.get("weather")
    if not isinstance(rows, list) or len(rows) > 5000 or not isinstance(weather, list) or len(weather) > 200:
        raise FeedError("Invalid catalog lists")
    items, keys = [], set()
    for raw in rows:
        row = object_value(raw, "catalog item")
        category = row.get("group")
        if category not in {"seeds", "gear", "eggs", "event"}:
            raise FeedError("Invalid catalog group")
        item = CatalogItem(category, text_value(row.get("name"), "item name"),
                           text_value(row.get("rarity"), "rarity"))
        if item.key in keys:
            raise FeedError(f"Duplicate catalog item: {item.key}")
        keys.add(item.key)
        items.append(item)
    return Catalog(tuple(items), tuple(dict.fromkeys(text_value(w, "weather name") for w in weather)))


@dataclass(frozen=True)
class Snapshot:
    now: float
    next_change_at: float
    items: tuple[Item, ...]
    deadlines: dict[str, float]
    weather: str
    event_name: str
    traveler_open: bool
    weather_since: float | None = None
    weather_until: float | None = None
    event_end: float | None = None
    next_event: str = ""
    next_event_start: float | None = None
    sell_multiplier: float = 1
    bonus_until: float | None = None

    @property
    def by_key(self) -> dict[str, Item]:
        return {i.key: i for i in self.items}


def parse_feed(payload: Any) -> Snapshot:
    """Reject malformed/incomplete stock rather than turning it into zero stock."""
    data = object_value(payload, "response")
    now = number(data.get("now"), "server time")
    next_at = number(data.get("nextChangeAt"), "next change time")
    shop = object_value(data.get("shop"), "shop")
    eggs = object_value(data.get("eggs"), "eggs")
    traveler = object_value(data.get("traveler"), "traveler")
    main_at = number(shop.get("restockAt"), "shop restock")
    eggs_at = number(eggs.get("restockAt"), "egg restock")
    traveler_at = number(traveler.get("changesAt"), "traveler change")
    if not isinstance(traveler.get("open"), bool):
        raise FeedError("Invalid traveler availability")
    deadlines = {"seeds": main_at, "gear": main_at, "eggs": eggs_at,
                 "traveler": traveler_at}
    items = []
    keys = set()

    def add(category: str, rows: Any, deadline: float, cycle: str = ""):
        if not isinstance(rows, list) or len(rows) > 2000:
            raise FeedError(f"Invalid {category} inventory")
        for row in rows:
            row = object_value(row, "item")
            name = row.get("name")
            if not isinstance(name, str) or not name.strip() or len(name) > 200:
                raise FeedError("Invalid item name")
            stock = number(row.get("stock"), "stock quantity")
            if stock != int(stock):
                raise FeedError("Stock quantity must be an integer")
            item = Item(category, name, int(stock), str(row.get("rarity", "")),
                        number(row.get("price", 0), "price"), str(row.get("currency", "Sheckles")),
                        deadline, cycle or str(deadline))
            if item.key in keys:
                raise FeedError(f"Duplicate item: {item.key}")
            keys.add(item.key)
            items.append(item)

    add("seeds", shop.get("seeds"), main_at)
    add("gear", shop.get("gear"), main_at)
    add("eggs", eggs.get("items"), eggs_at)
    event = data.get("event")
    event_name = "No active event"
    if event is not None:
        event = object_value(event, "event")
        event_name = str(event.get("name", "Event shop"))
        event_at = number(event.get("shopRestockAt"), "event restock")
        deadlines["event"] = event_at
        add("event", event.get("shop"), event_at, f"{event_name}:{event_at}")
    if traveler["open"]:
        add("traveler", traveler.get("offers"), traveler_at)
    weather = object_value(data.get("weather"), "weather")
    next_event = data.get("nextEvent")
    if next_event is not None:
        next_event = object_value(next_event, "next event")
    bonus = data.get("bonus")
    if bonus is not None:
        bonus = object_value(bonus, "sell bonus")
    def optional_time(obj, key):
        return number(obj[key], key) if obj and key in obj else None
    return Snapshot(now, next_at, tuple(items), deadlines,
                    text_value(weather.get("name"), "weather name"), event_name, traveler["open"],
                    optional_time(weather, "since"), optional_time(weather, "until"),
                    optional_time(event, "end"), text_value(next_event.get("name"), "next event name") if next_event else "",
                    optional_time(next_event, "start"), number(bonus.get("sellMultiplier"), "sell multiplier") if bonus else 1,
                    number(bonus.get("until"), "sell bonus end") if bonus else None)


def poll_delay(snapshot: Snapshot, jitter: float = 1.0) -> float:
    # Same nextChangeAt-driven cadence as the website (cap: five minutes).
    return min(300.0, max(1.0, snapshot.next_change_at - snapshot.now + 1 + jitter))


def countdown(deadline: float | None, now: float) -> str:
    if deadline is None:
        return "—"
    seconds = max(0, math.ceil(deadline - now))
    if seconds == 0:
        return "Refreshing…"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"


def world_countdown(deadline, now):
    if deadline is not None and deadline-now >= 86400:
        minutes = math.ceil((deadline-now)/60)
        days, remaining = divmod(minutes, 1440)
        hours, minutes = divmod(remaining, 60)
        return f'{days}d {hours}h {minutes}m'
    return countdown(deadline, now)


class AlertTracker:
    """One alert per watched item per cycle; initial connection is a quiet baseline."""
    def __init__(self):
        self.previous: Snapshot | None = None
        self.seen: set[tuple[str, str]] = set()

    def update(self, snapshot: Snapshot, watched: set[str], repeat: bool = True) -> list[Item]:
        old = self.previous.by_key if self.previous else {}
        alerts = []
        active_cycles = {(i.key, i.cycle) for i in snapshot.items}
        self.seen.intersection_update(active_cycles)
        for item in snapshot.items:
            before = old.get(item.key)
            token = (item.key, item.cycle)
            if self.previous is not None and item.key in watched and item.stock > 0:
                appeared = before is None or before.stock == 0
                restocked = repeat and before is not None and before.cycle != item.cycle
                if (appeared or restocked) and token not in self.seen:
                    alerts.append(item)
                    self.seen.add(token)
        self.previous = snapshot
        return alerts


class WorldAlertTracker:
    """Quiet initial state; notify only observed changes, never countdown guesses."""
    def __init__(self):
        self.previous = None

    def update(self, snapshot, *, weather=False, traveler=False, bonus=False):
        before, self.previous = self.previous, snapshot
        if before is None:
            return []
        messages = []
        if weather and before.weather != snapshot.weather:
            messages.append(("Weather changed", f"{snapshot.weather} is now active."))
        # A new closing boundary also identifies a different visit if an entire
        # closed period was missed while offline. Remaining time alone never alerts.
        if traveler and snapshot.traveler_open and (not before.traveler_open or
                before.deadlines['traveler'] != snapshot.deadlines['traveler']):
            messages.append(("The Traveler has arrived", "The Traveler has arrived; his current offers are available."))
        active = snapshot.sell_multiplier > 1 and snapshot.bonus_until is not None and snapshot.bonus_until > snapshot.now
        was_active = before.sell_multiplier > 1 and before.bonus_until is not None and before.bonus_until > before.now
        if bonus and active and (not was_active or before.sell_multiplier != snapshot.sell_multiplier or
                                 before.bonus_until != snapshot.bonus_until):
            messages.append(("Sell bonus active", f"Global selling multiplier: ×{snapshot.sell_multiplier:g}."))
        return messages
