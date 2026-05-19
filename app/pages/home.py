"""
Home dashboard page for the Investment Engine.
"""

import streamlit as st
from app.services.signals import SignalsService
from app.services.portfolio import PortfolioService
from app.services.backtest import BacktestService
from app.services.pipeline import PipelineService
from app.state.session import SessionState
from app.utils.formatting import format_currency, format_percentage
from app.components.metrics import render_metric_card
from app.components.tables import render_signals_table
from app.components.charts import render_equity_curve_chart

def render_home():
    """Render the home dashboard."""
    selected_index = SessionState.get('selected_index', 'NIFTY50')
    index_name = selected_index.lower()

    st.markdown('<div class="main-header">🏠 Investment Engine Dashboard</div>', unsafe_allow_html=True)
    st.markdown(f"**Selected Index:** {selected_index}")
    st.markdown("Welcome to your professional Indian stock market analysis platform.")

    # Load data
    try:
        signal_summary = SignalsService.get_signal_summary(index_name=index_name)
        portfolio_metrics = PortfolioService.get_portfolio_metrics(index_name=index_name)
        backtest_summary = BacktestService.get_performance_summary(index_name=index_name)
        pipeline_status = PipelineService.get_pipeline_status(index_name=index_name)
        pipeline_freshness = PipelineService.get_data_freshness(index_name=index_name)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        signal_summary = {'total_signals': 0, 'buy_signals': 0, 'sell_signals': 0, 'hold_signals': 0}
        portfolio_metrics = {'total_value': 0, 'total_positions': 0, 'total_allocated': 0, 'avg_position_size': 0}
        backtest_summary = {'total_return': 0, 'cagr': 0, 'sharpe': 0, 'max_drawdown': 0, 'win_rate': 0}
        pipeline_status = {'overall_health': 'unknown'}
        pipeline_freshness = {}

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            "Total Signals",
            signal_summary['total_signals'],
            f"+{signal_summary['buy_signals']}",
            "signals"
        )

    with col2:
        render_metric_card(
            "Portfolio Value",
            format_currency(portfolio_metrics['total_value']),
            f"{format_percentage(backtest_summary.get('total_return', 0))}",
            "portfolio"
        )

    with col3:
        render_metric_card(
            "Active Positions",
            portfolio_metrics['total_positions'],
            "0",
            "positions"
        )

    with col4:
        render_metric_card(
            "System Health",
            pipeline_status['overall_health'].title(),
            "Operational" if pipeline_status['overall_health'] == 'healthy' else "Issues",
            "health"
        )

    st.markdown("---")

    # Latest signals table
    st.subheader("🚨 Latest Signals")
    try:
        signals_df = SignalsService.get_latest_signals(index_name=index_name)
        if not signals_df.empty:
            render_signals_table(signals_df.head(10))
        else:
            st.info("No signals available. Run the pipeline to generate signals.")
    except Exception as e:
        st.error(f"Error loading signals: {e}")

    # Equity curve chart
    st.subheader("📈 Portfolio Performance")
    try:
        equity_df = BacktestService.get_backtest_results(index_name=index_name)
        if not equity_df.empty:
            render_equity_curve_chart(equity_df)
        else:
            st.info("No backtest results available. Run backtesting to see performance.")
    except Exception as e:
        st.error(f"Error loading backtest results: {e}")

    # System status
    st.subheader("🔧 System Status")
    status_col1, status_col2 = st.columns(2)

    with status_col1:
        health_color = "🟢" if pipeline_status['overall_health'] == 'healthy' else "🔴"
        st.markdown(f"{health_color} **Data Pipeline:** {pipeline_status['overall_health'].title()}")

        signal_count = signal_summary['total_signals']
        signal_color = "🟢" if signal_count > 0 else "🟡"
        st.markdown(f"{signal_color} **Signal Generation:** {signal_count} signals active")

    with status_col2:
        # Show data freshness
        fresh_count = sum(1 for status in pipeline_freshness.values() if status == 'fresh')
        total_count = len(pipeline_freshness)
        freshness_color = "🟢" if fresh_count == total_count else "🟡" if fresh_count > 0 else "🔴"
        st.markdown(f"{freshness_color} **Data Freshness:** {fresh_count}/{total_count} components fresh")

        st.markdown("⏰ **Next Update:** Daily at 9:00 AM IST")