"""Tests for performance analytics."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from reports.performance import (
    analyze_backtest,
    calculate_drawdown,
    calculate_performance_metrics,
    calculate_sharpe_ratio,
)
from utils.config import load_settings


class PerformanceTests(unittest.TestCase):
    """Validate Phase 11 performance analytics."""

    def test_calculate_drawdown(self) -> None:
        drawdown = calculate_drawdown(pd.Series([100.0, 120.0, 90.0, 110.0]))

        self.assertEqual(round(float(drawdown.min()), 4), -0.25)

    def test_calculate_sharpe_ratio(self) -> None:
        sharpe = calculate_sharpe_ratio(
            returns=pd.Series([0.01, 0.02, -0.01, 0.03]),
            risk_free_rate=0.0,
            periods_per_year=12,
        )

        self.assertTrue(pd.notna(sharpe))

    def test_calculate_performance_metrics(self) -> None:
        settings = load_settings()
        equity = self._sample_equity()
        trades = self._sample_trades()

        metrics = calculate_performance_metrics(
            equity_curve=equity,
            trade_log=trades,
            settings=settings,
        )

        self.assertEqual(int(metrics.loc[0, "trades"]), 2)
        self.assertGreater(float(metrics.loc[0, "total_return"]), 0)

    def test_analyze_backtest_writes_outputs(self) -> None:
        settings = load_settings()

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["signals_data_dir"] = "tmp_signals"
            output_dir = Path(tmp_dir) / "tmp_signals" / settings["backtest"]["output_subdir"] / "nifty50"
            output_dir.mkdir(parents=True)
            self._sample_equity().to_parquet(output_dir / "nifty50_equity_curve.parquet", index=False)
            self._sample_trades().to_parquet(output_dir / "nifty50_trade_log.parquet", index=False)

            with patch(
                "reports.performance.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                result = analyze_backtest(index_name="NIFTY50", settings=settings)

            self.assertTrue(result.metrics_path.exists())
            self.assertTrue(result.metrics_csv_path.exists())
            self.assertTrue(result.markdown_report_path.exists())

    @staticmethod
    def _sample_equity() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-31", "2026-02-28", "2026-03-31"]),
                "equity": [1000.0, 1050.0, 1100.0],
                "period_return": [0.0, 0.05, 0.047619],
                "positions": [0, 2, 2],
                "cash_weight": [1.0, 0.2, 0.2],
            }
        )

    @staticmethod
    def _sample_trades() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "symbol": ["AAA", "BBB"],
                "entry_date": pd.to_datetime(["2026-01-31", "2026-01-31"]),
                "exit_date": pd.to_datetime(["2026-02-28", "2026-02-28"]),
                "net_return": [0.10, -0.02],
                "estimated_pnl": [100.0, -20.0],
            }
        )


if __name__ == "__main__":
    unittest.main()
