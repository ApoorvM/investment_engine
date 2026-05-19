"""Tests for index constituent normalization and storage."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from universe.constituents import normalize_constituents, save_constituent_snapshot
from utils.config import load_settings


class UniverseConstituentTests(unittest.TestCase):
    """Validate Phase 2 universe behavior without live network calls."""

    def test_normalize_constituents_adds_project_columns(self) -> None:
        raw_frame = pd.DataFrame(
            {
                "Company Name": ["Infosys Ltd.", "Reliance Industries Ltd."],
                "Industry": ["Information Technology", "Oil Gas & Consumable Fuels"],
                "Symbol": [" infy ", "RELIANCE"],
                "Series": ["EQ", "EQ"],
                "ISIN Code": ["INE009A01021", "INE002A01018"],
            }
        )

        normalized = normalize_constituents(
            raw_frame=raw_frame,
            index_name="CUSTOM",
            display_name="Custom Index",
            fetched_at=datetime(2026, 5, 10, tzinfo=UTC),
            snapshot_date=date(2026, 5, 10),
            source_url="https://example.com/index.csv",
        )

        self.assertEqual(list(normalized["symbol"]), ["INFY", "RELIANCE"])
        self.assertEqual(list(normalized["yfinance_symbol"]), ["INFY.NS", "RELIANCE.NS"])
        self.assertIn("snapshot_date", normalized.columns)
        self.assertIn("source_url", normalized.columns)

    def test_save_constituent_snapshot_writes_dated_and_latest_parquet(self) -> None:
        settings = load_settings()
        constituents = pd.DataFrame(
            {
                "company_name": ["Infosys Ltd."],
                "industry": ["Information Technology"],
                "symbol": ["INFY"],
                "series": ["EQ"],
                "isin": ["INE009A01021"],
                "nse_symbol": ["INFY"],
                "yfinance_symbol": ["INFY.NS"],
                "index_name": ["CUSTOM"],
                "index_display_name": ["Custom Index"],
                "snapshot_date": [pd.Timestamp("2026-05-10")],
                "fetched_at_utc": [pd.Timestamp("2026-05-10T00:00:00Z")],
                "source_url": ["https://example.com/index.csv"],
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["universe_data_dir"] = "tmp_universe"
            with patch(
                "universe.constituents.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                snapshot = save_constituent_snapshot(
                    constituents=constituents,
                    index_name="CUSTOM",
                    snapshot_date=date(2026, 5, 10),
                    settings=settings,
                    source_url="https://example.com/index.csv",
                )

            self.assertTrue(snapshot.snapshot_path.exists())
            self.assertTrue(snapshot.latest_path.exists())
            saved = pd.read_parquet(snapshot.latest_path)
            self.assertEqual(saved.loc[0, "symbol"], "INFY")


if __name__ == "__main__":
    unittest.main()
