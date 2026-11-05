# Validation record

## Version 1.2.0 — November 5, 2026

- **56 offline checks passed**, including capture-window flags and opacity, independent visibility and close/tray behavior, restoration from minimized state, saved geometry across restart, shared watchlist/stock/world clocks and stale state, and old/invalid preference handling.
- **Native Windows window check passed** for both `Garden Companion - VR Bar` and `Garden Companion - VR Panel`: enumerated as visible top-level windows, not minimized, not utility/tool windows, and not layered windows. Window frames were within the available desktop area, including the title bar. See `tools/verify_vr.py` for the repeatable offline check.
- Rendered and inspected the VR bar, panel and scrollable Preferences page using historical stock fixtures and isolated settings. The guide's images show source-window content, not current stock or headset output.
- Windows x64 executable built with the existing build script and passed its isolated packaged startup check with `frozen: true` and all four desktop/VR windows registered.
- No additional runtime dependency, network polling, game-input code or change to personal settings was needed. Existing API and alert regressions passed; this UI update did not repeat the historical live API integration check below.

**Headset / XSOverlay capture has not been tested.** Windows enumeration and application checks establish suitable capture targets, but do not verify headset rendering, VR pointer interaction, saved-layout reconnection or other overlay apps. [VR.md](VR.md) includes the remaining manual checks. Notifications continue to use the Windows tray and are not forwarded to XSOverlay.

## Version 1.1.0 — November 2, 2026

- **50 offline checks passed**, including the original stock companion regressions plus catalog validation, catalog-only watches, advance Traveler watches, world-alert transitions and opt-outs, stale-state suppression and catalog-failure isolation.
- **Live production-client check passed** for both `/api/v1/live` and `/api/v1/items`: 60 catalog items, 10 weather types and 51 live item rows. The live response included real Traveler offers; the app reported LIVE.
- Rendered and inspected the watchlist, World tab, Preferences and both overlays. Screenshots in this folder show captured historical stock and server-clock countdowns. Long event timers use days/hours/minutes.
- The Windows x64 executable built successfully and passed its isolated packaged startup check with `frozen: true`.
- No macro code or additional runtime dependency was introduced. Existing user settings remain in the original preference folder.

World notifications were verified with simulated feed transitions. Windows banner/sound delivery remains subject to the platform-specific limitations below. No active sell bonus was present in the captured response; bonus parsing and notification behavior were checked with synthetic data. Only source-client live integration and packaged startup were checked for this version, not an unattended multi-day run.

## Version 1.0.0 — historical checks

Validated on November 1, 2026, using Windows 11 x64, Python 3.12.14, PyQt6 / Qt 6.10.2 and PyInstaller 6.19.0.

## Passed

- **31 automated checks**: feed parsing and malformed data, missing inventories, event/traveler handling, identity separation, countdowns, poll bounds, notification baseline and deduplication, restock cycles, preferences recovery and persistence, HTTP errors, malformed JSON, response-size limit, `Retry-After`, watchlist interactions, both overlays, unavailable watched items, stale snapshots and geometry recovery.
- **Public feed inspection**: traced the homepage's script to `/api/live`, then successfully requested it without cookies or authorization. See [FEED.md](FEED.md).
- **Live Qt HTTPS integration**: the same client used in production returned 45 items and a LIVE state. Server time advanced between independent observations.
- **Visual inspection**: rendered the actual Qt watchlist, preferences page, bar and panel using the live response. Checked readable text, quantities, countdowns, controls and scrolling. The included images are captures from that check, not current stock readings.
- **Windows executable build**: completed a single-file x64 build. The script isolates its DLL search path so unrelated media-tool libraries cannot contaminate the executable.
- **Packaged startup check**: the actual executable returned `{"startup": "ok", "overlays": ["bar", "panel"], "qt": true, "frozen": true}`.
- **Packaged live connection**: launched the normal Windows executable in an isolated background test. Its saved discovered catalog contained all 45 real feed items, with no application errors logged. Test processes were closed afterward.

## Scope of the checks

The visual captures use Qt's offscreen renderer with system fonts loaded explicitly. Windows notification banners, sound delivery, tray-menu interactions, exclusive-fullscreen games, other monitor/DPI configurations and other computers were not manually verified. The app provides a **Test notification** button and **Reset overlay positions** action for those environment-specific checks.

The build is unsigned. No installer, automatic Windows sign-in registration, privileged service, or auto-update mechanism is included. Stock accuracy depends on the public website's feed and future schema stability.
