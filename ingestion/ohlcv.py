"""Download and store OHLCV price history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from utils.paths import resolve_project_path


@dataclass(frozen=True)
class PriceDownloadResult:
    """Summary of a single symbol price download."""

    symbol: str
    yfinance_symbol: str
    row_count: int
    output_path: Path | None
    status: str
    message: str
    mode: str
    start_date: str


@dataclass(frozen=True)
class PriceDownloadBatch:
    """Summary of a batch OHLCV download."""

    index_name: str
    requested_symbols: int
    successful_symbols: int
    failed_symbols: int
    results: list[PriceDownloadResult]


def load_latest_universe(index_name: str, settings: dict[str, Any]) -> pd.DataFrame:
    """Load the latest saved constituent universe for an index."""
    index_slug = index_name.lower()
    universe_dir = resolve_project_path(settings["storage"]["universe_data_dir"])
    universe_path = universe_dir / f"{index_slug}_constituents_latest.parquet"
    if not universe_path.exists():
        raise FileNotFoundError(
            f"Universe snapshot not found: {universe_path}. "
            "Run `python main.py fetch-universe --index NIFTY50` first."
        )

    return pd.read_parquet(universe_path)


def download_universe_ohlcv(
    index_name: str,
    settings: dict[str, Any],
    start_date: str | None = None,
    end_date: str | None = None,
    symbols: list[str] | None = None,
    limit: int | None = None,
    incremental: bool = True,
) -> PriceDownloadBatch:
    """Download OHLCV history for the latest saved universe."""
    universe = load_latest_universe(index_name=index_name, settings=settings)
    if symbols:
        requested = {symbol.upper() for symbol in symbols}
        universe = universe[universe["symbol"].isin(requested)].copy()
        missing = requested.difference(set(universe["symbol"]))
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Requested symbols not found in universe: {missing_text}")

    universe = universe.sort_values("symbol").reset_index(drop=True)
    if limit is not None:
        universe = universe.head(limit)

    results: list[PriceDownloadResult] = []
    for row in universe.itertuples(index=False):
        result = download_symbol_ohlcv(
            symbol=row.symbol,
            yfinance_symbol=row.yfinance_symbol,
            index_name=index_name,
            settings=settings,
            start_date=start_date,
            end_date=end_date,
            incremental=incremental,
        )
        results.append(result)

    successful = sum(1 for result in results if result.status == "success")
    failed = len(results) - successful
    return PriceDownloadBatch(
        index_name=index_name.upper(),
        requested_symbols=len(results),
        successful_symbols=successful,
        failed_symbols=failed,
        results=results,
    )


def download_symbol_ohlcv(
    symbol: str,
    yfinance_symbol: str,
    index_name: str,
    settings: dict[str, Any],
    start_date: str | None = None,
    end_date: str | None = None,
    incremental: bool = True,
) -> PriceDownloadResult:
    """Download and save OHLCV history for one symbol."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError(
            "yfinance is required for Phase 3. "
            "Install dependencies with `python -m pip install -r requirements.txt`."
        ) from exc

    prices_config = settings["prices"]
    output_path = get_ohlcv_path(symbol=symbol, index_name=index_name, settings=settings)
    existing = read_existing_ohlcv(output_path)
    start = determine_download_start_date(
        existing=existing,
        configured_start_date=start_date or prices_config["default_start_date"],
        incremental=incremental,
        overlap_days=prices_config["incremental_overlap_days"],
    )
    data = yf.download(
        tickers=yfinance_symbol,
        start=start,
        end=end_date,
        interval=prices_config["default_interval"],
        auto_adjust=prices_config["auto_adjust"],
        progress=False,
        threads=prices_config["threads"],
    )

    if data.empty:
        if incremental and existing is not None:
            return PriceDownloadResult(
                symbol=symbol,
                yfinance_symbol=yfinance_symbol,
                row_count=len(existing),
                output_path=output_path,
                status="success",
                message="No new rows returned by yfinance; existing file left unchanged",
                mode="incremental",
                start_date=start,
            )
        return PriceDownloadResult(
            symbol=symbol,
            yfinance_symbol=yfinance_symbol,
            row_count=0,
            output_path=None,
            status="failed",
            message="No rows returned by yfinance",
            mode="incremental" if incremental else "full",
            start_date=start,
        )

    normalized = normalize_ohlcv(
        frame=data,
        symbol=symbol,
        yfinance_symbol=yfinance_symbol,
        provider=prices_config["provider"],
    )
    if incremental:
        normalized = filter_ohlcv_from_start(frame=normalized, start_date=start)

    if normalized.empty and incremental and existing is not None:
        return PriceDownloadResult(
            symbol=symbol,
            yfinance_symbol=yfinance_symbol,
            row_count=len(existing),
            output_path=output_path,
            status="success",
            message="No rows on or after incremental start; existing file left unchanged",
            mode="incremental",
            start_date=start,
        )

    rows_before = len(existing) if existing is not None else 0
    merged = merge_ohlcv(existing=existing, new_data=normalized)
    output_path = save_ohlcv(
        frame=merged,
        symbol=symbol,
        index_name=index_name,
        settings=settings,
    )
    rows_after = len(merged)
    new_rows = max(rows_after - rows_before, 0)

    return PriceDownloadResult(
        symbol=symbol,
        yfinance_symbol=yfinance_symbol,
        row_count=rows_after,
        output_path=output_path,
        status="success",
        message=f"Downloaded from {start}; added {new_rows} net new rows",
        mode="incremental" if incremental else "full",
        start_date=start,
    )


def normalize_ohlcv(
    frame: pd.DataFrame,
    symbol: str,
    yfinance_symbol: str,
    provider: str,
) -> pd.DataFrame:
    """Normalize yfinance OHLCV output into a stable parquet schema."""
    normalized = frame.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = normalized.columns.get_level_values(0)

    normalized = normalized.reset_index()
    normalized.columns = [str(column).strip().lower().replace(" ", "_") for column in normalized.columns]

    if "date" not in normalized.columns:
        first_column = normalized.columns[0]
        normalized = normalized.rename(columns={first_column: "date"})

    rename_map = {
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "adj_close": "adj_close",
        "volume": "volume",
    }
    normalized = normalized.rename(columns=rename_map)

    required_columns = ["date", "open", "high", "low", "close", "volume"]
    missing_columns = [column for column in required_columns if column not in normalized.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"OHLCV data missing required columns: {missing}")

    output_columns = required_columns.copy()
    if "adj_close" in normalized.columns:
        output_columns.append("adj_close")

    normalized = normalized[output_columns]
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.tz_localize(None)
    normalized = normalized.dropna(subset=["date", "open", "high", "low", "close"])
    normalized = normalized.sort_values("date").drop_duplicates("date").reset_index(drop=True)

    numeric_columns = [column for column in output_columns if column != "date"]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized["symbol"] = symbol.upper()
    normalized["yfinance_symbol"] = yfinance_symbol.upper()
    normalized["provider"] = provider
    normalized["downloaded_at_utc"] = pd.Timestamp(datetime.now(tz=UTC))

    return normalized


def save_ohlcv(
    frame: pd.DataFrame,
    symbol: str,
    index_name: str,
    settings: dict[str, Any],
) -> Path:
    """Save normalized OHLCV data to a symbol-level parquet file."""
    output_path = get_ohlcv_path(symbol=symbol, index_name=index_name, settings=settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, index=False)
    return output_path


def get_ohlcv_path(symbol: str, index_name: str, settings: dict[str, Any]) -> Path:
    """Return the raw OHLCV parquet path for one symbol."""
    raw_dir = resolve_project_path(settings["storage"]["raw_data_dir"])
    return (
        raw_dir
        / settings["prices"]["raw_ohlcv_subdir"]
        / index_name.lower()
        / f"{symbol.lower()}.parquet"
    )


def read_existing_ohlcv(path: Path) -> pd.DataFrame | None:
    """Read an existing OHLCV parquet file if present."""
    if not path.exists():
        return None
    return pd.read_parquet(path)


def determine_download_start_date(
    existing: pd.DataFrame | None,
    configured_start_date: str,
    incremental: bool,
    overlap_days: int,
) -> str:
    """Determine the yfinance start date for full or incremental download."""
    if not incremental or existing is None or existing.empty:
        return configured_start_date

    if "date" not in existing.columns:
        raise ValueError("Existing OHLCV file does not contain a date column")

    last_date = pd.to_datetime(existing["date"]).max().date()
    overlap_start = last_date - timedelta(days=overlap_days)
    configured_date = date.fromisoformat(configured_start_date)
    start = max(overlap_start, configured_date)
    return start.isoformat()


def merge_ohlcv(
    existing: pd.DataFrame | None,
    new_data: pd.DataFrame,
) -> pd.DataFrame:
    """Merge existing and newly downloaded OHLCV rows by date."""
    if existing is None or existing.empty:
        combined = new_data.copy()
    else:
        combined = pd.concat([existing, new_data], ignore_index=True)

    combined["date"] = pd.to_datetime(combined["date"]).dt.tz_localize(None)
    combined = combined.sort_values(["date", "downloaded_at_utc"])
    combined = combined.drop_duplicates(subset=["date"], keep="last")
    return combined.sort_values("date").reset_index(drop=True)


def filter_ohlcv_from_start(frame: pd.DataFrame, start_date: str) -> pd.DataFrame:
    """Keep only rows on or after the requested provider start date."""
    filtered = frame.copy()
    start_timestamp = pd.Timestamp(start_date)
    filtered["date"] = pd.to_datetime(filtered["date"]).dt.tz_localize(None)
    return filtered[filtered["date"] >= start_timestamp].reset_index(drop=True)
