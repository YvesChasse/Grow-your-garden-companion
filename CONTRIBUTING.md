# Contributing

Bug reports, feature ideas and focused pull requests are welcome.

## Local development

Use Windows and Python 3.11 or newer. Run `setup.ps1`, then launch the app with:

```powershell
.\.venv\Scripts\python.exe main.py
```

Run the offline checks before submitting a change:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For a deliberate live-feed check:

```powershell
.\.venv\Scripts\python.exe tools\verify_live.py --output work\live-check
```

The live check contacts garden.orpine.app. Keep routine tests offline and use captured or clearly synthetic fixtures for edge cases. Do not increase polling frequency or add guessed data endpoints.

## Changes and reports

- Describe the behavior being changed and how you verified it.
- Include a screenshot for visible interface changes.
- Keep network and stock-model logic separate from interface code.
- Preserve the distinction between zero stock, an unavailable item and stale data.
- Keep credentials, personal preferences, logs, environments and generated binaries out of commits.
- Update relevant setup instructions or the changelog when behavior changes.

For bugs, include the Windows version, source/executable version, reproduction steps, expected result and actual result. If sharing log excerpts, remove personal paths or other private information first.

Contributions to the application are under the repository's [GPL-3.0 license](LICENSE). Third-party components retain their own notices.
