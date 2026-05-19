"""
Configuration utilities for the Investment Engine.
"""

import json
import toml
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path(__file__).parent.parent / "config" / "settings.toml"

def load_config() -> Dict[str, Any]:
    """Load configuration from TOML file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return toml.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return get_default_config()
    else:
        return get_default_config()

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to TOML file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, 'w') as f:
            toml.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_default_config() -> Dict[str, Any]:
    """Get default configuration."""
    return {
        'risk_management': {
            'max_risk_per_trade': 2.0,
            'max_portfolio_risk': 10.0,
            'max_positions': 20,
            'rebalance_threshold': 5.0
        },
        'signals': {
            'min_confidence': 70,
            'lookback_period': 100,
            'momentum_threshold': 0.1,
            'volatility_filter': 0.3
        },
        'system': {
            'update_frequency': 'Daily',
            'cache_timeout': 6,
            'max_retries': 3,
            'timeout': 30
        },
        'notifications': {
            'signals': True,
            'errors': True
        }
    }