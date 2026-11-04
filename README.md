# 18KGoldir

A Windows desktop widget built with **Python** and **PyQt6** for displaying the price of 18-karat (18K / 750) gold in Iranian tomans (تومان).

> **Project status:** The GitHub repository was empty when this README was created. This document describes the project based on its stated purpose; implementation details such as the widget layout, refresh interval, packaging, and exact source-field mappings should be updated when the application code is added.

## Overview

18KGoldir is intended to collect 18-karat gold price information from two online sources and present the available data in a compact Windows widget:

1. [RialNerkh — 18 Ayar rate](https://www.rialnerkh.com/rate/18ayar/?lang=fa)
2. [TIndex](https://tindex.app/en/)

The application should attempt to retrieve data from **both** sources independently. If one source is unavailable or does not expose a usable 18K price, the other source may still provide a value. The UI should identify the source and indicate when data was last updated.

## Features

- Windows desktop widget built with PyQt6.
- Retrieves 18K gold price information from RialNerkh and TIndex.
- Displays prices in Iranian tomans (تومان).
- Supports partial source availability: one successful source should not prevent showing the other source's result.
- Presents source-specific values separately rather than silently treating potentially different quotes as identical.

The precise fields available from each provider depend on the provider's current website/API response and may change.

## Data sources

| Source | Target | Purpose |
| --- | --- | --- |
| RialNerkh | [18 Ayar rate page](https://www.rialnerkh.com/rate/18ayar/?lang=fa) | Retrieve the published 18-karat gold rate, when available. |
| TIndex | [English website](https://tindex.app/en/) | Check for an available 18K gold quote or related market data. |

### Data handling notes

- Fetch each provider independently and handle timeouts, network errors, unexpected HTML/API responses, and missing fields.
- Do not assume both sites publish the same unit or quote basis. Confirm whether a returned value is per gram, per mithqal, or another unit before displaying or comparing it.
- Normalize units only when the source's unit is known. Convert rial to toman only when the source explicitly provides rial (1 toman = 10 rials).
- Preserve the provider's original value and unit for diagnostics.
- Display a timestamp for each successful fetch and clearly mark unavailable or stale data.
- Treat website content as external data, not executable code. Respect provider terms, rate limits, and robots/access policies; prefer documented APIs if available.

## Requirements

- Windows
- Python 3.10 or newer (adjust to the version actually supported by the project)
- PyQt6

Install the GUI dependency:

```powershell
py -m pip install PyQt6
```

Additional dependencies, if any, should be listed in the project's dependency file (for example, `requirements.txt` or `pyproject.toml`).

## Run

Once the application entry point and dependencies are present, run it from PowerShell. Replace the placeholder with the actual entry-point filename:

```powershell
py .\<entry-point>.py
```

## Configuration

No configuration interface or environment variables are documented yet. Add source-specific settings (such as request timeout and refresh interval) here when they are implemented. Do not embed API keys or other secrets in source control.

## Development

Suggested implementation boundaries:

- **Source adapters:** one adapter per provider, each returning a normalized result or a structured error.
- **Normalization:** explicit unit/currency conversion with tests; never infer a unit from the numeric value alone.
- **UI:** keep network requests off the Qt GUI thread (for example, use a worker thread or asynchronous task) so the widget remains responsive.
- **Resilience:** retain the last successful value while showing its age and the current fetch status.
- **Testing:** cover parsing, missing data, malformed responses, timeouts, and one-source-only availability with mocked responses.

## Disclaimer

Displayed prices are informational quotes from third-party sources and may be delayed, unavailable, or different from executable market prices. Verify prices and units with the original provider before making financial decisions. This application is not financial advice.

## License

No license file was present when this README was created. Until a license is added, all rights remain with the repository owner; do not assume the project is open-source or freely reusable.
