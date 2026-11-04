# 18KGoldir

A Windows desktop widget built with **Python** and **PyQt6** that displays the price of one gram of 18-karat (18K / 750) gold in Iranian tomans (تومان).

## Data sources

The application is intended to query both providers independently and show each provider's quote when available.

### 1. RialNerkh

- Page: https://www.rialnerkh.com/rate/18ayar/?lang=fa
- The page explicitly identifies the instrument as **one gram of 18-karat gold** (`یک گرم طلا ۱۸ عیار`).
- The displayed quote is labelled `18AYAR · قیمت به تومان`.
- Available page data includes the latest rate, price change, opening price, daily high and low, update count, and intraday historical records.
- The page's own disclaimer says the figures are informational, not a buy/sell recommendation.

### 2. TIndex

- Website: https://tindex.app/en/
- Gold market page: https://tindex.app/en/indicators/precious-metals/
- API documentation: https://tindex.app/en/developers/
- The Gold & coins market page lists **18K Gold**. TIndex's symbol reference identifies its slug as `GOLD-18K` and its unit as **toman/gram**.
- The documented category endpoint is:

  ```text
  GET https://tindex.app/api/public/indicators/by-category/precious-metals
  ```

- The documented Python example uses the `Authorization: Bearer YOUR_TOKEN` header and reads indicator rows from `data.rows`. Filter the response rows for `slug == "GOLD-18K"`.
- TIndex requires an API token created from a registered account. Its documented free plan currently allows 3 requests per minute and 300 requests per day; observe the response rate-limit headers and `Retry-After` value.
- TIndex's API documents successful responses as `{ "success": true, "data": ... }`; handle unsuccessful responses and authentication/rate-limit errors explicitly.

**Important:** Both providers currently expose an 18K quote denominated in tomans per gram according to their published pages/documentation. Still validate the actual returned unit and symbol at runtime. Do not silently substitute 24K gold, melted gold, coins, or another unit if the 18K record is missing.

## Intended behavior

- Fetch RialNerkh and TIndex separately. Failure or missing data from one source must not hide a successful result from the other.
- Display each source's price independently, together with its source name and last-update time.
- Show a clear unavailable/error/stale state instead of inventing a price or presenting an old value as current.
- Keep the UI responsive by running network I/O outside the Qt GUI thread.
- Parse numeric values defensively and preserve the raw provider response/value for troubleshooting.
- Do not average or reconcile the two quotes unless that behavior is explicitly implemented and labelled.

## Configuration

The TIndex API requires a personal token. Store it outside source control, for example in an environment variable or a local, ignored configuration file. Never commit real tokens, passwords, or other credentials.

Suggested environment variable:

```powershell
$env:TINDEX_API_TOKEN = "your-token"
```

RialNerkh page access may be implemented using a documented/public endpoint if available, or carefully maintained page parsing. Prefer stable structured data over scraping rendered HTML. Respect each provider's terms, access rules, and rate limits.

## Requirements

- Windows
- Python 3.10 or newer (adjust to the version actually supported by the implementation)
- PyQt6
- An HTTP client such as `requests` or `httpx` (depending on the implementation)

Install the core GUI and HTTP dependencies:

```powershell
py -m pip install PyQt6 requests
```

Keep the actual dependency list in `requirements.txt` or `pyproject.toml` once the application code is added.

## Run

The repository did not contain an application entry point when this README was written. After adding the application code and dependencies, run its actual entry-point script, for example:

```powershell
py .\main.py
```

Update this command if the project's entry point differs.

## Development notes

Suggested separation of responsibilities:

- **RialNerkh adapter:** fetch and parse the 18AYAR page/data, validating that the result is the per-gram 18K quote in toman.
- **TIndex adapter:** call the documented precious-metals endpoint with the bearer token, then select the `GOLD-18K` row.
- **Normalization:** produce a common internal representation containing source, symbol, price, currency, unit, source timestamp, fetch timestamp, and status. Reject unknown units rather than guessing.
- **Qt UI:** use a worker thread (for example, `QThread`/worker object) for network operations; update widgets only on the GUI thread.
- **Resilience:** handle timeouts, DNS/network errors, HTTP errors, malformed JSON/HTML, missing symbols, and rate limits. Retain last-known values only when clearly marked with their age.
- **Tests:** mock provider responses and cover valid prices, missing `GOLD-18K`, wrong units, malformed payloads, timeouts, and one-provider-only success.

## Disclaimer

Prices are third-party informational quotes. They may be delayed, unavailable, or different from executable market prices. Verify the current price and unit with the provider before making a transaction. This application is not financial advice.

## Project status

The repository was empty when this README was first added. This document describes the requested application and verified public data-source interfaces; it does not claim that the widget, fetchers, packaging, or tests have already been implemented.

## License

No license file was present when this README was created. Until a license is added, all rights remain with the repository owner; do not assume the project is open-source or freely reusable.
