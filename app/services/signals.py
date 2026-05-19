"""
Signals service for loading and processing trading signals.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from app.components.loaders import load_csv_data, load_parquet_data, get_data_path

class SignalsService:
    """Service for accessing signal data."""

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
    def _standardize_signal_value(signal: str) -> str:
        if pd.isna(signal):
            return signal

        normalized = str(signal).strip().lower()
        if 'buy' in normalized:
            return 'BUY'
        if 'sell' in normalized:
            return 'SELL'
        if 'hold' in normalized:
            return 'HOLD'
        return normalized.upper()

    @staticmethod
    def _normalize_signal_df(df: pd.DataFrame, index_name: str = "nifty50") -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()
        rename_map = {
            'symbol': 'Symbol',
            'company_name': 'Company_Name',
            'sector': 'Sector',
            'signal': 'Signal',
            'confidence': 'Confidence',
            'price': 'Price',
            'stop_loss_price': 'Stop_Loss',
            'stop_loss_pct': 'Stop_Loss_Pct',
            'position_value': 'Position_Value',
            'portfolio_weight': 'Portfolio_Weight',
            'risk_status': 'Risk_Status',
            'screen_result': 'Screen_Result',
            'risk_reason': 'Risk_Reason',
            'position_shares': 'Position_Shares',
            'capital_at_risk': 'Capital_At_Risk',
            'total_score': 'Total_Score',
            'return_1m': 'Return_1M',
            'return_3m': 'Return_3M',
            'return_6m': 'Return_6M',
            'signal_generated_at_utc': 'Signal_Generated_At_UTC'
        }
        df.rename(columns=rename_map, inplace=True)

        if 'Symbol' in df.columns:
            df['Symbol'] = df['Symbol'].astype(str).str.upper()

        if 'Signal' in df.columns:
            df['Signal'] = df['Signal'].apply(SignalsService._standardize_signal_value)

        if 'Confidence' not in df.columns and 'Total_Score' in df.columns:
            df['Confidence'] = df['Total_Score']

        if 'Selected' not in df.columns:
            if 'Risk_Status' in df.columns:
                df['Selected'] = df['Risk_Status'].astype(str).str.lower() == 'selected'
            else:
                df['Selected'] = False

        try:
            from app.services.market_data import MarketDataService
            df = MarketDataService.enrich_with_universe(df, index_name=index_name)
        except Exception:
            pass

        if 'Company_Name' not in df.columns:
            df['Company_Name'] = pd.NA
        if 'Sector' not in df.columns:
            df['Sector'] = pd.NA

        return df

    @staticmethod
    def get_latest_signals(index_name: str = "nifty50") -> pd.DataFrame:
        """Get latest signals data."""
        path_base = get_data_path("signals", "final", index_name, f"{index_name}_signals_latest")
        df = SignalsService._load_data_file(path_base)
        return SignalsService._normalize_signal_df(df, index_name=index_name)

    @staticmethod
    def get_screen_results(index_name: str = "nifty50") -> pd.DataFrame:
        """Get screening results."""
        path_base = get_data_path("signals", "screens", index_name, f"{index_name}_screen_latest")
        df = SignalsService._load_data_file(path_base)
        return SignalsService._normalize_signal_df(df, index_name=index_name)

    @staticmethod
    def get_risk_sized_positions(index_name: str = "nifty50") -> pd.DataFrame:
        """Get risk-sized positions."""
        path_base = get_data_path("signals", "risk", index_name, f"{index_name}_risk_latest")
        df = SignalsService._load_data_file(path_base)
        return SignalsService._normalize_signal_df(df, index_name=index_name)

    @staticmethod
    def get_signal_summary(index_name: str = "nifty50") -> dict:
        """Get signal summary statistics."""
        signals_df = SignalsService.get_latest_signals(index_name=index_name)
        if signals_df.empty:
            return {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'hold_signals': 0
            }

        return {
            'total_signals': len(signals_df),
            'buy_signals': len(signals_df[signals_df['Signal'] == 'BUY']),
            'sell_signals': len(signals_df[signals_df['Signal'] == 'SELL']),
            'hold_signals': len(signals_df[signals_df['Signal'] == 'HOLD'])
        }
