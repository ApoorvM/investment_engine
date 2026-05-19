"""
Pipeline monitoring service.
"""

import os
import subprocess
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
from app.components.loaders import get_data_path

class PipelineService:
    """Service for monitoring pipeline health."""

    @staticmethod
    def get_pipeline_status(index_name: str = "nifty50") -> Dict:
        """Get overall pipeline status."""
        data_dir = get_data_path()

        component_paths = {
            'universe': data_dir / "universe" / f"{index_name}_constituents_latest.parquet",
            'ohlcv': data_dir / "raw" / "ohlcv" / index_name,
            'processed': data_dir / "processed" / "ohlcv" / index_name,
            'indicators': data_dir / "processed" / "indicators" / index_name,
            'screens': data_dir / "signals" / "screens" / index_name,
            'risk': data_dir / "signals" / "risk" / index_name,
            'signals': data_dir / "signals" / "final" / index_name,
            'backtest': data_dir / "signals" / "backtest" / index_name
        }

        checks = {component: path.exists() for component, path in component_paths.items()}

        last_updates = {}
        for component, path in component_paths.items():
            if checks[component]:
                try:
                    if path.is_file():
                        mtime = datetime.fromtimestamp(path.stat().st_mtime)
                    else:
                        files = list(path.rglob("*.parquet")) + list(path.rglob("*.csv"))
                        if files:
                            mtime = max(datetime.fromtimestamp(f.stat().st_mtime) for f in files)
                        else:
                            mtime = None
                    last_updates[component] = mtime
                except Exception:
                    last_updates[component] = None
            else:
                last_updates[component] = None

        return {
            'status': checks,
            'last_updates': last_updates,
            'overall_health': 'healthy' if all(checks.values()) else 'issues'
        }

    @staticmethod
    def get_data_freshness(index_name: str = "nifty50") -> Dict:
        """Check data freshness."""
        status = PipelineService.get_pipeline_status(index_name=index_name)
        now = datetime.now()

        freshness = {}
        for component, last_update in status['last_updates'].items():
            if last_update:
                hours_old = (now - last_update).total_seconds() / 3600
                if hours_old < 24:
                    freshness[component] = 'fresh'
                elif hours_old < 72:
                    freshness[component] = 'stale'
                else:
                    freshness[component] = 'old'
            else:
                freshness[component] = 'missing'

        return freshness

    @staticmethod
    def run_daily_update(index_name: str = "nifty50") -> Dict[str, str]:
        """Run the full pipeline for the selected index."""
        repo_root = Path(__file__).resolve().parents[2]
        main_script = repo_root / "main.py"
        
        env = os.environ.copy()
        env['PYTHONPATH'] = str(repo_root)
        
        command = [sys.executable, str(main_script), "daily-update", "--index", index_name.upper()]
        result = subprocess.run(command, capture_output=True, text=True, cwd=repo_root, env=env)

        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }

    @staticmethod
    def run_backtest(index_name: str = "nifty50", start_date: str = None, end_date: str = None) -> Dict[str, str]:
        """Run a backtest for the selected index."""
        repo_root = Path(__file__).resolve().parents[2]
        main_script = repo_root / "main.py"
        
        env = os.environ.copy()
        env['PYTHONPATH'] = str(repo_root)
        
        command = [sys.executable, str(main_script), "backtest", "--index", index_name.upper()]
        if start_date:
            command.extend(["--start", start_date])
        if end_date:
            command.extend(["--end", end_date])
            
        result = subprocess.run(command, capture_output=True, text=True, cwd=repo_root, env=env)

        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }
