"""Clean and validate raw OHLCV parquet files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from utils.paths import resolve_project_path


REQUIRED_RAW_COLUMNS = {
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "symbol",
    "yfinance_symbol",
    "provider",
}
PRICE_COLUMNS = ["open", "high", "low", "close"]


@dataclass(frozen=True)
class CleaningResult:
    """Summary for one cleaned symbol file."""

    symbol: str
    status: str
    rows_in: int
    rows_out: int
    output_path: Path | None
    warnings: list[str]


@dataclass(frozen=True)
class CleaningBatch:
    """Summary for a batch cleaning run."""

    index_name: str
    requested_files: int
    successful_files: int
    failed_files: int
    results: list[CleaningResult]


def process_ohlcv_universe(
    index_name: str,
    settings: dict[str, Any],
    symbols: list[str] | None = None,
    limit: int | None = None,
) -> CleaningBatch:
    """Clean raw OHLCV parquet files for an index."""
    raw_dir = get_raw_ohlcv_dir(index_name=index_name, settings=settings)
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw OHLCV directory not found: {raw_dir}. "
            "Run `python main.py fetch-prices --index NIFTY50` first."
        )

    raw_files = sorted(raw_dir.glob("*.parquet"))
    if symbols:
        requested = {symbol.lower() for symbol in symbols}
        raw_files = [path for path in raw_files if path.stem.lower() in requested]
        found = {path.stem.lower() for path in raw_files}
        missing = requested.difference(found)
        if missing:
            missing_text = ", ".join(sorted(symbol.upper() for symbol in missing))
            raise FileNotFoundError(f"Raw OHLCV files not found for: {missing_text}")

    if limit is not None:
        raw_files = raw_files[:limit]

    results = [
        process_ohlcv_file(path=path, index_name=index_name, settings=settings)
        for path in raw_files
    ]
    successful = sum(1 for result in results if result.status == "success")
    failed = len(results) - successful
    return CleaningBatch(
        index_name=index_name.upper(),
        requested_files=len(results),
        successful_files=successful,
        failed_files=failed,
        results=results,
    )


def process_ohlcv_file(
    path: Path,
    index_name: str,
    settings: dict[str, Any],
) -> CleaningResult:
    """Clean one raw OHLCV parquet file and save processed output."""
    try:
        raw = pd.read_parquet(path)
        cleaned, warnings = clean_ohlcv_frame(raw, settings=settings)
        symbol = str(cleaned["symbol"].iloc[0])
        output_path = save_processed_ohlcv(
            frame=cleaned,
            symbol=symbol,
            index_name=index_name,
            settings=settings,
        )
        return CleaningResult(
            symbol=symbol,
            status="success",
            rows_in=len(raw),
            rows_out=len(cleaned),
            output_path=output_path,
            warnings=warnings,
        )
    except Exception as exc:
        return CleaningResult(
            symbol=path.stem.upper(),
            status="failed",
            rows_in=0,
            rows_out=0,
            output_path=None,
            warnings=[str(exc)],
        )


def clean_ohlcv_frame(
    frame: pd.DataFrame,
    settings: dict[str, Any],
) -> tuple[pd.DataFrame, list[str]]:
    """Validate, clean, and enrich one raw OHLCV frame."""
    validate_required_columns(frame)
    cleaned = frame.copy()
    warnings: list[str] = []

    cleaned["date"] = pd.to_datetime(cleaned["date"]).dt.tz_localize(None)
    cleaned = cleaned.sort_values("date")
    duplicate_count = int(cleaned["date"].duplicated().sum())
    if duplicate_count:
        warnings.append(f"Dropped {duplicate_count} duplicate date rows")
    cleaned = cleaned.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

    for column in PRICE_COLUMNS + ["volume"]:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    missing_price_ratio = float(cleaned[PRICE_COLUMNS].isna().any(axis=1).mean())
    max_missing = settings["processing"]["max_missing_price_ratio"]
    if missing_price_ratio > max_missing:
        raise ValueError(
            f"Missing price ratio {missing_price_ratio:.2%} exceeds limit {max_missing:.2%}"
        )

    before_drop = len(cleaned)
    cleaned = cleaned.dropna(subset=PRICE_COLUMNS + ["volume"]).reset_index(drop=True)
    dropped_missing = before_drop - len(cleaned)
    if dropped_missing:
        warnings.append(f"Dropped {dropped_missing} rows with missing OHLCV values")

    invalid_mask = (
        (cleaned[PRICE_COLUMNS] <= 0).any(axis=1)
        | (cleaned["volume"] < 0)
        | (cleaned["high"] < cleaned[["open", "close", "low"]].max(axis=1))
        | (cleaned["low"] > cleaned[["open", "close", "high"]].min(axis=1))
    )
    invalid_count = int(invalid_mask.sum())
    if invalid_count:
        raise ValueError(f"Found {invalid_count} invalid OHLCV rows")

    min_rows = settings["processing"]["min_rows"]
    if len(cleaned) < min_rows:
        raise ValueError(f"Only {len(cleaned)} rows available, minimum required is {min_rows}")

    cleaned = add_adjusted_columns(cleaned)
    cleaned["processed_at_utc"] = pd.Timestamp(datetime.now(tz=UTC))
    return cleaned, warnings


def validate_required_columns(frame: pd.DataFrame) -> None:
    """Ensure a raw OHLCV frame contains the required schema."""
    missing = REQUIRED_RAW_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Raw OHLCV data missing required columns: {missing_text}")


def add_adjusted_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add adjusted OHLC columns using adj_close when available."""
    adjusted = frame.copy()
    if "adj_close" not in adjusted.columns:
        adjusted["adj_open"] = adjusted["open"]
        adjusted["adj_high"] = adjusted["high"]
        adjusted["adj_low"] = adjusted["low"]
        adjusted["adj_close"] = adjusted["close"]
        return adjusted

    adjusted["adj_close"] = pd.to_numeric(adjusted["adj_close"], errors="coerce")
    adjustment_factor = adjusted["adj_close"] / adjusted["close"]
    adjustment_factor = adjustment_factor.replace([float("inf"), -float("inf")], pd.NA)
    adjustment_factor = adjustment_factor.fillna(1.0)

    adjusted["adj_open"] = adjusted["open"] * adjustment_factor
    adjusted["adj_high"] = adjusted["high"] * adjustment_factor
    adjusted["adj_low"] = adjusted["low"] * adjustment_factor
    return adjusted


def save_processed_ohlcv(
    frame: pd.DataFrame,
    symbol: str,
    index_name: str,
    settings: dict[str, Any],
) -> Path:
    """Save cleaned OHLCV data to processed parquet storage."""
    output_dir = get_processed_ohlcv_dir(index_name=index_name, settings=settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{symbol.lower()}.parquet"
    frame.to_parquet(output_path, index=False)
    return output_path


def get_raw_ohlcv_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return the raw OHLCV directory for an index."""
    return (
        resolve_project_path(settings["storage"]["raw_data_dir"])
        / settings["prices"]["raw_ohlcv_subdir"]
        / index_name.lower()
    )


def get_processed_ohlcv_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return the processed OHLCV directory for an index."""
    return (
        resolve_project_path(settings["storage"]["processed_data_dir"])
        / settings["processing"]["ohlcv_subdir"]
        / index_name.lower()
    )
