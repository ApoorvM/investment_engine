"""Technical indicator calculations for processed OHLCV data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from utils.paths import resolve_project_path


@dataclass(frozen=True)
class IndicatorResult:
    """Summary for one indicator-enriched symbol file."""

    symbol: str
    status: str
    rows_in: int
    rows_out: int
    output_path: Path | None
    message: str


@dataclass(frozen=True)
class IndicatorBatch:
    """Summary for a batch indicator run."""

    index_name: str
    requested_files: int
    successful_files: int
    failed_files: int
    results: list[IndicatorResult]


def build_indicators_for_universe(
    index_name: str,
    settings: dict[str, Any],
    symbols: list[str] | None = None,
    limit: int | None = None,
) -> IndicatorBatch:
    """Build indicators for processed OHLCV parquet files."""
    input_dir = get_processed_ohlcv_dir(index_name=index_name, settings=settings)
    if not input_dir.exists():
        raise FileNotFoundError(
            f"Processed OHLCV directory not found: {input_dir}. "
            "Run `python main.py process-prices --index NIFTY50` first."
        )

    input_files = sorted(input_dir.glob("*.parquet"))
    if symbols:
        requested = {symbol.lower() for symbol in symbols}
        input_files = [path for path in input_files if path.stem.lower() in requested]
        found = {path.stem.lower() for path in input_files}
        missing = requested.difference(found)
        if missing:
            missing_text = ", ".join(sorted(symbol.upper() for symbol in missing))
            raise FileNotFoundError(f"Processed OHLCV files not found for: {missing_text}")

    if limit is not None:
        input_files = input_files[:limit]

    results = [
        build_indicators_for_file(path=path, index_name=index_name, settings=settings)
        for path in input_files
    ]
    successful = sum(1 for result in results if result.status == "success")
    failed = len(results) - successful
    return IndicatorBatch(
        index_name=index_name.upper(),
        requested_files=len(results),
        successful_files=successful,
        failed_files=failed,
        results=results,
    )


def build_indicators_for_file(
    path: Path,
    index_name: str,
    settings: dict[str, Any],
) -> IndicatorResult:
    """Build indicators for one processed OHLCV parquet file."""
    try:
        frame = pd.read_parquet(path)
        enriched = add_technical_indicators(frame=frame, settings=settings)
        symbol = str(enriched["symbol"].iloc[0])
        output_path = save_indicator_frame(
            frame=enriched,
            symbol=symbol,
            index_name=index_name,
            settings=settings,
        )
        return IndicatorResult(
            symbol=symbol,
            status="success",
            rows_in=len(frame),
            rows_out=len(enriched),
            output_path=output_path,
            message="Indicators built",
        )
    except Exception as exc:
        return IndicatorResult(
            symbol=path.stem.upper(),
            status="failed",
            rows_in=0,
            rows_out=0,
            output_path=None,
            message=str(exc),
        )


def add_technical_indicators(frame: pd.DataFrame, settings: dict[str, Any]) -> pd.DataFrame:
    """Add SMA, EMA, RSI, MACD, ATR, and volume indicators."""
    indicators = settings["indicators"]
    price_column = indicators["price_column"]
    required_columns = {"date", price_column, "adj_high", "adj_low", "volume", "symbol"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Processed OHLCV data missing required columns: {missing}")

    enriched = frame.copy()
    enriched["date"] = pd.to_datetime(enriched["date"]).dt.tz_localize(None)
    enriched = enriched.sort_values("date").reset_index(drop=True)

    price = pd.to_numeric(enriched[price_column], errors="coerce")
    high = pd.to_numeric(enriched["adj_high"], errors="coerce")
    low = pd.to_numeric(enriched["adj_low"], errors="coerce")
    volume = pd.to_numeric(enriched["volume"], errors="coerce")

    for window in indicators["sma_windows"]:
        enriched[f"sma_{window}"] = price.rolling(window=window, min_periods=window).mean()

    for window in indicators["ema_windows"]:
        enriched[f"ema_{window}"] = price.ewm(span=window, adjust=False, min_periods=window).mean()

    enriched[f"rsi_{indicators['rsi_window']}"] = calculate_rsi(
        price=price,
        window=indicators["rsi_window"],
    )

    macd_line, macd_signal, macd_histogram = calculate_macd(
        price=price,
        fast=indicators["macd_fast"],
        slow=indicators["macd_slow"],
        signal=indicators["macd_signal"],
    )
    enriched["macd"] = macd_line
    enriched["macd_signal"] = macd_signal
    enriched["macd_histogram"] = macd_histogram

    enriched[f"atr_{indicators['atr_window']}"] = calculate_atr(
        high=high,
        low=low,
        close=price,
        window=indicators["atr_window"],
    )

    for window in indicators["volume_sma_windows"]:
        enriched[f"volume_sma_{window}"] = volume.rolling(
            window=window,
            min_periods=window,
        ).mean()
        enriched[f"volume_ratio_{window}"] = volume / enriched[f"volume_sma_{window}"]

    enriched["daily_return"] = price.pct_change()
    enriched["indicator_price_column"] = price_column
    enriched["indicators_built_at_utc"] = pd.Timestamp(datetime.now(tz=UTC))
    return enriched


def calculate_rsi(price: pd.Series, window: int) -> pd.Series:
    """Calculate Relative Strength Index using Wilder-style smoothing."""
    delta = price.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    average_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.clip(lower=0, upper=100)


def calculate_macd(
    price: pd.Series,
    fast: int,
    slow: int,
    signal: int,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, signal line, and histogram."""
    fast_ema = price.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = price.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int,
) -> pd.Series:
    """Calculate Average True Range."""
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def save_indicator_frame(
    frame: pd.DataFrame,
    symbol: str,
    index_name: str,
    settings: dict[str, Any],
) -> Path:
    """Save indicator-enriched data to parquet."""
    output_dir = get_indicator_dir(index_name=index_name, settings=settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{symbol.lower()}.parquet"
    frame.to_parquet(output_path, index=False)
    return output_path


def get_processed_ohlcv_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return the processed OHLCV input directory for an index."""
    return (
        resolve_project_path(settings["storage"]["processed_data_dir"])
        / settings["processing"]["ohlcv_subdir"]
        / index_name.lower()
    )


def get_indicator_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return the indicator output directory for an index."""
    return (
        resolve_project_path(settings["storage"]["processed_data_dir"])
        / settings["indicators"]["output_subdir"]
        / index_name.lower()
    )
