"""
Investment Engine Dashboard - Main Streamlit Application

A professional dashboard for Indian stock market analysis and portfolio management.
"""

import sys
import streamlit as st
from pathlib import Path

# Ensure the project root is on the import path so the app package imports resolve correctly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure page
st.set_page_config(
    page_title="Investment Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS for dark mode friendly theme
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    [data-testid="stSidebar"] {
        background-color: #262730;
    }
    .sidebar-header {
        color: #ffffff;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Import components
from app.components.sidebar import render_sidebar
from app.pages.home import render_home
from app.pages.market_overview import render_market_overview
from app.pages.stock_analysis import render_stock_analysis
from app.pages.signals_dashboard import render_signals_dashboard
from app.pages.portfolio import render_portfolio
from app.pages.backtesting import render_backtesting
from app.pages.pipeline_monitor import render_pipeline_monitor
from app.pages.settings import render_settings

def main():
    """Main application entry point."""
    # Render sidebar navigation
    selected_page = render_sidebar()

    # Route to selected page
    if selected_page == "🏠 Home":
        render_home()
    elif selected_page == "📊 Market Overview":
        render_market_overview()
    elif selected_page == "📈 Stock Analysis":
        render_stock_analysis()
    elif selected_page == "🚨 Signal Dashboard":
        render_signals_dashboard()
    elif selected_page == "💼 Portfolio":
        render_portfolio()
    elif selected_page == "📉 Backtesting":
        render_backtesting()
    elif selected_page == "🔧 Pipeline Monitor":
        render_pipeline_monitor()
    elif selected_page == "⚙️ Settings":
        render_settings()

if __name__ == "__main__":
    main()