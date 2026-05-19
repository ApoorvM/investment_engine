"""Basic momentum, trend, volatility, and liquidity screening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from utils.paths import resolve_project_path


@dataclass(frozen=True)
class ScreeningResult:
    """Summary of a screening run."""

    index_name: str
    screened_symbols: int
    watchlist_symbols: int
    output_parquet_path: Path
    output_csv_path: Path


def run_basic_screen(
    index_name: str,
    settings: dict[str, Any],
    symbols: list[str] | None = None,
    limit: int | None = None,
) -> ScreeningResult:
    """Run the Phase 7 basic screening engine for an index."""
    indicator_dir = get_indicator_dir(index_name=index_name, settings=settings)
    if not indicator_dir.exists():
        raise FileNotFoundError(
            f"Indicator directory not found: {indicator_dir}. "
            "Run `python main.py build-indicators --index NIFTY50` first."
        )

    input_files = sorted(indicator_dir.glob("*.parquet"))
    if symbols:
        requested = {symbol.lower() for symbol in symbols}
        input_files = [path for path in input_files if path.stem.lower() in requested]
        found = {path.stem.lower() for path in input_files}
        missing = requested.difference(found)
        if missing:
            missing_text = ", ".join(sorted(symbol.upper() for symbol in missing))
            raise FileNotFoundError(f"Indicator files not found for: {missing_text}")

    if limit is not None:
        input_files = input_files[:limit]

    rows = [screen_symbol_file(path=path, settings=settings) for path in input_files]
    screen = pd.DataFrame(rows)
    if screen.empty:
        raise ValueError("No symbols available for screening")

    screen = screen.sort_values(
        by=["recommendation_rank", "total_score", "momentum_score", "trend_score"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)
    screen["rank"] = range(1, len(screen) + 1)

    parquet_path, csv_path = save_screen(
        screen=screen,
        index_name=index_name,
        settings=settings,
    )
    watchlist_count = int((screen["screen_result"] == "watchlist").sum())
    return ScreeningResult(
        index_name=index_name.upper(),
        screened_symbols=len(screen),
        watchlist_symbols=watchlist_count,
        output_parquet_path=parquet_path,
        output_csv_path=csv_path,
    )


def screen_symbol_file(path: Path, settings: dict[str, Any]) -> dict[str, Any]:
    """Screen one indicator parquet file and return a summary row."""
    frame = pd.read_parquet(path)
    return screen_symbol_frame(frame=frame, settings=settings)


def screen_symbol_frame(frame: pd.DataFrame, settings: dict[str, Any]) -> dict[str, Any]:
    """Score one symbol using the latest available indicator row."""
    config = settings["screening"]
    price_column = config["price_column"]
    required_columns = {
        "date",
        "symbol",
        price_column,
        "sma_50",
        "sma_200",
        "rsi_14",
        "macd_histogram",
        "atr_14",
        "volume",
        "volume_sma_20",
        "volume_ratio_20",
        "daily_return",
    }
    missing = required_columns.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Indicator frame missing required columns: {missing_text}")

    data = frame.copy().sort_values("date").reset_index(drop=True)
    latest = data.iloc[-1]
    close = float(latest[price_column])
    atr_pct = safe_divide(float(latest["atr_14"]), close)
    avg_turnover_20 = float(latest["volume_sma_20"]) * close
    volatility_63d = float(data["daily_return"].tail(63).std())

    return_1m = calculate_lookback_return(data, price_column, config["lookback_1m"])
    return_3m = calculate_lookback_return(data, price_column, config["lookback_3m"])
    return_6m = calculate_lookback_return(data, price_column, config["lookback_6m"])

    momentum_score = score_momentum(return_1m, return_3m, return_6m, float(latest["rsi_14"]))
    trend_score = score_trend(
        close=close,
        sma_50=float(latest["sma_50"]) if pd.notna(latest["sma_50"]) else None,
        sma_200=float(latest["sma_200"]) if pd.notna(latest["sma_200"]) else None,
        macd_histogram=float(latest["macd_histogram"]) if pd.notna(latest["macd_histogram"]) else None,
    )
    volatility_score = score_volatility(
        atr_pct=atr_pct,
        volatility_63d=volatility_63d,
        max_atr_pct=config["max_atr_pct"],
        max_daily_volatility_63d=config["max_daily_volatility_63d"],
    )
    liquidity_score = score_liquidity(
        avg_turnover_20=avg_turnover_20,
        min_avg_turnover_inr=config["min_avg_turnover_inr"],
        volume_ratio_20=float(latest["volume_ratio_20"]),
        min_volume_ratio_20=config["min_volume_ratio_20"],
    )
    total_score = round(
        0.35 * momentum_score
        + 0.35 * trend_score
        + 0.15 * volatility_score
        + 0.15 * liquidity_score,
        2,
    )
    screen_result = classify_screen_result(
        total_score=total_score,
        trend_score=trend_score,
        liquidity_score=liquidity_score,
        threshold=config["watchlist_score_threshold"],
        rows_available=len(data),
        min_history_rows=config["min_history_rows"],
    )

    return {
        "as_of_date": pd.Timestamp(latest["date"]),
        "symbol": str(latest["symbol"]),
        "price": close,
        "total_score": total_score,
        "momentum_score": momentum_score,
        "trend_score": trend_score,
        "volatility_score": volatility_score,
        "liquidity_score": liquidity_score,
        "screen_result": screen_result,
        "recommendation_rank": recommendation_rank(screen_result),
        "return_1m": return_1m,
        "return_3m": return_3m,
        "return_6m": return_6m,
        "rsi_14": float(latest["rsi_14"]) if pd.notna(latest["rsi_14"]) else pd.NA,
        "macd_histogram": float(latest["macd_histogram"]) if pd.notna(latest["macd_histogram"]) else pd.NA,
        "atr_pct": atr_pct,
        "daily_volatility_63d": volatility_63d,
        "volume_ratio_20": float(latest["volume_ratio_20"]),
        "avg_turnover_20": avg_turnover_20,
        "rows_available": len(data),
        "screened_at_utc": pd.Timestamp(datetime.now(tz=UTC)),
    }


def calculate_lookback_return(
    frame: pd.DataFrame,
    price_column: str,
    lookback: int,
) -> float:
    """Calculate return from a fixed row lookback to the latest row."""
    if len(frame) <= lookback:
        return float("nan")
    latest_price = float(frame[price_column].iloc[-1])
    past_price = float(frame[price_column].iloc[-lookback - 1])
    return safe_divide(latest_price - past_price, past_price)


def score_momentum(
    return_1m: float,
    return_3m: float,
    return_6m: float,
    rsi_14: float,
) -> int:
    """Score return momentum and RSI quality out of 100."""
    score = 0
    if pd.notna(return_1m) and return_1m > 0:
        score += 20
    if pd.notna(return_3m) and return_3m > 0.05:
        score += 30
    elif pd.notna(return_3m) and return_3m > 0:
        score += 15
    if pd.notna(return_6m) and return_6m > 0.10:
        score += 30
    elif pd.notna(return_6m) and return_6m > 0:
        score += 15
    if pd.notna(rsi_14) and 45 <= rsi_14 <= 70:
        score += 20
    elif pd.notna(rsi_14) and 35 <= rsi_14 < 45:
        score += 10
    return min(score, 100)


def score_trend(
    close: float,
    sma_50: float | None,
    sma_200: float | None,
    macd_histogram: float | None,
) -> int:
    """Score trend alignment out of 100."""
    score = 0
    if sma_50 is not None and close > sma_50:
        score += 30
    if sma_200 is not None and close > sma_200:
        score += 30
    if sma_50 is not None and sma_200 is not None and sma_50 > sma_200:
        score += 25
    if macd_histogram is not None and macd_histogram > 0:
        score += 15
    return min(score, 100)


def score_volatility(
    atr_pct: float,
    volatility_63d: float,
    max_atr_pct: float,
    max_daily_volatility_63d: float,
) -> int:
    """Score volatility acceptability out of 100."""
    score = 0
    if pd.notna(atr_pct):
        if atr_pct <= max_atr_pct * 0.5:
            score += 50
        elif atr_pct <= max_atr_pct:
            score += 30
    if pd.notna(volatility_63d):
        if volatility_63d <= max_daily_volatility_63d * 0.5:
            score += 50
        elif volatility_63d <= max_daily_volatility_63d:
            score += 30
    return min(score, 100)


def score_liquidity(
    avg_turnover_20: float,
    min_avg_turnover_inr: float,
    volume_ratio_20: float,
    min_volume_ratio_20: float,
) -> int:
    """Score liquidity and current volume participation out of 100."""
    score = 0
    if pd.notna(avg_turnover_20):
        if avg_turnover_20 >= min_avg_turnover_inr * 2:
            score += 60
        elif avg_turnover_20 >= min_avg_turnover_inr:
            score += 40
    if pd.notna(volume_ratio_20):
        if volume_ratio_20 >= 1:
            score += 40
        elif volume_ratio_20 >= min_volume_ratio_20:
            score += 25
    return min(score, 100)


def classify_screen_result(
    total_score: float,
    trend_score: int,
    liquidity_score: int,
    threshold: float,
    rows_available: int,
    min_history_rows: int,
) -> str:
    """Classify screen output for watchlist use."""
    if rows_available < min_history_rows:
        return "insufficient_history"
    if liquidity_score < 40:
        return "low_liquidity"
    if total_score >= threshold and trend_score >= 60:
        return "watchlist"
    if total_score >= threshold * 0.75:
        return "monitor"
    return "avoid"


def recommendation_rank(screen_result: str) -> int:
    """Return sortable rank bucket for screen labels."""
    ranks = {
        "watchlist": 1,
        "monitor": 2,
        "avoid": 3,
        "low_liquidity": 4,
        "insufficient_history": 5,
    }
    return ranks.get(screen_result, 99)


def save_screen(
    screen: pd.DataFrame,
    index_name: str,
    settings: dict[str, Any],
) -> tuple[Path, Path]:
    """Save screen output as parquet and CSV."""
    output_dir = get_screen_dir(index_name=index_name, settings=settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_date = pd.to_datetime(screen["as_of_date"]).max().strftime("%Y%m%d")
    index_slug = index_name.lower()
    parquet_path = output_dir / f"{index_slug}_screen_{latest_date}.parquet"
    csv_path = output_dir / f"{index_slug}_screen_{latest_date}.csv"
    latest_parquet_path = output_dir / f"{index_slug}_screen_latest.parquet"
    latest_csv_path = output_dir / f"{index_slug}_screen_latest.csv"

    screen.to_parquet(parquet_path, index=False)
    screen.to_csv(csv_path, index=False)
    screen.to_parquet(latest_parquet_path, index=False)
    screen.to_csv(latest_csv_path, index=False)
    return parquet_path, csv_path


def get_indicator_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return indicator input directory for an index."""
    return (
        resolve_project_path(settings["storage"]["processed_data_dir"])
        / settings["indicators"]["output_subdir"]
        / index_name.lower()
    )


def get_screen_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return screen output directory for an index."""
    return (
        resolve_project_path(settings["storage"]["signals_data_dir"])
        / settings["screening"]["output_subdir"]
        / index_name.lower()
    )


def safe_divide(numerator: float, denominator: float) -> float:
    """Divide while avoiding zero denominator errors."""
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return numerator / denominator
