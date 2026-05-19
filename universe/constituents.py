"""Fetch and store index constituent snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from utils.paths import resolve_project_path


REQUIRED_SOURCE_COLUMNS = {
    "Company Name",
    "Industry",
    "Symbol",
    "Series",
    "ISIN Code",
}


@dataclass(frozen=True)
class UniverseSnapshot:
    """Metadata for a saved universe snapshot."""

    index_name: str
    row_count: int
    snapshot_date: date
    source_url: str
    snapshot_path: Path
    latest_path: Path


def fetch_index_constituents(
    index_name: str,
    settings: dict[str, Any],
    as_of_date: date | None = None,
) -> UniverseSnapshot:
    """Fetch latest constituents for an index and save parquet snapshots."""
    normalized_index = index_name.upper()
    index_config = settings["universe"]["indices"][normalized_index]
    fetched_at = datetime.now(tz=UTC)
    snapshot_date = as_of_date or fetched_at.date()

    raw_frame, source_url = _download_first_available_csv(
        source_urls=index_config["source_urls"],
        user_agent=settings["universe"]["user_agent"],
        timeout_seconds=settings["universe"]["request_timeout_seconds"],
    )
    constituents = normalize_constituents(
        raw_frame=raw_frame,
        index_name=normalized_index,
        display_name=index_config["display_name"],
        fetched_at=fetched_at,
        snapshot_date=snapshot_date,
        source_url=source_url,
    )

    return save_constituent_snapshot(
        constituents=constituents,
        index_name=normalized_index,
        snapshot_date=snapshot_date,
        settings=settings,
        source_url=source_url,
    )


def normalize_constituents(
    raw_frame: pd.DataFrame,
    index_name: str,
    display_name: str,
    fetched_at: datetime,
    snapshot_date: date,
    source_url: str,
) -> pd.DataFrame:
    """Normalize official constituent CSV columns into the project schema."""
    missing_columns = REQUIRED_SOURCE_COLUMNS.difference(raw_frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Constituent source missing required columns: {missing}")

    frame = raw_frame.copy()
    frame = frame.rename(
        columns={
            "Company Name": "company_name",
            "Industry": "industry",
            "Symbol": "symbol",
            "Series": "series",
            "ISIN Code": "isin",
        }
    )

    frame = frame[["company_name", "industry", "symbol", "series", "isin"]]
    for column in frame.columns:
        frame[column] = frame[column].astype(str).str.strip()

    frame["symbol"] = frame["symbol"].str.upper()
    frame = frame.sort_values("symbol").drop_duplicates("symbol").reset_index(drop=True)
    
    # Filter out dummy/placeholder symbols that may appear in NSE data
    frame = frame[~frame["company_name"].str.contains("dummy", case=False, na=False)].reset_index(drop=True)
    
    frame["nse_symbol"] = frame["symbol"]
    frame["yfinance_symbol"] = frame["symbol"] + ".NS"
    frame["index_name"] = index_name
    frame["index_display_name"] = display_name
    frame["snapshot_date"] = pd.Timestamp(snapshot_date)
    frame["fetched_at_utc"] = pd.Timestamp(fetched_at)
    frame["source_url"] = source_url

    expected_count = 50 if index_name == "NIFTY50" else None
    if expected_count is not None and len(frame) != expected_count:
        raise ValueError(
            f"{index_name} expected {expected_count} constituents, got {len(frame)}"
        )

    return frame


def save_constituent_snapshot(
    constituents: pd.DataFrame,
    index_name: str,
    snapshot_date: date,
    settings: dict[str, Any],
    source_url: str,
) -> UniverseSnapshot:
    """Save a dated parquet snapshot and update the latest parquet pointer."""
    date_format = settings["universe"]["snapshot_date_format"]
    date_suffix = snapshot_date.strftime(date_format)
    output_dir = resolve_project_path(settings["storage"]["universe_data_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    index_slug = index_name.lower()
    snapshot_path = output_dir / f"{index_slug}_constituents_{date_suffix}.parquet"
    latest_path = output_dir / f"{index_slug}_constituents_latest.parquet"

    constituents.to_parquet(snapshot_path, index=False)
    constituents.to_parquet(latest_path, index=False)

    return UniverseSnapshot(
        index_name=index_name,
        row_count=len(constituents),
        snapshot_date=snapshot_date,
        source_url=source_url,
        snapshot_path=snapshot_path,
        latest_path=latest_path,
    )


def _download_first_available_csv(
    source_urls: list[str],
    user_agent: str,
    timeout_seconds: int,
) -> tuple[pd.DataFrame, str]:
    """Download constituents from the first source URL that returns valid CSV."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/csv,application/csv,text/plain,*/*",
        "Referer": "https://www.niftyindices.com/",
    }
    session = requests.Session()
    errors: list[str] = []

    for source_url in source_urls:
        try:
            response = session.get(
                source_url,
                headers=headers,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            frame = pd.read_csv(StringIO(response.text))
            if REQUIRED_SOURCE_COLUMNS.issubset(frame.columns):
                return frame, source_url
            errors.append(f"{source_url}: unexpected columns {list(frame.columns)}")
        except Exception as exc:
            errors.append(f"{source_url}: {exc}")

    details = "; ".join(errors)
    raise RuntimeError(f"Unable to fetch constituent CSV from configured sources. {details}")
