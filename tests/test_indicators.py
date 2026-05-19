"""Tests for technical indicator calculations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from indicators.technical import (
    add_technical_indicators,
    calculate_atr,
    calculate_macd,
    calculate_rsi,
    save_indicator_frame,
)
from utils.config import load_settings


class IndicatorTests(unittest.TestCase):
    """Validate Phase 6 indicator behavior."""

    def test_add_technical_indicators_adds_expected_columns(self) -> None:
        settings = load_settings()
        frame = self._sample_processed_frame(rows=260)

        enriched = add_technical_indicators(frame=frame, settings=settings)

        expected_columns = {
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_12",
            "ema_26",
            "rsi_14",
            "macd",
            "macd_signal",
            "macd_histogram",
            "atr_14",
            "volume_sma_20",
            "volume_ratio_20",
            "daily_return",
        }
        self.assertTrue(expected_columns.issubset(enriched.columns))
        self.assertEqual(len(enriched), 260)
        self.assertFalse(enriched["sma_200"].tail(1).isna().iloc[0])

    def test_rsi_is_bounded(self) -> None:
        price = pd.Series([100, 101, 102, 101, 103, 104, 102, 105, 106, 107, 106, 108, 109, 110, 111])

        rsi = calculate_rsi(price=price, window=14)

        valid = rsi.dropna()
        self.assertTrue(((valid >= 0) & (valid <= 100)).all())

    def test_macd_shapes_match_input(self) -> None:
        price = pd.Series(range(1, 80), dtype="float64")

        macd, signal, histogram = calculate_macd(price=price, fast=12, slow=26, signal=9)

        self.assertEqual(len(macd), len(price))
        self.assertEqual(len(signal), len(price))
        self.assertEqual(len(histogram), len(price))

    def test_atr_is_non_negative(self) -> None:
        high = pd.Series([11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25], dtype="float64")
        low = pd.Series([9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23], dtype="float64")
        close = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24], dtype="float64")

        atr = calculate_atr(high=high, low=low, close=close, window=14)

        self.assertTrue((atr.dropna() >= 0).all())

    def test_save_indicator_frame_writes_symbol_parquet(self) -> None:
        settings = load_settings()
        frame = self._sample_processed_frame(rows=40)

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["processed_data_dir"] = "tmp_processed"
            with patch(
                "indicators.technical.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                output_path = save_indicator_frame(
                    frame=frame,
                    symbol="INFY",
                    index_name="NIFTY50",
                    settings=settings,
                )

            self.assertTrue(output_path.exists())
            saved = pd.read_parquet(output_path)
            self.assertEqual(saved.loc[0, "symbol"], "INFY")

    @staticmethod
    def _sample_processed_frame(rows: int) -> pd.DataFrame:
        dates = pd.date_range("2025-01-01", periods=rows, freq="B")
        close = pd.Series(range(100, 100 + rows), dtype="float64")
        return pd.DataFrame(
            {
                "date": dates,
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": [1000 + index for index in range(rows)],
                "adj_open": close - 1,
                "adj_high": close + 2,
                "adj_low": close - 2,
                "adj_close": close,
                "symbol": ["INFY"] * rows,
                "yfinance_symbol": ["INFY.NS"] * rows,
                "provider": ["yfinance"] * rows,
            }
        )


if __name__ == "__main__":
    unittest.main()
