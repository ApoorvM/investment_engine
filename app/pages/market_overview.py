"""
Market overview page for the Investment Engine.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.services.market_data import MarketDataService
from app.services.signals import SignalsService
from app.components.charts import render_sector_heatmap, render_market_cap_chart
from app.components.tables import render_market_table
from app.components.filters import render_sector_filter, render_market_cap_filter
from app.state.session import SessionState
from app.utils.formatting import format_currency, format_percentage

def render_market_overview():
    """Render the market overview page."""
    st.markdown('<div class="main-header">📊 Market Overview</div>', unsafe_allow_html=True)
    st.markdown("Comprehensive view of the Indian stock market landscape.")

    selected_index = SessionState.get('selected_index', 'NIFTY50')
    index_name = selected_index.lower()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_sector = render_sector_filter(index_name=index_name)
    with col2:
        selected_market_cap = render_market_cap_filter()
    with col3:
        st.markdown(f"**Index:** {selected_index}")

    # Load market data
    try:
        universe_df = MarketDataService.get_universe_data(index_name=index_name)
        signals_df = SignalsService.get_latest_signals(index_name=index_name)

        if not universe_df.empty:
            # Merge universe data with signals data to get performance metrics
            market_df = universe_df.copy()
            if not signals_df.empty:
                # Merge on Symbol to get performance data
                market_df = market_df.merge(
                    signals_df[['Symbol', 'Return_1M', 'Return_3M', 'Return_6M', 'Signal', 'Total_Score']], 
                    on='Symbol', 
                    how='left'
                )
            else:
                # Add empty columns if no signals data
                market_df['Return_1M'] = pd.NA
                market_df['Return_3M'] = pd.NA
                market_df['Return_6M'] = pd.NA
                market_df['Signal'] = pd.NA
                market_df['Total_Score'] = pd.NA

            # Filter data
            filtered_df = market_df.copy()
            if selected_sector != "All":
                filtered_df = filtered_df[filtered_df['Sector'] == selected_sector]
            if selected_market_cap != "All" and 'Market_Cap' in filtered_df.columns:
                market_caps = pd.to_numeric(filtered_df['Market_Cap'], errors='coerce')
                if selected_market_cap == "Small Cap":
                    filtered_df = filtered_df[market_caps < 5000]
                elif selected_market_cap == "Mid Cap":
                    filtered_df = filtered_df[(market_caps >= 5000) & (market_caps < 20000)]
                elif selected_market_cap == "Large Cap":
                    filtered_df = filtered_df[market_caps >= 20000]

            # Market statistics
            st.subheader("📈 Market Statistics")
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

            with stats_col1:
                st.metric("Total Companies", len(filtered_df))
            with stats_col2:
                # Handle missing market cap data
                valid_market_caps = filtered_df['Market_Cap'].dropna()
                if not valid_market_caps.empty:
                    avg_market_cap = valid_market_caps.mean()
                    st.metric("Avg Market Cap", format_currency(avg_market_cap))
                else:
                    st.metric("Avg Market Cap", "N/A")
            with stats_col3:
                # Handle missing market cap data
                valid_market_caps = filtered_df['Market_Cap'].dropna()
                if not valid_market_caps.empty:
                    total_market_cap = valid_market_caps.sum()
                    st.metric("Total Market Cap", format_currency(total_market_cap))
                else:
                    st.metric("Total Market Cap", "N/A")
            with stats_col4:
                if not signals_df.empty:
                    buy_signals = len(signals_df[signals_df['Signal'] == 'BUY'])
                    st.metric("Buy Signals", buy_signals)
                else:
                    st.metric("Buy Signals", 0)

            # Sector allocation
            st.subheader("🏢 Sector Allocation")
            if 'Sector' in filtered_df.columns:
                # Filter out rows with missing market cap or sector data
                sector_filtered = filtered_df.dropna(subset=['Sector', 'Market_Cap'])
                if not sector_filtered.empty:
                    sector_data = sector_filtered.groupby('Sector')['Market_Cap'].sum().reset_index()
                    total_market_cap = sector_data['Market_Cap'].sum()
                    if total_market_cap > 0:
                        sector_data['Percentage'] = (sector_data['Market_Cap'] / total_market_cap) * 100
                        render_sector_heatmap(sector_data)
                    else:
                        st.warning("No valid market cap data available for sector allocation chart.")
                else:
                    st.warning("No sector and market cap data available for sector allocation chart.")

            # Market cap distribution
            st.subheader("💰 Market Cap Distribution")
            render_market_cap_chart(filtered_df)

            # Top performers
            st.subheader("🚀 Top Performers")
            if 'Return_1M' in filtered_df.columns:
                # Filter out rows with missing return data
                performers_df = filtered_df.dropna(subset=['Return_1M'])
                if not performers_df.empty:
                    top_performers = performers_df.nlargest(10, 'Return_1M')[['Symbol', 'Company_Name', 'Return_1M', 'Market_Cap']]
                    # Format return percentage
                    top_performers['Return_1M'] = top_performers['Return_1M'].apply(lambda x: format_percentage(x) if pd.notna(x) else 'N/A')
                    render_market_table(top_performers, "Top 10 Performers (1M)")
                else:
                    st.info("No return data available for top performers.")
            else:
                st.info("Return data not available. Please run the data pipeline to generate performance metrics.")

            # Market table
            st.subheader("📋 Market Data")
            display_cols = ['Symbol', 'Company_Name', 'Sector', 'Market_Cap', 'PE_Ratio', 'Return_1M', 'Signal']
            available_cols = [col for col in display_cols if col in filtered_df.columns]
            
            if available_cols:
                table_df = filtered_df[available_cols].copy()
                # Format numeric columns
                if 'Market_Cap' in table_df.columns:
                    table_df['Market_Cap'] = table_df['Market_Cap'].apply(lambda x: format_currency(x) if pd.notna(x) else 'N/A')
                if 'Return_1M' in table_df.columns:
                    table_df['Return_1M'] = table_df['Return_1M'].apply(lambda x: format_percentage(x) if pd.notna(x) else 'N/A')
                if 'PE_Ratio' in table_df.columns:
                    table_df['PE_Ratio'] = table_df['PE_Ratio'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else 'N/A')
                
                render_market_table(table_df)
            else:
                st.info("No market data columns available to display.")

        else:
            st.warning("No market data available. Please run the data pipeline first.")

    except Exception as e:
        st.error(f"Error loading market data: {e}")
        st.info("Make sure the data pipeline has been run to generate market data.")
