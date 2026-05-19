"""
Backtesting page for the Investment Engine.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.services.backtest import BacktestService
from app.services.pipeline import PipelineService
from app.components.charts import render_equity_curve_chart, render_drawdown_chart, render_returns_distribution
from app.components.tables import render_trades_table
from app.components.metrics import render_performance_metrics
from app.state.session import SessionState
from app.utils.formatting import format_percentage, format_currency, format_number

def render_backtesting():
    """Render the backtesting page."""
    st.markdown('<div class="main-header">🔬 Backtesting Results</div>', unsafe_allow_html=True)
    st.markdown("Analyze historical performance of your trading strategy.")

    selected_index = SessionState.get('selected_index', 'NIFTY50')
    index_name = selected_index.lower()

    # Backtest controls
    st.subheader("🎯 Run Backtest")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input("Start Date", value=pd.to_datetime('2020-01-01'), key="backtest_start")
    with col2:
        end_date = st.date_input("End Date", value=pd.to_datetime('2024-01-01'), key="backtest_end")
    with col3:
        if st.button("🚀 Run Backtest", key="run_backtest", type="primary"):
            with st.spinner(f"Running backtest for {selected_index}..."):
                result = PipelineService.run_backtest(
                    index_name=index_name,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
            if result['returncode'] == 0:
                st.success(f"Backtest completed for {selected_index}!")
                st.rerun()  # Refresh to show new results
            else:
                st.error(f"Backtest failed for {selected_index}.")
                with st.expander("Error Details"):
                    st.code(result['stderr'] or result['stdout'])

    st.divider()

    try:
        # Load backtest data
        equity_df = BacktestService.get_backtest_results(index_name=index_name)
        trades_df = BacktestService.get_backtest_trades(index_name=index_name)
        metrics_df = BacktestService.get_performance_metrics(index_name=index_name)
        performance_summary = BacktestService.get_performance_summary(index_name=index_name)

        if not equity_df.empty:
            # Performance metrics
            st.subheader("📊 Performance Metrics")
            render_performance_metrics(performance_summary)

            # Equity curve
            st.subheader("📈 Equity Curve")
            render_equity_curve_chart(equity_df)

            # Drawdown analysis
            st.subheader("📉 Drawdown Analysis")
            if 'Drawdown' in equity_df.columns:
                render_drawdown_chart(equity_df)
            else:
                st.info("Drawdown data not available in current backtest results.")

            # Returns distribution
            st.subheader("📊 Returns Distribution")
            if 'Returns' in equity_df.columns:
                render_returns_distribution(equity_df)
            else:
                st.info("Returns data not available for distribution analysis.")

            # Trade log
            st.subheader("📋 Trade Log")
            if not trades_df.empty:
                render_trades_table(trades_df)

                # Trade statistics
                st.subheader("📈 Trade Statistics")
                trade_stats_col1, trade_stats_col2, trade_stats_col3, trade_stats_col4 = st.columns(4)

                with trade_stats_col1:
                    total_trades = len(trades_df)
                    st.metric("Total Trades", total_trades)
                with trade_stats_col2:
                    winning_trades = len(trades_df[trades_df['PnL'] > 0])
                    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                    st.metric("Win Rate", format_percentage(win_rate))
                with trade_stats_col3:
                    avg_win = trades_df[trades_df['PnL'] > 0]['PnL'].mean()
                    st.metric("Avg Win", format_currency(avg_win) if not pd.isna(avg_win) else "N/A")
                with trade_stats_col4:
                    avg_loss = trades_df[trades_df['PnL'] < 0]['PnL'].mean()
                    st.metric("Avg Loss", format_currency(avg_loss) if not pd.isna(avg_loss) else "N/A")
            else:
                st.info("No trade log available.")

            # Monthly returns
            st.subheader("📅 Monthly Returns")
            if 'Returns' in equity_df.columns:
                monthly_source = equity_df.copy()
                if 'Date' in monthly_source.columns:
                    monthly_dates = pd.to_datetime(monthly_source['Date'], errors='coerce')
                elif isinstance(monthly_source.index, pd.DatetimeIndex):
                    monthly_dates = monthly_source.index
                else:
                    monthly_dates = pd.to_datetime(monthly_source.index, errors='coerce')

                monthly_source['Month'] = monthly_dates.to_period('M')
                monthly_returns = monthly_source.dropna(subset=['Month']).groupby('Month')['Returns'].sum().reset_index()
                monthly_returns['Month'] = monthly_returns['Month'].astype(str)

                fig = px.bar(monthly_returns, x='Month', y='Returns',
                           title='Monthly Returns',
                           labels={'Returns': 'Return %', 'Month': 'Month'})
                fig.update_traces(marker_color='lightblue')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Monthly returns are unavailable for this backtest output.")

        else:
            st.warning("No backtest results available. Please run the backtesting pipeline.")
            st.info(f"Use the command: `python main.py backtest --index {selected_index}` to generate backtest results.")

        # Strategy parameters
        st.subheader("⚙️ Strategy Parameters")
        st.info("Strategy parameters and optimization results will be displayed here.")

    except Exception as e:
        st.error(f"Error loading backtest data: {e}")
        st.info("Make sure the backtesting pipeline has been run.")
