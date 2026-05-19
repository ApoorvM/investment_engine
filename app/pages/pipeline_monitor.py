"""
Pipeline monitor page for the Investment Engine.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.services.pipeline import PipelineService
from app.components.status import render_pipeline_status, render_data_freshness
from app.state.session import SessionState
from app.utils.formatting import format_date

def render_pipeline_monitor():
    """Render the pipeline monitor page."""
    st.markdown('<div class="main-header">🔧 Pipeline Monitor</div>', unsafe_allow_html=True)
    st.markdown("Monitor the health and status of your data processing pipeline.")

    selected_index = SessionState.get('selected_index', 'NIFTY50')
    index_name = selected_index.lower()

    # Refresh button
    if st.button("🔄 Refresh Status", key="refresh_pipeline"):
        st.rerun()

    try:
        # Get pipeline status
        pipeline_status = PipelineService.get_pipeline_status(index_name=index_name)
        data_freshness = PipelineService.get_data_freshness(index_name=index_name)

        # Overall health
        st.subheader("🏥 Overall Health")
        health_color = "🟢" if pipeline_status['overall_health'] == 'healthy' else "🔴"
        st.markdown(f"### {health_color} System Status: {pipeline_status['overall_health'].title()}")

        # Pipeline components status
        st.subheader("📊 Pipeline Components")
        render_pipeline_status(pipeline_status)

        # Data freshness
        st.subheader("⏰ Data Freshness")
        render_data_freshness(data_freshness)

        # Last updates table
        st.subheader("📅 Last Updates")
        if pipeline_status['last_updates']:
            updates_data = []
            for component, last_update in pipeline_status['last_updates'].items():
                if last_update:
                    time_diff = datetime.now() - last_update
                    hours_old = time_diff.total_seconds() / 3600
                    status = "Fresh" if hours_old < 24 else "Stale" if hours_old < 72 else "Old"
                    status_color = "🟢" if status == "Fresh" else "🟡" if status == "Stale" else "🔴"
                    updates_data.append({
                        'Component': component.title(),
                        'Last Update': format_date(last_update),
                        'Hours Old': round(hours_old, 1),
                        'Status': f"{status_color} {status}"
                    })
                else:
                    updates_data.append({
                        'Component': component.title(),
                        'Last Update': 'Never',
                        'Hours Old': 'N/A',
                        'Status': '🔴 Missing'
                    })

            updates_df = pd.DataFrame(updates_data)
            st.dataframe(updates_df, use_container_width=True, hide_index=True)
        else:
            st.info("No update information available.")

        # Pipeline actions
        st.subheader("🚀 Pipeline Actions")
        st.markdown(f"**Quick Actions for Index:** **{selected_index}**")

        action_col1, action_col2, action_col3 = st.columns(3)

        with action_col1:
            if st.button("📥 Update Universe", key="update_universe"):
                st.info(f"Universe action is enabled for {selected_index}. Use the full pipeline button below.")

        with action_col2:
            if st.button("📊 Download OHLCV", key="download_ohlcv"):
                st.info(f"OHLCV action is enabled for {selected_index}. Use the full pipeline button below.")

        with action_col3:
            if st.button("🔄 Run Full Pipeline", key="run_pipeline"):
                with st.spinner(f"Running full pipeline for {selected_index}..."):
                    result = PipelineService.run_daily_update(index_name=index_name)
                if result['returncode'] == 0:
                    st.success(f"Full pipeline completed for {selected_index}.")
                    st.code(result['stdout'][-1000:])
                else:
                    st.error(f"Pipeline failed for {selected_index}.")
                    st.code(result['stderr'] or result['stdout'])

        # System logs
        st.subheader("📋 System Logs")
        st.info("Recent pipeline logs will be displayed here.")
        st.code("""
2024-01-15 09:00:01 - INFO - Universe update completed successfully
2024-01-15 09:05:23 - INFO - OHLCV download completed for 50 symbols
2024-01-15 09:10:45 - INFO - Technical indicators calculated
2024-01-15 09:15:12 - INFO - Screening completed with 45 candidates
2024-01-15 09:20:33 - INFO - Risk sizing completed for 12 positions
2024-01-15 09:25:01 - INFO - Signal generation completed
2024-01-15 09:30:15 - INFO - Backtesting completed successfully
        """)

        # Scheduled runs
        st.subheader("⏰ Scheduled Runs")
        st.markdown("""
        - **Daily Update**: Every day at 9:00 AM IST
        - **Weekly Report**: Every Monday at 8:00 AM IST
        - **Monthly Review**: First day of month at 7:00 AM IST
        """)

    except Exception as e:
        st.error(f"Error loading pipeline status: {e}")
        st.info("Make sure the data directory structure exists.")