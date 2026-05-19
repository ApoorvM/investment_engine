"""Final signal generation from screen and risk outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from utils.paths import resolve_project_path


@dataclass(frozen=True)
class SignalResult:
    """Summary of a final signal generation run."""

    index_name: str
    total_symbols: int
    buy_candidates: int
    watchlist_symbols: int
    output_parquet_path: Path
    output_csv_path: Path


def generate_signals(
    index_name: str,
    settings: dict[str, Any],
    symbols: list[str] | None = None,
) -> SignalResult:
    """Generate final risk-aware signals for an index."""
    screen_path = get_latest_screen_path(index_name=index_name, settings=settings)
    risk_path = get_latest_risk_path(index_name=index_name, settings=settings)
    if not screen_path.exists():
        raise FileNotFoundError(
            f"Latest screen file not found: {screen_path}. "
            "Run `python main.py screen --index NIFTY50` first."
        )
    if not risk_path.exists():
        raise FileNotFoundError(
            f"Latest risk file not found: {risk_path}. "
            "Run `python main.py risk --index NIFTY50` first."
        )

    screen = pd.read_parquet(screen_path)
    risk = pd.read_parquet(risk_path)
    if symbols:
        requested = {symbol.upper() for symbol in symbols}
        screen = screen[screen["symbol"].isin(requested)].copy()
        missing = requested.difference(set(screen["symbol"]))
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise FileNotFoundError(f"Screen rows not found for: {missing_text}")

    signals = build_signal_frame(screen=screen, risk=risk, settings=settings)
    parquet_path, csv_path = save_signal_frame(
        signals=signals,
        index_name=index_name,
        settings=settings,
    )
    return SignalResult(
        index_name=index_name.upper(),
        total_symbols=len(signals),
        buy_candidates=int((signals["signal"] == "buy_candidate").sum()),
        watchlist_symbols=int((signals["signal"] == "watchlist").sum()),
        output_parquet_path=parquet_path,
        output_csv_path=csv_path,
    )


def build_signal_frame(
    screen: pd.DataFrame,
    risk: pd.DataFrame,
    settings: dict[str, Any],
) -> pd.DataFrame:
    """Create final signal labels and attach risk sizing when available."""
    validate_screen_columns(screen)
    validate_risk_columns(risk)

    risk_columns = [
        "symbol",
        "portfolio_rank",
        "stop_loss_price",
        "stop_loss_pct",
        "position_shares",
        "position_value",
        "portfolio_weight",
        "capital_at_risk",
        "risk_status",
        "risk_reason",
    ]
    merged = screen.merge(risk[risk_columns], on="symbol", how="left")
    merged["risk_status"] = merged["risk_status"].fillna("not_selected")
    merged["risk_reason"] = merged["risk_reason"].fillna("Not selected by risk layer")
    merged["signal"] = merged.apply(classify_signal, axis=1, settings=settings)
    merged["signal_rank_bucket"] = merged["signal"].map(signal_rank_bucket)
    merged["signal_generated_at_utc"] = pd.Timestamp(datetime.now(tz=UTC))

    output_columns = [
        "as_of_date",
        "symbol",
        "signal",
        "signal_rank_bucket",
        "rank",
        "portfolio_rank",
        "price",
        "total_score",
        "momentum_score",
        "trend_score",
        "volatility_score",
        "liquidity_score",
        "screen_result",
        "risk_status",
        "risk_reason",
        "position_shares",
        "position_value",
        "portfolio_weight",
        "stop_loss_price",
        "stop_loss_pct",
        "capital_at_risk",
        "return_1m",
        "return_3m",
        "return_6m",
        "rsi_14",
        "atr_pct",
        "daily_volatility_63d",
        "avg_turnover_20",
        "signal_generated_at_utc",
    ]
    final = merged[output_columns].sort_values(
        by=["signal_rank_bucket", "portfolio_rank", "total_score", "rank"],
        ascending=[True, True, False, True],
        na_position="last",
    )
    return final.reset_index(drop=True)


def classify_signal(row: pd.Series, settings: dict[str, Any]) -> str:
    """Classify one row into a final signal label."""
    config = settings["signals"]
    if row["risk_status"] == "selected" and row["total_score"] >= config["buy_score_threshold"]:
        return "buy_candidate"
    if row["screen_result"] == "watchlist" and row["total_score"] >= config["watchlist_score_threshold"]:
        return "watchlist"
    if row["total_score"] >= config["hold_score_threshold"]:
        return "hold_monitor"
    return "avoid"


def signal_rank_bucket(signal: str) -> int:
    """Return sortable bucket for final signals."""
    buckets = {
        "buy_candidate": 1,
        "watchlist": 2,
        "hold_monitor": 3,
        "avoid": 4,
    }
    return buckets.get(signal, 99)


def save_signal_frame(
    signals: pd.DataFrame,
    index_name: str,
    settings: dict[str, Any],
) -> tuple[Path, Path]:
    """Save final signals as parquet and CSV."""
    output_dir = get_signal_dir(index_name=index_name, settings=settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_date = pd.to_datetime(signals["as_of_date"]).max().strftime("%Y%m%d")
    index_slug = index_name.lower()
    parquet_path = output_dir / f"{index_slug}_signals_{latest_date}.parquet"
    csv_path = output_dir / f"{index_slug}_signals_{latest_date}.csv"
    latest_parquet_path = output_dir / f"{index_slug}_signals_latest.parquet"
    latest_csv_path = output_dir / f"{index_slug}_signals_latest.csv"

    signals.to_parquet(parquet_path, index=False)
    signals.to_csv(csv_path, index=False)
    signals.to_parquet(latest_parquet_path, index=False)
    signals.to_csv(latest_csv_path, index=False)
    return parquet_path, csv_path


def validate_screen_columns(screen: pd.DataFrame) -> None:
    """Validate required screen columns."""
    required = {
        "as_of_date",
        "symbol",
        "price",
        "total_score",
        "momentum_score",
        "trend_score",
        "volatility_score",
        "liquidity_score",
        "screen_result",
        "rank",
    }
    missing = required.difference(screen.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Screen data missing required columns: {missing_text}")


def validate_risk_columns(risk: pd.DataFrame) -> None:
    """Validate required risk columns."""
    required = {
        "symbol",
        "portfolio_rank",
        "stop_loss_price",
        "stop_loss_pct",
        "position_shares",
        "position_value",
        "portfolio_weight",
        "capital_at_risk",
        "risk_status",
        "risk_reason",
    }
    missing = required.difference(risk.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Risk data missing required columns: {missing_text}")


def get_latest_screen_path(index_name: str, settings: dict[str, Any]) -> Path:
    """Return latest screen parquet path."""
    return (
        resolve_project_path(settings["storage"]["signals_data_dir"])
        / settings["screening"]["output_subdir"]
        / index_name.lower()
        / f"{index_name.lower()}_screen_latest.parquet"
    )


def get_latest_risk_path(index_name: str, settings: dict[str, Any]) -> Path:
    """Return latest risk parquet path."""
    return (
        resolve_project_path(settings["storage"]["signals_data_dir"])
        / settings["risk"]["output_subdir"]
        / index_name.lower()
        / f"{index_name.lower()}_risk_latest.parquet"
    )


def get_signal_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return final signal output directory."""
    return (
        resolve_project_path(settings["storage"]["signals_data_dir"])
        / settings["signals"]["output_subdir"]
        / index_name.lower()
    )
