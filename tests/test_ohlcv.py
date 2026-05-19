"""Tests for OHLCV normalization and storage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ingestion.ohlcv import (
    determine_download_start_date,
    filter_ohlcv_from_start,
    merge_ohlcv,
    normalize_ohlcv,
    save_ohlcv,
)
from utils.config import load_settings


class OhlcvTests(unittest.TestCase):
    """Validate Phase 3 OHLCV behavior without live network calls."""

    def test_normalize_ohlcv_creates_stable_schema(self) -> None:
        raw_frame = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [99.0, 100.0],
                "Close": [104.0, 103.0],
                "Adj Close": [103.5, 102.5],
                "Volume": [1000, 1500],
            },
            index=pd.to_datetime(["2026-05-07", "2026-05-08"]),
        )
        raw_frame.index.name = "Date"

        normalized = normalize_ohlcv(
            frame=raw_frame,
            symbol="INFY",
            yfinance_symbol="INFY.NS",
            provider="yfinance",
        )

        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized.loc[0, "symbol"], "INFY")
        self.assertEqual(normalized.loc[0, "yfinance_symbol"], "INFY.NS")
        self.assertIn("adj_close", normalized.columns)
        self.assertIn("downloaded_at_utc", normalized.columns)

    def test_save_ohlcv_writes_symbol_parquet(self) -> None:
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
                "downloaded_at_utc": [pd.Timestamp("2026-05-10T00:00:00Z")],
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["raw_data_dir"] = "tmp_raw"
            with patch(
                "ingestion.ohlcv.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                output_path = save_ohlcv(
                    frame=frame,
                    symbol="INFY",
                    index_name="NIFTY50",
                    settings=settings,
                )

            self.assertTrue(output_path.exists())
            saved = pd.read_parquet(output_path)
            self.assertEqual(saved.loc[0, "symbol"], "INFY")

    def test_determine_download_start_date_uses_overlap_for_incremental(self) -> None:
        existing = pd.DataFrame({"date": pd.to_datetime(["2026-05-01", "2026-05-10"])})

        start_date = determine_download_start_date(
            existing=existing,
            configured_start_date="2020-01-01",
            incremental=True,
            overlap_days=5,
        )

        self.assertEqual(start_date, "2026-05-05")

    def test_determine_download_start_date_respects_full_refresh(self) -> None:
        existing = pd.DataFrame({"date": pd.to_datetime(["2026-05-10"])})

        start_date = determine_download_start_date(
            existing=existing,
            configured_start_date="2020-01-01",
            incremental=False,
            overlap_days=5,
        )

        self.assertEqual(start_date, "2020-01-01")

    def test_merge_ohlcv_keeps_latest_duplicate_date(self) -> None:
        existing = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-05-07", "2026-05-08"]),
                "close": [100.0, 101.0],
                "downloaded_at_utc": [
                    pd.Timestamp("2026-05-09T00:00:00Z"),
                    pd.Timestamp("2026-05-09T00:00:00Z"),
                ],
            }
        )
        new_data = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-05-08", "2026-05-09"]),
                "close": [102.0, 103.0],
                "downloaded_at_utc": [
                    pd.Timestamp("2026-05-10T00:00:00Z"),
                    pd.Timestamp("2026-05-10T00:00:00Z"),
                ],
            }
        )

        merged = merge_ohlcv(existing=existing, new_data=new_data)

        self.assertEqual(len(merged), 3)
        self.assertEqual(float(merged.loc[merged["date"] == pd.Timestamp("2026-05-08"), "close"].iloc[0]), 102.0)

    def test_filter_ohlcv_from_start_removes_provider_backfill(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-01", "2026-05-05"]),
                "close": [100.0, 200.0],
            }
        )

        filtered = filter_ohlcv_from_start(frame=frame, start_date="2026-05-03")

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.loc[0, "date"], pd.Timestamp("2026-05-05"))


if __name__ == "__main__":
    unittest.main()
