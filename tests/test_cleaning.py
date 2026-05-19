"""Tests for OHLCV cleaning and processed storage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ingestion.cleaning import clean_ohlcv_frame, save_processed_ohlcv
from utils.config import load_settings


class CleaningTests(unittest.TestCase):
    """Validate Phase 5 cleaning behavior."""

    def test_clean_ohlcv_frame_adds_adjusted_columns(self) -> None:
        settings = load_settings()
        settings["processing"]["min_rows"] = 2
        raw = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-05-08", "2026-05-07", "2026-05-08"]),
                "open": [100.0, 90.0, 102.0],
                "high": [110.0, 95.0, 112.0],
                "low": [99.0, 89.0, 101.0],
                "close": [108.0, 94.0, 110.0],
                "volume": [1000, 900, 1200],
                "adj_close": [54.0, 47.0, 55.0],
                "symbol": ["INFY", "INFY", "INFY"],
                "yfinance_symbol": ["INFY.NS", "INFY.NS", "INFY.NS"],
                "provider": ["yfinance", "yfinance", "yfinance"],
            }
        )

        cleaned, warnings = clean_ohlcv_frame(raw, settings=settings)

        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(warnings), 1)
        self.assertIn("adj_open", cleaned.columns)
        self.assertEqual(float(cleaned.loc[1, "adj_close"]), 55.0)
        self.assertEqual(float(cleaned.loc[1, "adj_open"]), 51.0)

    def test_clean_ohlcv_frame_rejects_invalid_prices(self) -> None:
        settings = load_settings()
        settings["processing"]["min_rows"] = 1
        raw = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-05-07"]),
                "open": [100.0],
                "high": [99.0],
                "low": [98.0],
                "close": [101.0],
                "volume": [1000],
                "symbol": ["INFY"],
                "yfinance_symbol": ["INFY.NS"],
                "provider": ["yfinance"],
            }
        )

        with self.assertRaises(ValueError):
            clean_ohlcv_frame(raw, settings=settings)

    def test_save_processed_ohlcv_writes_symbol_parquet(self) -> None:
        settings = load_settings()
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-05-07"]),
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [104.0],
                "volume": [1000],
                "symbol": ["INFY"],
                "yfinance_symbol": ["INFY.NS"],
                "provider": ["yfinance"],
                "adj_open": [100.0],
                "adj_high": [105.0],
                "adj_low": [99.0],
                "adj_close": [104.0],
                "processed_at_utc": [pd.Timestamp("2026-05-10T00:00:00Z")],
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["processed_data_dir"] = "tmp_processed"
            with patch(
                "ingestion.cleaning.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                output_path = save_processed_ohlcv(
                    frame=frame,
                    symbol="INFY",
                    index_name="NIFTY50",
                    settings=settings,
                )

            self.assertTrue(output_path.exists())
            saved = pd.read_parquet(output_path)
            self.assertEqual(saved.loc[0, "symbol"], "INFY")


if __name__ == "__main__":
    unittest.main()
