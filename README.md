# Investment Engine

Local, modular Indian stock market analysis and recommendation engine with a comprehensive Streamlit dashboard.

## Overview

This project implements a complete Indian stock market analysis system with:

- **Backend Engine**: Data ingestion, technical analysis, screening, signal generation, risk management, and backtesting
- **Dashboard**: Professional Streamlit interface for monitoring and analysis
- **Modular Architecture**: Clean separation of concerns with services, components, and utilities

## Features

### Backend Engine
- Universe data fetching from NSE
- Historical OHLCV data download via Yahoo Finance
- Technical indicators (SMA, EMA, RSI, MACD, ATR)
- Multi-factor screening engine
- Risk-based position sizing
- Signal generation (BUY/HOLD/SELL)
- Historical backtesting with transaction costs
- Performance analytics and reporting

### Dashboard
- **Home**: Portfolio overview and key metrics
- **Market Overview**: Sector analysis and market statistics
- **Stock Analysis**: Individual stock technical analysis
- **Signals Dashboard**: Real-time signal monitoring
- **Portfolio**: Position management and risk analysis
- **Backtesting**: Performance analysis and trade logs
- **Pipeline Monitor**: System health and data freshness
- **Settings**: Configuration and parameter management

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the complete pipeline**:
```bash
python main.py run-pipeline
```

3. **Start the dashboard**:
```bash
streamlit run app/app.py
```

## Project Structure

```
├── main.py                 # CLI entry point
├── app/                    # Streamlit dashboard
│   ├── app.py             # Main dashboard application
│   ├── pages/             # Dashboard pages
│   ├── components/        # Reusable UI components
│   ├── services/          # Data access services
│   ├── utils/             # Utilities and formatting
│   └── state/             # Session management
├── data/                   # Data storage
│   ├── raw/               # Raw downloaded data
│   ├── processed/         # Cleaned and processed data
│   ├── signals/           # Generated signals and analysis
│   └── reports/           # Performance reports
├── indicators/            # Technical analysis indicators
├── strategies/            # Trading strategies and screening
├── risk/                  # Risk management
├── backtest/              # Backtesting engine
├── ingestion/             # Data ingestion pipeline
├── universe/              # Market universe management
├── reports/               # Reporting utilities
├── tests/                 # Unit tests
├── config/                # Configuration files
├── logs/                  # Application logs
└── scripts/               # Automation scripts
```

## CLI Commands

```bash
# Run complete pipeline
python main.py run-pipeline

# Individual pipeline steps
python main.py fetch-universe
python main.py download-ohlcv
python main.py calculate-indicators
python main.py screen-stocks
python main.py size-positions
python main.py generate-signals
python main.py run-backtest

# Daily update
python main.py daily-update

# View help
python main.py --help
```

## Dashboard Features

The Streamlit dashboard provides:

- **Real-time Monitoring**: Live pipeline status and data freshness
- **Interactive Charts**: Plotly-based visualizations for technical analysis
- **Filtering & Search**: Dynamic filtering across all data views
- **Performance Analytics**: Comprehensive backtesting results
- **Risk Management**: Position sizing and portfolio risk analysis
- **Signal Tracking**: Confidence-based signal monitoring

## Configuration

Edit `config/settings.toml` to customize:

- Risk management parameters
- Signal generation thresholds
- System update frequencies
- Data paths and caching settings

## Data Sources

- **NSE**: Stock universe and basic information
- **Yahoo Finance**: Historical price data
- **Local Storage**: Parquet and CSV files for performance

## Development

### Adding New Features

1. **Backend**: Add modules in appropriate directories
2. **Dashboard**: Create new pages in `app/pages/`
3. **Components**: Add reusable components in `app/components/`
4. **Services**: Implement data access in `app/services/`

### Testing

```bash
python -m pytest tests/
```

## Requirements

- Python 3.8+
- pandas, numpy, yfinance, pyarrow
- streamlit, plotly
- pytest (for testing)

## License

Educational and research purposes only. Not for production use without proper validation and risk assessment.
