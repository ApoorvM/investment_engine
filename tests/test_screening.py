"""Tests for the basic screening engine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from strategies.screening import (
    calculate_lookback_return,
    classify_screen_result,
    run_basic_screen,
    screen_symbol_frame,
    score_trend,
)
from utils.config import load_settings


class ScreeningTests(unittest.TestCase):
    """Validate Phase 7 screening behavior."""

    def test_calculate_lookback_return(self) -> None:
        frame = pd.DataFrame({"adj_close": [100.0, 105.0, 110.0]})

        result = calculate_lookback_return(frame=frame, price_column="adj_close", lookback=2)

        self.assertEqual(result, 0.10)

    def test_score_trend_rewards_alignment(self) -> None:
        score = score_trend(close=120.0, sma_50=110.0, sma_200=100.0, macd_histogram=1.0)

        self.assertEqual(score, 100)

    def test_classify_screen_result_requires_history(self) -> None:
        result = classify_screen_result(
            total_score=90,
            trend_score=100,
            liquidity_score=100,
            threshold=65,
            rows_available=20,
            min_history_rows=126,
        )

        self.assertEqual(result, "insufficient_history")

    def test_screen_symbol_frame_returns_watchlist_for_strong_trend(self) -> None:
        settings = load_settings()
        frame = self._sample_indicator_frame(rows=220, symbol="INFY")

        row = screen_symbol_frame(frame=frame, settings=settings)

        self.assertEqual(row["symbol"], "INFY")
        self.assertEqual(row["screen_result"], "watchlist")
        self.assertGreaterEqual(row["total_score"], settings["screening"]["watchlist_score_threshold"])

    def test_run_basic_screen_writes_outputs(self) -> None:
        settings = load_settings()
        frame = self._sample_indicator_frame(rows=220, symbol="INFY")

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
            frame.to_parquet(indicator_dir / "infy.parquet", index=False)

            with patch(
                "strategies.screening.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                result = run_basic_screen(index_name="NIFTY50", settings=settings)

            self.assertEqual(result.screened_symbols, 1)
            self.assertTrue(result.output_parquet_path.exists())
            self.assertTrue(result.output_csv_path.exists())

    @staticmethod
    def _sample_indicator_frame(rows: int, symbol: str) -> pd.DataFrame:
        dates = pd.date_range("2025-01-01", periods=rows, freq="B")
        price = pd.Series([100 + index * 0.5 for index in range(rows)], dtype="float64")
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
