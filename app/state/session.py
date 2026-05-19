"""
Session state management for the dashboard.
"""

import streamlit as st
from typing import Any, Dict

class SessionState:
    """Manage session state for the dashboard."""

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get a value from session state."""
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any) -> None:
        """Set a value in session state."""
        st.session_state[key] = value

    @staticmethod
    def initialize_defaults():
        """Initialize default session state values."""
        defaults = {
            'selected_index': 'NIFTY50',
            'previous_selected_index': 'NIFTY50',
            'selected_symbol': 'RELIANCE',
            'selected_sector': 'All',
            'selected_signal_type': 'All',
            'chart_timeframe': '1M',
            'last_refresh': None
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def clear_cache():
        """Clear all cached data."""
        st.cache_data.clear()
        st.success("Cache cleared successfully!")

# Initialize session state on import
SessionState.initialize_defaults()