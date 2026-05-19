"""Portfolio and position risk management rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from utils.paths import resolve_project_path


@dataclass(frozen=True)
class RiskResult:
    """Summary of a risk sizing run."""

    index_name: str
    input_symbols: int
    eligible_symbols: int
    selected_symbols: int
    total_allocated_capital: float
    output_parquet_path: Path
    output_csv_path: Path


def run_portfolio_risk(
    index_name: str,
    settings: dict[str, Any],
    symbols: list[str] | None = None,
    limit: int | None = None,
) -> RiskResult:
    """Apply portfolio risk rules to the latest screen output."""
    screen_path = get_latest_screen_path(index_name=index_name, settings=settings)
    if not screen_path.exists():
        raise FileNotFoundError(
            f"Latest screen file not found: {screen_path}. "
            "Run `python main.py screen --index NIFTY50` first."
        )

    screen = pd.read_parquet(screen_path)
    if symbols:
        requested = {symbol.upper() for symbol in symbols}
        screen = screen[screen["symbol"].isin(requested)].copy()
        missing = requested.difference(set(screen["symbol"]))
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise FileNotFoundError(f"Screen rows not found for: {missing_text}")

    risk_frame = apply_risk_rules(screen=screen, settings=settings)
    if limit is not None:
        risk_frame = risk_frame.head(limit).copy()
        risk_frame["portfolio_rank"] = range(1, len(risk_frame) + 1)

    parquet_path, csv_path = save_risk_frame(
        risk_frame=risk_frame,
        index_name=index_name,
        settings=settings,
    )
    selected = risk_frame[risk_frame["risk_status"] == "selected"]
    return RiskResult(
        index_name=index_name.upper(),
        input_symbols=len(screen),
        eligible_symbols=int((risk_frame["risk_status"] == "selected").sum()),
        selected_symbols=len(selected),
        total_allocated_capital=float(selected["position_value"].sum()),
        output_parquet_path=parquet_path,
        output_csv_path=csv_path,
    )


def apply_risk_rules(screen: pd.DataFrame, settings: dict[str, Any]) -> pd.DataFrame:
    """Filter, rank, and size screen candidates using risk rules."""
    config = settings["risk"]
    required_columns = {
        "as_of_date",
        "symbol",
        "price",
        "total_score",
        "screen_result",
        "atr_pct",
        "avg_turnover_20",
        "rank",
    }
    missing = required_columns.difference(screen.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Screen data missing required columns: {missing_text}")

    candidates = screen.copy()
    candidates["risk_status"] = "filtered"
    candidates["risk_reason"] = "Not eligible"
    allowed_results = set(config["allowed_screen_results"])
    eligible_mask = (
        candidates["screen_result"].isin(allowed_results)
        & (candidates["total_score"] >= config["min_total_score"])
        & (candidates["price"] > 0)
        & candidates["atr_pct"].notna()
        & (candidates["atr_pct"] > 0)
    )
    candidates.loc[eligible_mask, "risk_status"] = "eligible"
    candidates.loc[eligible_mask, "risk_reason"] = "Eligible before portfolio caps"

    eligible = candidates[eligible_mask].copy()
    eligible = eligible.sort_values(
        by=["total_score", "rank"],
        ascending=[False, True],
    ).head(config["max_positions"])
    eligible["portfolio_rank"] = range(1, len(eligible) + 1)
    eligible = add_position_sizing(eligible, config)
    eligible["risk_status"] = "selected"
    eligible["risk_reason"] = "Selected within portfolio caps"
    eligible["risk_evaluated_at_utc"] = pd.Timestamp(datetime.now(tz=UTC))

    output_columns = [
        "portfolio_rank",
        "as_of_date",
        "symbol",
        "screen_result",
        "total_score",
        "price",
        "atr_pct",
        "stop_loss_pct",
        "stop_loss_price",
        "risk_per_share",
        "position_shares",
        "position_value",
        "portfolio_weight",
        "capital_at_risk",
        "avg_turnover_20",
        "risk_status",
        "risk_reason",
        "risk_evaluated_at_utc",
    ]
    return eligible[output_columns].reset_index(drop=True)


def add_position_sizing(candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Calculate stop loss and position sizing fields."""
    sized = candidates.copy()
    portfolio_value = float(config["portfolio_value"])
    risk_budget = portfolio_value * float(config["risk_per_position_pct"])
    max_position_value = portfolio_value * float(config["max_position_pct"])

    stop_loss_pct = sized["atr_pct"] * float(config["stop_loss_atr_multiple"])
    stop_loss_pct = stop_loss_pct.clip(
        lower=float(config["min_stop_loss_pct"]),
        upper=float(config["max_stop_loss_pct"]),
    )
    sized["stop_loss_pct"] = stop_loss_pct
    sized["stop_loss_price"] = sized["price"] * (1 - sized["stop_loss_pct"])
    sized["risk_per_share"] = sized["price"] - sized["stop_loss_price"]

    shares_by_risk = risk_budget / sized["risk_per_share"]
    shares_by_cap = max_position_value / sized["price"]
    sized["position_shares"] = pd.concat([shares_by_risk, shares_by_cap], axis=1).min(axis=1)
    sized["position_shares"] = sized["position_shares"].fillna(0).astype(int)
    sized["position_value"] = sized["position_shares"] * sized["price"]
    sized["portfolio_weight"] = sized["position_value"] / portfolio_value
    sized["capital_at_risk"] = sized["position_shares"] * sized["risk_per_share"]
    return sized


def save_risk_frame(
    risk_frame: pd.DataFrame,
    index_name: str,
    settings: dict[str, Any],
) -> tuple[Path, Path]:
    """Save risk-adjusted candidates as parquet and CSV."""
    output_dir = get_risk_dir(index_name=index_name, settings=settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_date = pd.to_datetime(risk_frame["as_of_date"]).max().strftime("%Y%m%d")
    index_slug = index_name.lower()
    parquet_path = output_dir / f"{index_slug}_risk_{latest_date}.parquet"
    csv_path = output_dir / f"{index_slug}_risk_{latest_date}.csv"
    latest_parquet_path = output_dir / f"{index_slug}_risk_latest.parquet"
    latest_csv_path = output_dir / f"{index_slug}_risk_latest.csv"

    risk_frame.to_parquet(parquet_path, index=False)
    risk_frame.to_csv(csv_path, index=False)
    risk_frame.to_parquet(latest_parquet_path, index=False)
    risk_frame.to_csv(latest_csv_path, index=False)
    return parquet_path, csv_path


def get_latest_screen_path(index_name: str, settings: dict[str, Any]) -> Path:
    """Return latest screen parquet path."""
    return (
        resolve_project_path(settings["storage"]["signals_data_dir"])
        / settings["screening"]["output_subdir"]
        / index_name.lower()
        / f"{index_name.lower()}_screen_latest.parquet"
    )


def get_risk_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return risk output directory."""
    return (
        resolve_project_path(settings["storage"]["signals_data_dir"])
        / settings["risk"]["output_subdir"]
        / index_name.lower()
    )
