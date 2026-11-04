"""Download RialNerkh's daily 18-karat gold history table into one CSV.

Usage:
    py -m pip install -r requirements.txt
    py rialnerkh_history.py
    py rialnerkh_history.py --start-date 2026-08-01 --end-date 2026-11-04
"""
from __future__ import annotations

import argparse
import csv
import logging
import random
import re
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from requests import Response
from requests.exceptions import RequestException

BASE_URL = "https://www.rialnerkh.com/rate/18ayar/"
TABLE_SELECTOR = (
    "body > main > div > div.rn-detail-grid > "
    "section.rn-page-card.rn-history-panel > "
    "div.rn-history-table > table"
)
TEHRAN = ZoneInfo("Asia/Tehran")
DEFAULT_START = date(2026, 8, 1)
DEFAULT_MIN_DELAY = 4.0
DEFAULT_MAX_DELAY = 8.0
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT = (10, 30)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("rialnerkh_history")


def normalize_digits(value: str) -> str:
    """Convert Persian and Arabic-Indic digits to ASCII for stable CSV values."""
    return value.translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    ))


def _retry_after_seconds(response: Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        try:
            when = parsedate_to_datetime(raw)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def fetch_day(session: requests.Session, day: date) -> list[dict[str, str]]:
    """Fetch one date page and return every data row in the specified history table."""
    params = {"date": day.isoformat(), "lang": "fa"}
    url = f"{BASE_URL}?{urlencode(params)}"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
        except RequestException as exc:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"Network error for {day}: {exc}") from exc
            wait = random.uniform(10.0, 20.0) * attempt
            log.warning("%s network error; retrying in %.1fs: %s", day, wait, exc)
            time.sleep(wait)
            continue

        if response.status_code in (429, 503):
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Server asked us to slow down (HTTP {response.status_code}) "
                    f"for {day}; stopping to avoid further load."
                )
            wait = _retry_after_seconds(response)
            if wait is None:
                wait = random.uniform(30.0, 60.0) * attempt
            log.warning("HTTP %s for %s; waiting %.1fs before retry",
                        response.status_code, day, wait)
            time.sleep(wait)
            continue

        if response.status_code in (403,):
            raise RuntimeError(
                f"Access denied (HTTP 403) for {day}. Stopping; do not attempt "
                "to bypass the site's access controls."
            )
        if response.status_code == 404:
            log.warning("No page for %s (HTTP 404); skipping", day)
            return []
        response.raise_for_status()
        break

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one(TABLE_SELECTOR)
    if table is None:
        log.warning("History table not found for %s; page layout may have changed", day)
        return []

    header_rows = table.select("thead tr")
    headers: list[str] = []
    for row in header_rows:
        cells = row.find_all(["th", "td"], recursive=False)
        if cells:
            headers = [
                re.sub(r"\s+", " ", normalize_digits(cell.get_text(" ", strip=True))).strip()
                for cell in cells
            ]
    if not headers:
        raise RuntimeError(f"History table on {day} has no readable column headers")

    body_rows = table.select("tbody tr")
    if not body_rows:
        body_rows = [
            row for row in table.select("tr")
            if row not in header_rows
        ]

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict[str, str]] = []
    for row in body_rows:
        cells = row.find_all(["td", "th"], recursive=False)
        if not cells:
            continue
        values = [
            re.sub(r"\s+", " ", normalize_digits(cell.get_text(" ", strip=True))).strip()
            for cell in cells
        ]
        # Ignore separator/empty rows, but preserve every actual table cell.
        if not any(values):
            continue
        record = {
            header: values[index] if index < len(values) else ""
            for index, header in enumerate(headers)
        }
        if len(values) > len(headers):
            for index in range(len(headers), len(values)):
                record[f"extra_column_{index + 1}"] = values[index]
        record["_requested_date"] = day.isoformat()
        record["_source_url"] = url
        record["_fetched_at_utc"] = fetched_at
        records.append(record)

    log.info("%s: %d table rows", day.isoformat(), len(records))
    return records


def daterange_descending(start: date, end: date) -> Iterable[date]:
    current = end
    while current >= start:
        yield current
        current -= timedelta(days=1)


def scrape_history(
    start_date: date,
    end_date: date,
    output_dir: Path,
    min_delay: float = DEFAULT_MIN_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
) -> Path:
    if start_date > end_date:
        raise ValueError("start-date must be on or before end-date")
    if min_delay < 0 or max_delay < min_delay:
        raise ValueError("Delay range must satisfy 0 <= min-delay <= max-delay")

    output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "18KGoldir-history-collector/1.0 "
            "(polite historical data collection; contact: project repository)"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fa,en;q=0.8",
    })

    all_records: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    days = list(daterange_descending(start_date, end_date))
    try:
        for index, day in enumerate(days):
            rows = fetch_day(session, day)
            for row in rows:
                fingerprint = tuple(sorted(row.items()))
                if fingerprint not in seen:
                    seen.add(fingerprint)
                    all_records.append(row)

            # Jitter is for polite pacing, not for evading blocking. Honour
            # Retry-After and stop on access-denied/rate-limit exhaustion.
            if index < len(days) - 1:
                delay = random.uniform(min_delay, max_delay)
                log.info("Waiting %.1fs before the next date request", delay)
                time.sleep(delay)
    finally:
        session.close()

    if not all_records:
        log.warning("No history rows were collected; writing a header-only CSV.")

    # Keep the union of all columns in first-seen order in case the provider
    # changes its table schema during the requested period.
    fieldnames: list[str] = []
    for record in all_records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)

    stamp = datetime.now(TEHRAN).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{stamp}.csv"
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        if fieldnames:
            writer.writeheader()
            writer.writerows(all_records)

    log.info("Saved %d rows to %s", len(all_records), output_path.resolve())
    return output_path


def parse_args() -> argparse.Namespace:
    now = datetime.now(TEHRAN).date()
    parser = argparse.ArgumentParser(
        description="Collect RialNerkh 18K-gold daily history from today back to a start date."
    )
    parser.add_argument("--start-date", type=date.fromisoformat, default=DEFAULT_START,
                        help="First date to include, YYYY-MM-DD (default: 2026-08-01)")
    parser.add_argument("--end-date", type=date.fromisoformat, default=now,
                        help="Last date to include, YYYY-MM-DD (default: today in Tehran)")
    parser.add_argument("--output-dir", type=Path, default=Path("data"),
                        help="CSV output folder (default: ./data)")
    parser.add_argument("--min-delay", type=float, default=DEFAULT_MIN_DELAY,
                        help="Minimum seconds between daily requests (default: 4)")
    parser.add_argument("--max-delay", type=float, default=DEFAULT_MAX_DELAY,
                        help="Maximum seconds between daily requests (default: 8)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        scrape_history(
            args.start_date, args.end_date, args.output_dir,
            args.min_delay, args.max_delay,
        )
    except (ValueError, RuntimeError, RequestException) as exc:
        log.error("%s", exc)
        raise SystemExit(1)
