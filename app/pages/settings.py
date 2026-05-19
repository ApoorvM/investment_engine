"""
Settings page for the Investment Engine.
"""

import json
import streamlit as st
import pandas as pd
from pathlib import Path
from app.utils.config import load_config, save_config
from app.state.session import SessionState

def render_settings():
    """Render the settings page."""
    st.markdown('<div class="main-header">⚙️ Settings</div>', unsafe_allow_html=True)
    st.markdown("Configure your Investment Engine preferences and parameters.")

    # Load current config
    try:
        config = load_config()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        config = {}

    # Settings tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Trading Parameters", "🔧 System Settings", "📁 Data Paths", "🔄 Actions"])

    with tab1:
        st.subheader("Trading Parameters")

        # Risk management
        st.markdown("**Risk Management**")
        risk_col1, risk_col2 = st.columns(2)

        with risk_col1:
            max_risk_per_trade = st.slider("Max Risk per Trade (%)",
                                         min_value=0.5, max_value=5.0,
                                         value=config.get('risk_management', {}).get('max_risk_per_trade', 2.0),
                                         step=0.1)
            max_portfolio_risk = st.slider("Max Portfolio Risk (%)",
                                         min_value=5.0, max_value=20.0,
                                         value=config.get('risk_management', {}).get('max_portfolio_risk', 10.0),
                                         step=0.5)

        with risk_col2:
            max_positions = st.number_input("Max Positions",
                                          min_value=5, max_value=50,
                                          value=config.get('risk_management', {}).get('max_positions', 20))
            rebalance_threshold = st.slider("Rebalance Threshold (%)",
                                          min_value=1.0, max_value=10.0,
                                          value=config.get('risk_management', {}).get('rebalance_threshold', 5.0),
                                          step=0.5)

        # Signal parameters
        st.markdown("**Signal Parameters**")
        signal_col1, signal_col2 = st.columns(2)

        with signal_col1:
            min_confidence = st.slider("Min Signal Confidence (%)",
                                     min_value=50, max_value=90,
                                     value=config.get('signals', {}).get('min_confidence', 70))
            signal_lookback = st.number_input("Signal Lookback (days)",
                                            min_value=20, max_value=200,
                                            value=config.get('signals', {}).get('lookback_period', 100))

        with signal_col2:
            momentum_threshold = st.slider("Momentum Threshold",
                                         min_value=0.0, max_value=0.5,
                                         value=config.get('signals', {}).get('momentum_threshold', 0.1),
                                         step=0.01)
            volatility_filter = st.slider("Volatility Filter",
                                        min_value=0.1, max_value=1.0,
                                        value=config.get('signals', {}).get('volatility_filter', 0.3),
                                        step=0.05)

    with tab2:
        st.subheader("System Settings")

        # Data settings
        st.markdown("**Data Settings**")
        data_col1, data_col2 = st.columns(2)

        with data_col1:
            update_frequency = st.selectbox("Data Update Frequency",
                                          ["Daily", "Weekly", "Manual"],
                                          index=["Daily", "Weekly", "Manual"].index(
                                              config.get('system', {}).get('update_frequency', 'Daily')))
            cache_timeout = st.number_input("Cache Timeout (hours)",
                                          min_value=1, max_value=24,
                                          value=config.get('system', {}).get('cache_timeout', 6))

        with data_col2:
            max_retries = st.number_input("Max API Retries",
                                        min_value=1, max_value=10,
                                        value=config.get('system', {}).get('max_retries', 3))
            timeout_seconds = st.number_input("API Timeout (seconds)",
                                            min_value=10, max_value=120,
                                            value=config.get('system', {}).get('timeout', 30))

        # Notification settings
        st.markdown("**Notifications**")
        notify_on_signals = st.checkbox("Notify on New Signals",
                                      value=config.get('notifications', {}).get('signals', True))
        notify_on_errors = st.checkbox("Notify on Errors",
                                     value=config.get('notifications', {}).get('errors', True))

    with tab3:
        st.subheader("Data Paths")

        # Display current paths
        data_dir = Path("data")
        st.markdown("**Current Data Structure:**")
        st.code(f"""
Data Directory: {data_dir.absolute()}
├── raw/
│   └── ohlcv/
│       └── nifty50/
├── processed/
│   ├── ohlcv/
│   │   └── nifty50/
│   └── indicators/
│       └── nifty50/
├── signals/
│   ├── backtest/
│   │   └── nifty50/
│   ├── final/
│   │   └── nifty50/
│   ├── risk/
│   │   └── nifty50/
│   └── screens/
│       └── nifty50/
└── universe/
    └── nifty50_constituents_latest.parquet
        """)

        # Path validation
        st.markdown("**Path Validation:**")
        paths_status = {
            "Raw OHLCV": (data_dir / "raw" / "ohlcv" / "nifty50").exists(),
            "Processed OHLCV": (data_dir / "processed" / "ohlcv" / "nifty50").exists(),
            "Indicators": (data_dir / "processed" / "indicators" / "nifty50").exists(),
            "Signals": (data_dir / "signals" / "final" / "nifty50").exists(),
            "Reports": (data_dir / "reports" / "performance").exists()
        }

        for path_name, exists in paths_status.items():
            status_icon = "✅" if exists else "❌"
            st.markdown(f"{status_icon} {path_name}")

    with tab4:
        st.subheader("Actions")

        # Save settings
        if st.button("💾 Save Settings", type="primary"):
            # Update config with new values
            new_config = {
                'risk_management': {
                    'max_risk_per_trade': max_risk_per_trade,
                    'max_portfolio_risk': max_portfolio_risk,
                    'max_positions': max_positions,
                    'rebalance_threshold': rebalance_threshold
                },
                'signals': {
                    'min_confidence': min_confidence,
                    'lookback_period': signal_lookback,
                    'momentum_threshold': momentum_threshold,
                    'volatility_filter': volatility_filter
                },
                'system': {
                    'update_frequency': update_frequency,
                    'cache_timeout': cache_timeout,
                    'max_retries': max_retries,
                    'timeout': timeout_seconds
                },
                'notifications': {
                    'signals': notify_on_signals,
                    'errors': notify_on_errors
                }
            }

            try:
                save_config(new_config)
                st.success("Settings saved successfully!")
            except Exception as e:
                st.error(f"Error saving settings: {e}")

        # Reset to defaults
        if st.button("🔄 Reset to Defaults"):
            try:
                # Reset logic would go here
                st.info("Reset functionality will be implemented.")
            except Exception as e:
                st.error(f"Error resetting settings: {e}")

        # Clear cache
        if st.button("🗑️ Clear Cache"):
            SessionState.clear_cache()

        # Export configuration
        if st.button("📤 Export Config"):
            try:
                config_json = json.dumps(config, indent=2)
                st.download_button(
                    label="Download Config",
                    data=config_json,
                    file_name="investment_engine_config.json",
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"Error exporting config: {e}")

    # Version info
    st.markdown("---")
    st.markdown("**System Information:**")
    st.markdown("- **Version:** 1.0.0")
    st.markdown("- **Python:** 3.8+")
    st.markdown("- **Data Source:** NSE + Yahoo Finance")
    st.markdown("- **Last Updated:** January 2024")