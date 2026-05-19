"""
Portfolio service for loading and processing portfolio data.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict
from app.components.loaders import load_csv_data, load_parquet_data, get_data_path
from app.services.market_data import MarketDataService

class PortfolioService:
    """Service for accessing portfolio data."""

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
    def _normalize_risk_positions(df: pd.DataFrame, index_name: str = "nifty50") -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()
        rename_map = {
            'symbol': 'Symbol',
            'price': 'Price',
            'position_value': 'Allocated_Capital',
            'portfolio_weight': 'Weight',
            'stop_loss_price': 'Stop_Loss',
            'stop_loss_pct': 'Stop_Loss_Pct',
            'risk_status': 'Risk_Status',
            'risk_reason': 'Risk_Reason',
            'risk_evaluated_at_utc': 'Risk_Evaluated_At_UTC',
            'as_of_date': 'As_Of_Date',
            'capital_at_risk': 'Capital_At_Risk',
            'total_score': 'Total_Score',
            'screen_result': 'Screen_Result',
            'portfolio_rank': 'Portfolio_Rank',
            'position_shares': 'Position_Shares',
        }
        df.rename(columns=rename_map, inplace=True)

        if 'Symbol' in df.columns:
            df['Symbol'] = df['Symbol'].astype(str).str.upper()

        if 'Allocated_Capital' not in df.columns and 'Position_Value' in df.columns:
            df['Allocated_Capital'] = df['Position_Value']

        if 'Selected' not in df.columns:
            df['Selected'] = df.get('Risk_Status', '').astype(str).str.lower() == 'selected'

        if 'Risk_Percentage' not in df.columns and 'Capital_At_Risk' in df.columns and 'Allocated_Capital' in df.columns:
            denominator = df['Allocated_Capital'].replace(0, pd.NA)
            df['Risk_Percentage'] = df['Capital_At_Risk'] / denominator

        df = MarketDataService.enrich_with_universe(df, index_name=index_name)

        return df

    @staticmethod
    def get_portfolio_positions(index_name: str = "nifty50") -> pd.DataFrame:
        """Get current portfolio positions."""
        risk_df = PortfolioService.get_risk_positions(index_name=index_name)
        if not risk_df.empty:
            return risk_df[risk_df['Selected'] == True]
        return pd.DataFrame()

    @staticmethod
    def get_risk_positions(index_name: str = "nifty50") -> pd.DataFrame:
        """Get risk analysis results."""
        path_base = get_data_path("signals", "risk", index_name, f"{index_name}_risk_latest")
        risk_df = PortfolioService._load_data_file(path_base)
        return PortfolioService._normalize_risk_positions(risk_df, index_name=index_name)

    @staticmethod
    def get_portfolio_metrics(index_name: str = "nifty50") -> Dict:
        """Calculate portfolio metrics."""
        positions = PortfolioService.get_portfolio_positions(index_name=index_name)
        if positions.empty:
            return {
                'total_value': 0,
                'total_positions': 0,
                'total_allocated': 0,
                'avg_position_size': 0
            }

        return {
            'total_value': positions['Allocated_Capital'].sum(),
            'total_positions': len(positions),
            'total_allocated': positions['Allocated_Capital'].sum(),
            'avg_position_size': positions['Allocated_Capital'].mean()
        }

    @staticmethod
    def get_sector_allocation(index_name: str = "nifty50") -> pd.DataFrame:
        """Get sector allocation breakdown."""
        positions = PortfolioService.get_portfolio_positions(index_name=index_name)
        if positions.empty:
            return pd.DataFrame()

        if 'Sector' not in positions.columns:
            universe_df = MarketDataService.get_universe_data(index_name=index_name)
            if not universe_df.empty and 'Symbol' in universe_df.columns and 'Sector' in universe_df.columns:
                positions = positions.merge(universe_df[['Symbol', 'Sector']], on='Symbol', how='left')

        if 'Sector' not in positions.columns:
            return pd.DataFrame()

        sector_alloc = positions.groupby('Sector')['Allocated_Capital'].sum().reset_index()
        sector_alloc['Percentage'] = (sector_alloc['Allocated_Capital'] / sector_alloc['Allocated_Capital'].sum()) * 100
        return sector_alloc
