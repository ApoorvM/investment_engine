"""Tests for the dashboard pipeline monitoring service."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.pipeline import PipelineService


class PipelineServiceTests(unittest.TestCase):
    """Validate pipeline monitoring behavior."""

    def test_get_pipeline_status_resolves_nested_data_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            # Create the expected data layout for pipeline components.
            (root / "universe").mkdir(parents=True)
            (root / "universe" / "nifty50_constituents_latest.parquet").write_text("test")
            (root / "raw" / "ohlcv" / "nifty50").mkdir(parents=True)
            (root / "raw" / "ohlcv" / "nifty50" / "dummy.csv").write_text("test")
            (root / "processed" / "ohlcv" / "nifty50").mkdir(parents=True)
            (root / "processed" / "ohlcv" / "nifty50" / "dummy.csv").write_text("test")
            (root / "processed" / "indicators" / "nifty50").mkdir(parents=True)
            (root / "processed" / "indicators" / "nifty50" / "dummy.csv").write_text("test")
            (root / "signals" / "screens" / "nifty50").mkdir(parents=True)
            (root / "signals" / "screens" / "nifty50" / "dummy.csv").write_text("test")
            (root / "signals" / "risk" / "nifty50").mkdir(parents=True)
            (root / "signals" / "risk" / "nifty50" / "dummy.csv").write_text("test")
            (root / "signals" / "final" / "nifty50").mkdir(parents=True)
            (root / "signals" / "final" / "nifty50" / "dummy.csv").write_text("test")
            (root / "signals" / "backtest" / "nifty50").mkdir(parents=True)
            (root / "signals" / "backtest" / "nifty50" / "dummy.csv").write_text("test")

            with patch("app.services.pipeline.get_data_path", return_value=root):
                status = PipelineService.get_pipeline_status()
                freshness = PipelineService.get_data_freshness()

            self.assertTrue(status["status"]["universe"])
            self.assertTrue(status["status"]["ohlcv"])
            self.assertTrue(status["status"]["screens"])
            self.assertTrue(status["status"]["signals"])
            self.assertIsNotNone(status["last_updates"]["ohlcv"])
            self.assertIsNotNone(status["last_updates"]["screens"])
            self.assertIsNotNone(status["last_updates"]["signals"])
            self.assertEqual(freshness["universe"], "fresh")


if __name__ == "__main__":
    unittest.main()
