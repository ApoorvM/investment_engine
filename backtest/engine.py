"""Simple historical backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from risk.portfolio import apply_risk_rules
from strategies.screening import screen_symbol_frame
from utils.paths import resolve_project_path


@dataclass(frozen=True)
class BacktestResult:
    """Summary of a completed backtest."""

    index_name: str
    periods: int
    trades: int
    start_equity: float
    end_equity: float
    total_return: float
    equity_curve_path: Path
    trades_path: Path


def run_backtest(
    index_name: str,
    settings: dict[str, Any],
    start_date: str | None = None,
    end_date: str | None = None,
    symbols: list[str] | None = None,
) -> BacktestResult:
    """Run a monthly rebalance backtest using historical indicator files."""
    frames = load_indicator_history(index_name=index_name, settings=settings, symbols=symbols)
    config = settings["backtest"]
    start = pd.Timestamp(start_date or config["start_date"])
    end = pd.Timestamp(end_date) if end_date else None
    rebalance_dates = build_rebalance_dates(
        frames=frames,
        start_date=start,
        end_date=end,
        frequency=config["rebalance_frequency"],
        max_periods=config["max_rebalance_periods"],
    )
    if len(rebalance_dates) < 2:
        raise ValueError("Backtest requires at least two rebalance dates")

    equity = float(config["initial_capital"])
    equity_rows: list[dict[str, Any]] = [
        {
            "date": rebalance_dates[0],
            "equity": equity,
            "period_return": 0.0,
            "positions": 0,
            "cash_weight": 1.0,
        }
    ]
    trade_rows: list[dict[str, Any]] = []

    for entry_date, exit_date in zip(rebalance_dates[:-1], rebalance_dates[1:]):
        screen = build_historical_screen(frames=frames, as_of_date=entry_date, settings=settings)
        if screen.empty:
            equity_rows.append(
                {
                    "date": exit_date,
                    "equity": equity,
                    "period_return": 0.0,
                    "positions": 0,
                    "cash_weight": 1.0,
                }
            )
            continue

        risk_settings = with_backtest_portfolio_value(settings, equity)
        selected = apply_risk_rules(screen=screen, settings=risk_settings)
        period_return, trades = calculate_period_return(
            selected=selected,
            frames=frames,
            entry_date=entry_date,
            exit_date=exit_date,
            equity=equity,
            transaction_cost_pct=float(config["transaction_cost_pct"]),
        )
        equity = equity * (1 + period_return)
        equity_rows.append(
            {
                "date": exit_date,
                "equity": equity,
                "period_return": period_return,
                "positions": len(selected),
                "cash_weight": max(0.0, 1.0 - float(selected["portfolio_weight"].sum())),
            }
        )
        trade_rows.extend(trades)

    equity_curve = pd.DataFrame(equity_rows)
    trade_log = pd.DataFrame(trade_rows)
    equity_path, trades_path = save_backtest_outputs(
        equity_curve=equity_curve,
        trade_log=trade_log,
        index_name=index_name,
        settings=settings,
    )
    total_return = (equity / float(config["initial_capital"])) - 1
    return BacktestResult(
        index_name=index_name.upper(),
        periods=len(equity_curve) - 1,
        trades=len(trade_log),
        start_equity=float(config["initial_capital"]),
        end_equity=equity,
        total_return=total_return,
        equity_curve_path=equity_path,
        trades_path=trades_path,
    )


def load_indicator_history(
    index_name: str,
    settings: dict[str, Any],
    symbols: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Load indicator history files for an index."""
    indicator_dir = get_indicator_dir(index_name=index_name, settings=settings)
    if not indicator_dir.exists():
        raise FileNotFoundError(
            f"Indicator directory not found: {indicator_dir}. "
            "Run `python main.py build-indicators --index NIFTY50` first."
        )

    requested = {symbol.upper() for symbol in symbols} if symbols else None
    frames: dict[str, pd.DataFrame] = {}
    for path in sorted(indicator_dir.glob("*.parquet")):
        frame = pd.read_parquet(path)
        if frame.empty:
            continue
        symbol = str(frame["symbol"].iloc[-1]).upper()
        if requested and symbol not in requested:
            continue
        frame = frame.copy()
        frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None)
        frames[symbol] = frame.sort_values("date").reset_index(drop=True)

    if requested:
        missing = requested.difference(frames)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise FileNotFoundError(f"Indicator files not found for: {missing_text}")

    return frames


def build_rebalance_dates(
    frames: dict[str, pd.DataFrame],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp | None,
    frequency: str,
    max_periods: int,
) -> list[pd.Timestamp]:
    """Build rebalance dates from available trading dates."""
    all_dates = sorted({date for frame in frames.values() for date in frame["date"]})
    dates = pd.Series(pd.to_datetime(all_dates))
    dates = dates[dates >= start_date]
    if end_date is not None:
        dates = dates[dates <= end_date]
    if dates.empty:
        return []

    period_frequency = normalize_period_frequency(frequency)
    grouped = dates.groupby(dates.dt.to_period(period_frequency)).max()
    rebalance_dates = list(grouped.sort_values())
    if len(rebalance_dates) > max_periods + 1:
        rebalance_dates = rebalance_dates[-(max_periods + 1) :]
    return [pd.Timestamp(date) for date in rebalance_dates]


def normalize_period_frequency(frequency: str) -> str:
    """Map readable rebalance aliases to pandas Period frequencies."""
    aliases = {
        "ME": "M",
        "MONTH_END": "M",
        "QE": "Q",
        "QUARTER_END": "Q",
        "YE": "Y",
        "YEAR_END": "Y",
    }
    return aliases.get(frequency.upper(), frequency)


def build_historical_screen(
    frames: dict[str, pd.DataFrame],
    as_of_date: pd.Timestamp,
    settings: dict[str, Any],
) -> pd.DataFrame:
    """Build a point-in-time screen by slicing histories to a date."""
    rows: list[dict[str, Any]] = []
    for frame in frames.values():
        history = frame[frame["date"] <= as_of_date].copy()
        if history.empty:
            continue
        try:
            rows.append(screen_symbol_frame(frame=history, settings=settings))
        except ValueError:
            continue

    screen = pd.DataFrame(rows)
    if screen.empty:
        return screen
    screen = screen.sort_values(
        by=["recommendation_rank", "total_score", "momentum_score", "trend_score"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)
    screen["rank"] = range(1, len(screen) + 1)
    return screen


def calculate_period_return(
    selected: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    equity: float,
    transaction_cost_pct: float,
) -> tuple[float, list[dict[str, Any]]]:
    """Calculate one holding-period return and trade rows."""
    if selected.empty:
        return 0.0, []

    weighted_return = 0.0
    trades: list[dict[str, Any]] = []
    for row in selected.itertuples(index=False):
        frame = frames[row.symbol]
        entry_price = price_on_or_before(frame=frame, date=entry_date)
        exit_price = price_on_or_before(frame=frame, date=exit_date)
        if entry_price is None or exit_price is None or entry_price <= 0:
            continue

        raw_return = (exit_price / entry_price) - 1
        net_return = raw_return - (2 * transaction_cost_pct)
        weight = float(row.portfolio_weight)
        weighted_return += weight * net_return
        trades.append(
            {
                "entry_date": entry_date,
                "exit_date": exit_date,
                "symbol": row.symbol,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return": raw_return,
                "net_return": net_return,
                "portfolio_weight": weight,
                "position_value": float(row.position_value),
                "estimated_pnl": equity * weight * net_return,
            }
        )

    return weighted_return, trades


def price_on_or_before(frame: pd.DataFrame, date: pd.Timestamp) -> float | None:
    """Return adjusted close on or before a date."""
    available = frame[frame["date"] <= date]
    if available.empty:
        return None
    return float(available["adj_close"].iloc[-1])


def with_backtest_portfolio_value(settings: dict[str, Any], portfolio_value: float) -> dict[str, Any]:
    """Copy settings and replace portfolio value for a period."""
    copied = settings.copy()
    copied["risk"] = settings["risk"].copy()
    copied["risk"]["portfolio_value"] = portfolio_value
    return copied


def save_backtest_outputs(
    equity_curve: pd.DataFrame,
    trade_log: pd.DataFrame,
    index_name: str,
    settings: dict[str, Any],
) -> tuple[Path, Path]:
    """Save equity curve and trade log parquet/CSV files."""
    output_dir = get_backtest_dir(index_name=index_name, settings=settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_slug = index_name.lower()
    equity_path = output_dir / f"{index_slug}_equity_curve.parquet"
    trades_path = output_dir / f"{index_slug}_trade_log.parquet"
    equity_csv_path = output_dir / f"{index_slug}_equity_curve.csv"
    trades_csv_path = output_dir / f"{index_slug}_trade_log.csv"

    equity_curve.to_parquet(equity_path, index=False)
    equity_curve.to_csv(equity_csv_path, index=False)
    trade_log.to_parquet(trades_path, index=False)
    trade_log.to_csv(trades_csv_path, index=False)
    return equity_path, trades_path


def get_indicator_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return indicator input directory."""
    return (
        resolve_project_path(settings["storage"]["processed_data_dir"])
        / settings["indicators"]["output_subdir"]
        / index_name.lower()
    )


def get_backtest_dir(index_name: str, settings: dict[str, Any]) -> Path:
    """Return backtest output directory."""
    return (
        resolve_project_path(settings["storage"]["signals_data_dir"])
        / settings["backtest"]["output_subdir"]
        / index_name.lower()
    )
