"""Tests for final signal generation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from strategies.signals import build_signal_frame, classify_signal, generate_signals
from utils.config import load_settings


class SignalTests(unittest.TestCase):
    """Validate Phase 9 final signal behavior."""

    def test_classify_signal_buy_candidate_requires_risk_selection(self) -> None:
        settings = load_settings()
        row = pd.Series(
            {
                "risk_status": "selected",
                "total_score": 90,
                "screen_result": "watchlist",
            }
        )

        self.assertEqual(classify_signal(row=row, settings=settings), "buy_candidate")

    def test_build_signal_frame_merges_screen_and_risk(self) -> None:
        settings = load_settings()
        screen = self._sample_screen()
        risk = self._sample_risk()

        signals = build_signal_frame(screen=screen, risk=risk, settings=settings)

        self.assertEqual(signals.loc[0, "symbol"], "AAA")
        self.assertEqual(signals.loc[0, "signal"], "buy_candidate")
        self.assertEqual(signals.loc[1, "signal"], "watchlist")

    def test_generate_signals_writes_outputs(self) -> None:
        settings = load_settings()
        screen = self._sample_screen()
        risk = self._sample_risk()

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["signals_data_dir"] = "tmp_signals"
            base_dir = Path(tmp_dir) / "tmp_signals"
            screen_dir = base_dir / settings["screening"]["output_subdir"] / "nifty50"
            risk_dir = base_dir / settings["risk"]["output_subdir"] / "nifty50"
            screen_dir.mkdir(parents=True)
            risk_dir.mkdir(parents=True)
            screen.to_parquet(screen_dir / "nifty50_screen_latest.parquet", index=False)
            risk.to_parquet(risk_dir / "nifty50_risk_latest.parquet", index=False)

            with patch(
                "strategies.signals.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                result = generate_signals(index_name="NIFTY50", settings=settings)

            self.assertEqual(result.total_symbols, 2)
            self.assertEqual(result.buy_candidates, 1)
            self.assertTrue(result.output_parquet_path.exists())
            self.assertTrue(result.output_csv_path.exists())

    @staticmethod
    def _sample_screen() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "as_of_date": pd.to_datetime(["2026-05-08", "2026-05-08"]),
                "symbol": ["AAA", "BBB"],
                "price": [100.0, 200.0],
                "total_score": [90.0, 75.0],
                "momentum_score": [90, 70],
                "trend_score": [100, 80],
                "volatility_score": [80, 80],
                "liquidity_score": [100, 100],
                "screen_result": ["watchlist", "watchlist"],
                "rank": [1, 2],
                "return_1m": [0.02, 0.01],
                "return_3m": [0.08, 0.04],
                "return_6m": [0.15, 0.06],
                "rsi_14": [60.0, 55.0],
                "atr_pct": [0.02, 0.03],
                "daily_volatility_63d": [0.01, 0.02],
                "avg_turnover_20": [1_000_000_000.0, 900_000_000.0],
            }
        )

    @staticmethod
    def _sample_risk() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "symbol": ["AAA"],
                "portfolio_rank": [1],
                "stop_loss_price": [95.0],
                "stop_loss_pct": [0.05],
                "position_shares": [100],
                "position_value": [10_000.0],
                "portfolio_weight": [0.01],
                "capital_at_risk": [500.0],
                "risk_status": ["selected"],
                "risk_reason": ["Selected within portfolio caps"],
            }
        )


if __name__ == "__main__":
    unittest.main()
