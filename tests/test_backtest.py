"""Tests for the backtesting engine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backtest.engine import (
    build_rebalance_dates,
    calculate_period_return,
    price_on_or_before,
    run_backtest,
)
from utils.config import load_settings


class BacktestTests(unittest.TestCase):
    """Validate Phase 10 backtest behavior."""

    def test_price_on_or_before(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-01", "2026-01-03"]),
                "adj_close": [100.0, 110.0],
            }
        )

        self.assertEqual(price_on_or_before(frame, pd.Timestamp("2026-01-02")), 100.0)

    def test_build_rebalance_dates_month_end(self) -> None:
        frames = {
            "AAA": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2026-01-02", "2026-01-30", "2026-02-27"]),
                }
            )
        }

        dates = build_rebalance_dates(
            frames=frames,
            start_date=pd.Timestamp("2026-01-01"),
            end_date=None,
            frequency="ME",
            max_periods=10,
        )

        self.assertEqual(dates, [pd.Timestamp("2026-01-30"), pd.Timestamp("2026-02-27")])

    def test_calculate_period_return_uses_weights(self) -> None:
        selected = pd.DataFrame(
            {
                "symbol": ["AAA"],
                "portfolio_weight": [0.5],
                "position_value": [500.0],
            }
        )
        frames = {
            "AAA": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2026-01-31", "2026-02-28"]),
                    "adj_close": [100.0, 110.0],
                }
            )
        }

        period_return, trades = calculate_period_return(
            selected=selected,
            frames=frames,
            entry_date=pd.Timestamp("2026-01-31"),
            exit_date=pd.Timestamp("2026-02-28"),
            equity=1000.0,
            transaction_cost_pct=0.0,
        )

        self.assertEqual(round(period_return, 4), 0.05)
        self.assertEqual(len(trades), 1)

    def test_run_backtest_writes_outputs(self) -> None:
        settings = load_settings()
        settings["backtest"]["start_date"] = "2025-01-01"
        settings["backtest"]["max_rebalance_periods"] = 3
        settings["processing"]["min_rows"] = 30
        frame = self._sample_indicator_frame("AAA", rows=260)

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["processed_data_dir"] = "tmp_processed"
            settings["storage"]["signals_data_dir"] = "tmp_signals"
            indicator_dir = (
                Path(tmp_dir)
                / "tmp_processed"
                / settings["indicators"]["output_subdir"]
                / "nifty50"
            )
            indicator_dir.mkdir(parents=True)
            frame.to_parquet(indicator_dir / "aaa.parquet", index=False)

            with patch(
                "backtest.engine.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                result = run_backtest(index_name="NIFTY50", settings=settings)

            self.assertGreaterEqual(result.periods, 1)
            self.assertTrue(result.equity_curve_path.exists())
            self.assertTrue(result.trades_path.exists())

    @staticmethod
    def _sample_indicator_frame(symbol: str, rows: int) -> pd.DataFrame:
        dates = pd.date_range("2025-01-01", periods=rows, freq="B")
        price = pd.Series([100 + index for index in range(rows)], dtype="float64")
        return pd.DataFrame(
            {
                "date": dates,
                "symbol": [symbol] * rows,
                "adj_close": price,
                "sma_50": price - 5,
                "sma_200": price - 10,
                "rsi_14": [60.0] * rows,
                "macd_histogram": [1.0] * rows,
                "atr_14": [2.0] * rows,
                "volume": [2_000_000] * rows,
                "volume_sma_20": [2_000_000] * rows,
                "volume_ratio_20": [1.0] * rows,
                "daily_return": price.pct_change().fillna(0.0),
            }
        )


if __name__ == "__main__":
    unittest.main()
