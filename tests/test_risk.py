"""Tests for portfolio risk management."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from risk.portfolio import add_position_sizing, apply_risk_rules, run_portfolio_risk
from utils.config import load_settings


class RiskTests(unittest.TestCase):
    """Validate Phase 8 risk behavior."""

    def test_add_position_sizing_caps_position_value(self) -> None:
        settings = load_settings()
        candidates = self._sample_screen().head(1)

        sized = add_position_sizing(candidates=candidates, config=settings["risk"])

        max_position_value = settings["risk"]["portfolio_value"] * settings["risk"]["max_position_pct"]
        self.assertLessEqual(float(sized.loc[0, "position_value"]), max_position_value)
        self.assertGreater(int(sized.loc[0, "position_shares"]), 0)

    def test_apply_risk_rules_selects_max_positions(self) -> None:
        settings = load_settings()
        settings["risk"]["max_positions"] = 2
        screen = self._sample_screen(rows=4)

        risk_frame = apply_risk_rules(screen=screen, settings=settings)

        self.assertEqual(len(risk_frame), 2)
        self.assertEqual(list(risk_frame["portfolio_rank"]), [1, 2])
        self.assertTrue((risk_frame["risk_status"] == "selected").all())

    def test_run_portfolio_risk_writes_outputs(self) -> None:
        settings = load_settings()
        screen = self._sample_screen(rows=2)

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings["storage"]["signals_data_dir"] = "tmp_signals"
            screen_dir = (
                Path(tmp_dir)
                / "tmp_signals"
                / settings["screening"]["output_subdir"]
                / "nifty50"
            )
            screen_dir.mkdir(parents=True)
            screen.to_parquet(screen_dir / "nifty50_screen_latest.parquet", index=False)

            with patch(
                "risk.portfolio.resolve_project_path",
                side_effect=lambda relative_path: Path(tmp_dir) / relative_path,
            ):
                result = run_portfolio_risk(index_name="NIFTY50", settings=settings)

            self.assertEqual(result.input_symbols, 2)
            self.assertTrue(result.output_parquet_path.exists())
            self.assertTrue(result.output_csv_path.exists())

    @staticmethod
    def _sample_screen(rows: int = 3) -> pd.DataFrame:
        symbols = ["AAA", "BBB", "CCC", "DDD"][:rows]
        return pd.DataFrame(
            {
                "as_of_date": pd.to_datetime(["2026-05-08"] * rows),
                "symbol": symbols,
                "screen_result": ["watchlist"] * rows,
                "total_score": [95, 90, 85, 80][:rows],
                "price": [100.0, 200.0, 150.0, 120.0][:rows],
                "atr_pct": [0.02, 0.03, 0.04, 0.05][:rows],
                "avg_turnover_20": [1_000_000_000.0] * rows,
                "rank": list(range(1, rows + 1)),
            }
        )


if __name__ == "__main__":
    unittest.main()
