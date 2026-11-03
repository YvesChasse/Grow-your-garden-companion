# Public live-feed verification

Inspected November 1, 2026. No endpoint was guessed.

## Evidence chain

1. Downloaded the public [homepage](https://garden.orpine.app/). Its HTML links `/app.js` with a deferred script tag.
2. Downloaded that exact [application script](https://garden.orpine.app/app.js). In the inspected version, line 263 inside `refresh()` calls:

   ```javascript
   fetch("/api/live", { cache: "no-store" })
   ```

3. Requested that exact [public endpoint](https://garden.orpine.app/api/live) over HTTPS without cookies, an API key or authorization. It returned JSON successfully.
4. Verified the companion's own Qt HTTPS client against the same endpoint on Windows. A later response advanced the server timestamp and returned 45 items across seeds, gear, eggs and the active event shop. The traveler was closed, so no traveler offers were returned at that time.

First captured response: `now = 1793558928`, or **November 1, 2026, 12:48:48 PM America/Chicago (18:48:48 UTC)**. A subsequent Qt-client verification returned `now = 1793559438`, or **12:57:18 PM America/Chicago (18:57:18 UTC)**. The changing timestamps and stock values support that this is a live feed, rather than a static example response.

## Fields actually observed

| Feed field | App behavior |
| --- | --- |
| `now` | Server time used to anchor all countdowns |
| `nextChangeAt` | Time for the next stock/world-data fetch |
| `shop.seeds[]`, `shop.gear[]` | Seed and gear inventory |
| `shop.restockAt`, `shop.every` | Shared shop restock deadline and interval |
| `eggs.items[]`, `eggs.restockAt`, `eggs.every` | Egg inventory and independent restock timing |
| `event` | Object for an active event, or null; app handles both |
| `event.shop[]`, `event.shopRestockAt` | Event inventory and its restock deadline |
| `traveler.open`, `traveler.offers[]`, `traveler.changesAt` | Offers while open; next arrival/departure boundary |
| item `name`, `kind`, `rarity`, `price`, `stock`, `icon` | Item metadata; quantity comes directly from `stock` |
| item `currency` | Alternative price unit when present |
| `weather.name` | Current weather in the main-window footer |

The website's `shops()` function adds the traveler only while `traveler.open` is true, and the event shop only when `event` exists. The companion follows that behavior. The original closed-traveler response cannot prove the future shape of a populated traveler inventory by itself; its mapping to `offers` is also directly supported by the site's `shops()` implementation. The open-traveler case has an automated synthetic regression test.

The site's refresh logic sets its clock offset from `data.now`, then schedules a fetch just after `data.nextChangeAt` with small jitter and a 300-second cap. The companion uses the same schedule, an asynchronous request, a 20-second total timeout and bounded retries. It does not connect to a WebSocket or invent a `/b2/` route. No browser session is needed.

## Reproduce

In PowerShell:

```powershell
$live = Invoke-RestMethod 'https://garden.orpine.app/api/live'
$live.now
$live.shop.seeds | Select-Object name, stock
$live.eggs.restockAt
```

Or run `python tools/verify_live.py --output work/live-check` in the configured source environment. That uses the same network implementation as the app.

The test fixture `tests/observed_feed.json` preserves the first response. It is never loaded by production code. Inspection-file SHA-256 hashes:

```text
homepage HTML  F88A9D70104038ECD15153982D156E4A81BFF07B560AE9979E2E7745903AC0C0
app.js         3F6782CAF945CF59FC215F7DB91563F8A0EBA2BE72E214668087C2C8DDFE0140
live JSON      A15F7085B29D1268E788C399DBB72397B8C101D662B62B211380DB320128E261
```

These document the bytes observed during inspection, not a guarantee of future website content. Full website source is not redistributed in this project.
