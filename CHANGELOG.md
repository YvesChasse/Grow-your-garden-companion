# Changelog

## 1.2.0 — 2026-11-05

- Added separate opaque VR capture bar and panel windows for use with XSOverlay and similar window-capture software.
- Shared existing watchlists, live quantities, countdowns and world status with the VR views, without adding network polling or dependencies.
- Added independent saved VR window visibility and geometry, Preferences controls and tray toggles.
- Kept desktop opacity separate from capture windows, and restored minimized windows when enabled again.
- Made Preferences scrollable and added VR setup and troubleshooting documentation.
- Added regression coverage for capture windows and existing preference compatibility. Headset capture remains unverified.

## 1.1.0 — 2026-11-02

- Migrated live stock to the documented `/api/v1/live` endpoint.
- Added `/api/v1/items` catalog loading at startup and daily, with locally retained names and no fabricated stock quantities.
- Added advance Traveler watches by name, without implying that catalog entries are guaranteed Traveler offers.
- Added a World tab with weather, Traveler, sell-bonus and event countdowns, plus optional world status in both overlays.
- Added opt-in weather-change, Traveler-arrival and sell-bonus alerts, with quiet startup and duplicate suppression.
- Kept existing preferences and separated catalog failures from live-feed status.
- Added API, catalog, notification and UI regressions; 50 automated checks pass.

This update contains no macro, OCR or game-input code.

## 1.0.0 — 2026-11-01

Initial Windows desktop release.

- Added a dark-purple watchlist manager with search and shop filters.
- Added independently toggleable top-screen bar and floating mini-panel, with layout switching, dragging, resizing and adjustable opacity.
- Connected directly to the public live feed verified in the Garden website's own application script.
- Added quantities and server-based countdowns for seeds, eggs, gear, event shops and traveling-merchant offers.
- Added stock alerts, optional sound, restock-cycle alerts and duplicate suppression.
- Added system-tray operation and locally saved watchlists and window preferences.
- Added clear stale/offline states, request timeouts, retries and rate-limit handling.
- Included setup launchers, a Windows executable build script, 31 automated checks and a live verification utility.

See [the validation record](docs/VALIDATION.md) for the tested environment and remaining platform-specific checks.
