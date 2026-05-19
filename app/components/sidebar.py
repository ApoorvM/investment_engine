"""
Sidebar navigation component for the Investment Engine dashboard.
"""

import streamlit as st
from app.state.session import SessionState
from app.services.market_data import MarketDataService
from app.services.signals import SignalsService
from app.services.pipeline import PipelineService

def render_sidebar() -> str:
    """Render the sidebar navigation and return selected page."""
    with st.sidebar:
        st.markdown('<div class="sidebar-header">📈 Investment Engine</div>', unsafe_allow_html=True)
        st.markdown("---")

        # Index selector
        index_options = ["NIFTY50", "NIFTY100", "NIFTY500"]
        current_index = SessionState.get('selected_index', 'NIFTY50')
        selected_index = st.selectbox(
            "Select Index",
            index_options,
            index=index_options.index(current_index) if current_index in index_options else 0,
            key="selected_index"
        )
        # Note: selected_index is automatically stored in session_state by the widget

        # Check if index changed and data is missing
        previous_index = SessionState.get('previous_selected_index', 'NIFTY50')
        if selected_index != previous_index:
            index_name = selected_index.lower()
            # Check if data is available
            universe_df = MarketDataService.get_universe_data(index_name=index_name)
            signals_df = SignalsService.get_latest_signals(index_name=index_name)
            
            if universe_df.empty or signals_df.empty:
                st.info(f"Data not available for {selected_index}. Running pipeline...")
                with st.spinner(f"Running data pipeline for {selected_index}..."):
                    result = PipelineService.run_daily_update(index_name=index_name)
                if result['returncode'] == 0:
                    st.success(f"Pipeline completed successfully for {selected_index}")
                else:
                    st.error(f"Pipeline failed for {selected_index}")
                    st.code(result['stderr'] or result['stdout'])
                st.rerun()
            
            # Update previous index
            SessionState.set('previous_selected_index', selected_index)

        st.markdown("---")

        # Navigation menu
        pages = [
            "🏠 Home",
            "📊 Market Overview",
            "📈 Stock Analysis",
            "🚨 Signal Dashboard",
            "💼 Portfolio",
            "📉 Backtesting",
            "🔧 Pipeline Monitor",
            "⚙️ Settings"
        ]

        selected_page = st.radio(
            "Navigation",
            pages,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # System status
        st.markdown("### System Status")
        st.success("✅ Backend Online")
        st.info("📊 Last Update: Today")

        # Quick actions
        st.markdown("### Quick Actions")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.info(f"Refreshing data for {selected_index}...")
            with st.spinner(f"Running pipeline for {selected_index}..."):
                result = PipelineService.run_daily_update(index_name=selected_index.lower())
            if result['returncode'] == 0:
                st.success(f"Data refreshed successfully for {selected_index}")
            else:
                st.error(f"Data refresh failed for {selected_index}")
                st.code(result['stderr'] or result['stdout'])
            st.rerun()

        if st.button("📤 Export Signals", use_container_width=True):
            st.info("Export functionality coming soon")

    return selected_page