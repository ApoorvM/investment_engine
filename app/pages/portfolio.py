"""
Portfolio page for the Investment Engine.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from app.services.portfolio import PortfolioService
from app.services.signals import SignalsService
from app.components.tables import render_portfolio_table
from app.components.charts import render_sector_allocation_chart, render_portfolio_performance_chart
from app.state.session import SessionState
from app.utils.formatting import format_currency, format_percentage

def render_portfolio():
    """Render the portfolio page."""
    st.markdown('<div class="main-header">💼 Portfolio Management</div>', unsafe_allow_html=True)
    st.markdown("Monitor your investment portfolio and risk management.")

    selected_index = SessionState.get('selected_index', 'NIFTY50')
    index_name = selected_index.lower()

    try:
        # Load portfolio data
        positions_df = PortfolioService.get_portfolio_positions(index_name=index_name)
        risk_positions_df = PortfolioService.get_risk_positions(index_name=index_name)
        sector_allocation_df = PortfolioService.get_sector_allocation(index_name=index_name)
        portfolio_metrics = PortfolioService.get_portfolio_metrics(index_name=index_name)

        # Portfolio metrics
        st.subheader("📊 Portfolio Metrics")
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

        with metrics_col1:
            st.metric("Total Value", format_currency(portfolio_metrics['total_value']))
        with metrics_col2:
            st.metric("Active Positions", portfolio_metrics['total_positions'])
        with metrics_col3:
            st.metric("Allocated Capital", format_currency(portfolio_metrics['total_allocated']))
        with metrics_col4:
            st.metric("Avg Position Size", format_currency(portfolio_metrics['avg_position_size']))

        # Current positions
        st.subheader("📋 Current Positions")
        if not positions_df.empty:
            render_portfolio_table(positions_df)
        else:
            st.info("No active positions. Signals will be converted to positions after risk sizing.")

        # Risk analysis
        st.subheader("⚠️ Risk Analysis")
        if not risk_positions_df.empty:
            # Show risk metrics
            risk_cols = ['Symbol', 'Signal', 'Allocated_Capital', 'Stop_Loss', 'Risk_Percentage']
            available_cols = [col for col in risk_cols if col in risk_positions_df.columns]

            if available_cols:
                st.dataframe(risk_positions_df[available_cols], use_container_width=True)

                # Risk distribution
                if 'Risk_Percentage' in risk_positions_df.columns:
                    fig = px.histogram(risk_positions_df, x='Risk_Percentage',
                                     title='Risk Distribution Across Positions',
                                     labels={'Risk_Percentage': 'Risk %'})
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No risk analysis data available. Run risk management pipeline.")

        # Sector allocation
        st.subheader("🏢 Sector Allocation")
        if not sector_allocation_df.empty:
            render_sector_allocation_chart(sector_allocation_df)
        else:
            st.info("Sector allocation data will be available when positions are active.")

        # Portfolio performance
        st.subheader("📈 Portfolio Performance")
        st.info("Portfolio performance charts will be available after backtesting runs.")

        # Rebalancing suggestions
        st.subheader("🔄 Rebalancing Suggestions")
        if not positions_df.empty:
            # Simple rebalancing logic (placeholder)
            st.info("Rebalancing suggestions will be implemented based on target allocations and drift thresholds.")
        else:
            st.info("Rebalancing suggestions will appear when portfolio positions are active.")

    except Exception as e:
        st.error(f"Error loading portfolio data: {e}")
        st.info("Make sure the portfolio and risk management pipelines have been run.")