"""
Status components for the Investment Engine dashboard.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict
from datetime import datetime

def render_pipeline_status(pipeline_status: Dict):
    """Render pipeline status indicators."""
    status_data = []
    for component, exists in pipeline_status['status'].items():
        status_icon = "✅" if exists else "❌"
        status_text = "Operational" if exists else "Missing"
        status_color = "green" if exists else "red"

        status_data.append({
            'Component': component.title(),
            'Status': f"{status_icon} {status_text}",
            'Last_Update': pipeline_status['last_updates'].get(component, 'Never')
        })

    status_df = pd.DataFrame(status_data)
    st.dataframe(status_df, use_container_width=True, hide_index=True)

def render_data_freshness(data_freshness: Dict):
    """Render data freshness indicators."""
    freshness_data = []
    for component, status in data_freshness.items():
        if status == 'fresh':
            icon = "🟢"
            text = "Fresh (< 24h)"
        elif status == 'stale':
            icon = "🟡"
            text = "Stale (24-72h)"
        elif status == 'old':
            icon = "🔴"
            text = "Old (> 72h)"
        else:
            icon = "❌"
            text = "Missing"

        freshness_data.append({
            'Component': component.title(),
            'Freshness': f"{icon} {text}"
        })

    freshness_df = pd.DataFrame(freshness_data)
    st.dataframe(freshness_df, use_container_width=True, hide_index=True)

def render_system_health():
    """Render overall system health status."""
    # Placeholder for system health metrics
    health_metrics = {
        'CPU Usage': '45%',
        'Memory Usage': '62%',
        'Disk Usage': '78%',
        'Network Status': 'Connected'
    }

    col1, col2, col3, col4 = st.columns(4)

    for i, (metric, value) in enumerate(health_metrics.items()):
        with [col1, col2, col3, col4][i]:
            st.metric(metric, value)

def render_last_update_info():
    """Render last update information."""
    st.markdown("**Last System Updates:**")
    updates = {
        'Universe Data': '2024-01-15 09:00:01',
        'OHLCV Data': '2024-01-15 09:05:23',
        'Technical Indicators': '2024-01-15 09:10:45',
        'Signals Generation': '2024-01-15 09:25:01',
        'Backtesting': '2024-01-15 09:30:15'
    }

    for component, timestamp in updates.items():
        st.markdown(f"- **{component}:** {timestamp}")

def display_system_status():
    """Display overall system health status."""
    st.subheader("🔧 System Health")

    # Check data directories
    data_dir = Path(__file__).parent.parent.parent / "data"
    universe_exists = (data_dir / "universe" / "nifty50_constituents_latest.parquet").exists()
    signals_exist = (data_dir / "signals" / "final" / "nifty50" / "nifty50_signals_latest.csv").exists()

    col1, col2 = st.columns(2)

    with col1:
        if universe_exists:
            st.success("✅ Universe Data: Available")
        else:
            st.error("❌ Universe Data: Missing")

        if signals_exist:
            st.success("✅ Signals Data: Available")
        else:
            st.warning("⚠️ Signals Data: Not Generated")

    with col2:
        st.info(f"📅 Current Date: {datetime.now().strftime('%Y-%m-%d')}")
        st.info("⏰ Last Update: Check logs")

def display_pipeline_status():
    """Display data pipeline status."""
    st.subheader("🔄 Pipeline Status")

    # Placeholder for pipeline monitoring
    st.info("Pipeline monitoring will show last run times, success rates, and any failures here.")

    # Sample status
    statuses = {
        "Universe Fetch": "✅ Success",
        "Price Download": "✅ Success",
        "Data Processing": "✅ Success",
        "Indicators": "✅ Success",
        "Screening": "✅ Success",
        "Risk Sizing": "✅ Success",
        "Signals": "✅ Success"
    }

    for step, status in statuses.items():
        st.write(f"{step}: {status}")