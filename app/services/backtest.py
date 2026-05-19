"""
Backtest service for loading and processing backtest results.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict
from app.components.loaders import load_csv_data, load_parquet_data, get_data_path

class BacktestService:
    """Service for accessing backtest data."""

    @staticmethod
    def _load_data_file(path_base: Path) -> pd.DataFrame:
        csv_path = path_base.with_suffix('.csv')
        parquet_path = path_base.with_suffix('.parquet')

        if csv_path.exists():
            return load_csv_data(str(csv_path))
        if parquet_path.exists():
            return load_parquet_data(str(parquet_path))

        return pd.DataFrame()

    @staticmethod
    def _normalize_equity_df(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()
        rename_map = {
            'date': 'Date',
            'equity': 'Equity',
            'period_return': 'Returns',
            'positions': 'Positions',
            'cash_weight': 'Cash_Weight'
        }
        df.rename(columns=rename_map, inplace=True)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df.set_index('Date', inplace=True, drop=True)

        if 'Equity' in df.columns:
            df['Drawdown'] = df['Equity'] / df['Equity'].cummax() - 1

        return df

    @staticmethod
    def _normalize_trade_df(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()
        rename_map = {
            'entry_date': 'Entry_Date',
            'exit_date': 'Exit_Date',
            'symbol': 'Symbol',
            'entry_price': 'Entry_Price',
            'exit_price': 'Exit_Price',
            'return': 'Returns',
            'net_return': 'PnL',
            'portfolio_weight': 'Portfolio_Weight',
            'position_value': 'Position_Value',
            'estimated_pnl': 'Estimated_PnL'
        }
        df.rename(columns=rename_map, inplace=True)

        if 'Symbol' in df.columns:
            df['Symbol'] = df['Symbol'].astype(str).str.upper()

        return df

    @staticmethod
    def get_backtest_results(index_name: str = "nifty50") -> pd.DataFrame:
        """Get backtest equity curve."""
        path_base = get_data_path("signals", "backtest", index_name, f"{index_name}_equity_curve")
        df = BacktestService._load_data_file(path_base)
        return BacktestService._normalize_equity_df(df)

    @staticmethod
    def get_backtest_trades(index_name: str = "nifty50") -> pd.DataFrame:
        """Get backtest trade log."""
        path_base = get_data_path("signals", "backtest", index_name, f"{index_name}_trade_log")
        df = BacktestService._load_data_file(path_base)
        return BacktestService._normalize_trade_df(df)

    @staticmethod
    def get_performance_metrics(index_name: str = "nifty50") -> pd.DataFrame:
        """Get performance metrics."""
        path_base = get_data_path("signals", "backtest", index_name, f"{index_name}_performance_metrics")
        return BacktestService._load_data_file(path_base)

    @staticmethod
    def get_performance_summary(index_name: str = "nifty50") -> Dict:
        """Get key performance metrics."""
        metrics_df = BacktestService.get_performance_metrics(index_name)
        if metrics_df.empty:
            return {
                'total_return': 0,
                'cagr': 0,
                'sharpe': 0,
                'max_drawdown': 0,
                'win_rate': 0
            }

        if 'Metric' in metrics_df.columns and 'Value' in metrics_df.columns:
            metrics_dict = dict(zip(metrics_df['Metric'], metrics_df['Value']))
            return {
                'total_return': metrics_dict.get('Total Return', 0),
                'cagr': metrics_dict.get('CAGR', 0),
                'sharpe': metrics_dict.get('Sharpe Ratio', 0),
                'max_drawdown': metrics_dict.get('Max Drawdown', 0),
                'win_rate': metrics_dict.get('Win Rate', 0)
            }

        first_row = metrics_df.iloc[0]
        return {
            'total_return': first_row.get('total_return', 0) if 'total_return' in first_row else first_row.get('Total Return', 0),
            'cagr': first_row.get('cagr', 0) if 'cagr' in first_row else first_row.get('CAGR', 0),
            'sharpe': first_row.get('sharpe', 0) if 'sharpe' in first_row else first_row.get('Sharpe Ratio', 0),
            'max_drawdown': first_row.get('max_drawdown', 0) if 'max_drawdown' in first_row else first_row.get('Max Drawdown', 0),
            'win_rate': first_row.get('win_rate', 0) if 'win_rate' in first_row else first_row.get('Win Rate', 0)
        }
