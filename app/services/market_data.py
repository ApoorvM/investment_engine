"""
Market data service for loading and processing market data.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List
from app.components.loaders import load_parquet_data, load_csv_data, get_data_path

class MarketDataService:
    """Service for accessing market data."""

    @staticmethod
    def get_universe_data(index_name: str = "nifty50") -> pd.DataFrame:
        """Get latest universe data."""
        file_path = get_data_path("universe", f"{index_name}_constituents_latest.parquet")
        universe_df = load_parquet_data(str(file_path))
        return MarketDataService._normalize_universe_df(universe_df)

    @staticmethod
    def get_universe(index_name: str = "nifty50") -> pd.DataFrame:
        """Backwards-compatible alias for get_universe_data."""
        return MarketDataService.get_universe_data(index_name)

    @staticmethod
    def get_ohlcv_data(symbol: str, index_name: str = "nifty50") -> pd.DataFrame:
        """Get OHLCV data for a symbol."""
        symbol_file = MarketDataService._find_symbol_file(symbol, index_name, "raw", "ohlcv")
        return MarketDataService._load_time_series(symbol_file)

    @staticmethod
    def get_processed_data(symbol: str, index_name: str = "nifty50") -> pd.DataFrame:
        """Get processed OHLCV data for a symbol."""
        symbol_file = MarketDataService._find_symbol_file(symbol, index_name, "processed", "ohlcv")
        return MarketDataService._load_time_series(symbol_file)

    @staticmethod
    def get_indicators_data(symbol: str, index_name: str = "nifty50") -> pd.DataFrame:
        """Get technical indicators data for a symbol."""
        symbol_file = MarketDataService._find_symbol_file(symbol, index_name, "processed", "indicators")
        return MarketDataService._load_time_series(symbol_file)

    @staticmethod
    def _find_symbol_file(symbol: str, index_name: str, *path_parts: str) -> Path:
        """Resolve a symbol file path using case-insensitive matching."""
        base_dir = get_data_path(*path_parts, index_name)
        symbol_key = str(symbol).strip().lower()

        candidates = [
            base_dir / f"{symbol_key}.parquet",
            base_dir / f"{symbol_key}.csv"
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        if base_dir.exists():
            for candidate in base_dir.iterdir():
                if candidate.is_file() and candidate.stem.lower() == symbol_key:
                    return candidate

        return base_dir / f"{symbol_key}.parquet"

    @staticmethod
    def _load_time_series(file_path: Path) -> pd.DataFrame:
        """Load time series data from CSV or Parquet and normalize column names."""
        if not file_path.exists():
            return pd.DataFrame()

        if file_path.suffix.lower() == ".csv":
            df = load_csv_data(str(file_path))
        else:
            df = load_parquet_data(str(file_path))

        return MarketDataService._normalize_time_series_df(df)

    @staticmethod
    def _normalize_time_series_df(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()
        rename_map = {
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'adj_close': 'Adj_Close',
            'adj_open': 'Adj_Open',
            'adj_high': 'Adj_High',
            'adj_low': 'Adj_Low',
            'symbol': 'Symbol',
            'yfinance_symbol': 'YFinance_Symbol',
            'provider': 'Provider',
        }

        indicator_map = {
            'sma_20': 'SMA_20',
            'sma_50': 'SMA_50',
            'sma_200': 'SMA_200',
            'ema_12': 'EMA_12',
            'ema_26': 'EMA_26',
            'ema_20': 'EMA_20',
            'rsi_14': 'RSI',
            'macd': 'MACD',
            'macd_signal': 'MACD_Signal',
            'macd_histogram': 'MACD_Histogram',
            'atr_14': 'ATR_14',
            'volume_sma_20': 'Volume_SMA_20',
            'volume_ratio_20': 'Volume_Ratio_20',
            'volume_sma_50': 'Volume_SMA_50',
            'volume_ratio_50': 'Volume_Ratio_50',
            'daily_return': 'Daily_Return'
        }

        df.rename(columns=rename_map, inplace=True)
        df.rename(columns={old: new for old, new in indicator_map.items() if old in df.columns}, inplace=True)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df.set_index('Date', inplace=True, drop=True)

        if 'Symbol' in df.columns:
            df['Symbol'] = df['Symbol'].astype(str).str.upper()

        return df

    @staticmethod
    def _normalize_universe_df(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()
        rename_map = {
            'company_name': 'Company_Name',
            'industry': 'Sector',
            'symbol': 'Symbol',
            'nse_symbol': 'NSE_Symbol',
            'yfinance_symbol': 'YFinance_Symbol',
            'index_name': 'Index_Name',
            'index_display_name': 'Index_Display_Name',
            'snapshot_date': 'Snapshot_Date',
            'fetched_at_utc': 'Fetched_At_UTC',
            'source_url': 'Source_URL'
        }

        df.rename(columns=rename_map, inplace=True)

        if 'Symbol' in df.columns:
            df['Symbol'] = df['Symbol'].astype(str).str.upper()

        if 'Sector' not in df.columns and 'industry' in df.columns:
            df['Sector'] = df['industry']

        if 'Market_Cap' not in df.columns:
            df['Market_Cap'] = pd.NA
        if 'PE_Ratio' not in df.columns:
            df['PE_Ratio'] = pd.NA
        if 'Returns_1M' not in df.columns and 'return_1m' in df.columns:
            df.rename(columns={'return_1m': 'Returns_1M'}, inplace=True)

        return df

    @staticmethod
    def enrich_with_universe(df: pd.DataFrame, index_name: str = "nifty50") -> pd.DataFrame:
        """Attach company and sector fields without creating duplicate merge columns."""
        if df.empty or 'Symbol' not in df.columns:
            return df

        universe_df = MarketDataService.get_universe_data(index_name=index_name)
        if universe_df.empty or 'Symbol' not in universe_df.columns:
            return df

        enrichment_cols = [col for col in ['Symbol', 'Company_Name', 'Sector'] if col in universe_df.columns]
        if len(enrichment_cols) <= 1:
            return df

        enriched = df.merge(
            universe_df[enrichment_cols].drop_duplicates(subset=['Symbol']),
            on='Symbol',
            how='left',
            suffixes=('', '_Universe'),
        )

        for col in ['Company_Name', 'Sector']:
            universe_col = f"{col}_Universe"
            if universe_col not in enriched.columns:
                continue
            if col in enriched.columns:
                enriched[col] = enriched[col].combine_first(enriched[universe_col])
                enriched.drop(columns=[universe_col], inplace=True)
            else:
                enriched.rename(columns={universe_col: col}, inplace=True)

        return enriched

    @staticmethod
    def get_sector_performance() -> pd.DataFrame:
        """Get sector performance data."""
        # Placeholder - would aggregate from individual stocks
        return pd.DataFrame({
            'Sector': ['IT', 'Banking', 'Energy', 'Pharma'],
            'Performance': [2.1, -0.5, 1.8, 3.2],
            'Market_Share': [15.2, 25.1, 12.8, 8.9]
        })

    @staticmethod
    def get_market_breadth() -> dict:
        """Get market breadth indicators."""
        return {
            'advancing': 35,
            'declining': 15,
            'above_50dma': 28,
            'above_200dma': 22
        }
