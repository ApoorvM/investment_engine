# Investment Engine Dashboard

A comprehensive Streamlit dashboard for the Indian stock market analysis and portfolio management system.

## Features

### 🏠 Home Dashboard
- Key performance metrics and portfolio overview
- Latest trading signals with confidence scores
- Portfolio equity curve visualization
- System health monitoring

### 📊 Market Overview
- Comprehensive market statistics
- Sector allocation analysis
- Market cap distribution
- Top performing stocks
- Interactive filters by sector and market cap

### 📈 Stock Analysis
- Detailed technical analysis for individual stocks
- Interactive price charts (Candlestick, Line, OHLC)
- Technical indicators (SMA, EMA, RSI, MACD)
- Volume analysis
- Signal information and entry/exit points

### 🚨 Signals Dashboard
- Real-time signal monitoring
- Signal distribution analysis
- Screening results
- Confidence-based filtering
- Sector and signal type filters

### 💼 Portfolio Management
- Current position monitoring
- Risk analysis and sizing
- Sector allocation breakdown
- Rebalancing suggestions

### 📉 Backtesting Results
- Historical performance analysis
- Equity curve and drawdown charts
- Returns distribution
- Trade log analysis
- Performance metrics (CAGR, Sharpe, Max Drawdown)

### 🔧 Pipeline Monitor
- Real-time pipeline health status
- Data freshness monitoring
- Component status indicators
- System logs and scheduled runs

### ⚙️ Settings
- Trading parameters configuration
- Risk management settings
- System preferences
- Data path validation

## Installation

1. Ensure you have Python 3.8+ installed
2. Install required packages:
```bash
pip install streamlit pandas plotly pyarrow toml
```

3. Run the data pipeline first to generate data:
```bash
python main.py run-pipeline
```

4. Start the dashboard:
```bash
streamlit run app/app.py
```

## Data Requirements

The dashboard expects data in the following structure:
```
data/
├── universe/
│   └── nifty50_constituents_latest.parquet
├── processed/
│   ├── ohlcv/
│   │   └── nifty50/
│   └── indicators/
│       └── nifty50/
├── signals/
│   ├── screens/
│   ├── risk/
│   └── final/
└── reports/
    └── performance/
```

## Usage

1. **Navigation**: Use the sidebar to navigate between different sections
2. **Filters**: Most pages include filters to customize the view
3. **Real-time Updates**: Data is cached and refreshed based on the configured intervals
4. **Settings**: Configure parameters in the Settings page

## Architecture

The dashboard is built with a modular architecture:

- **Services**: Data access layer (`app/services/`)
- **Components**: Reusable UI components (`app/components/`)
- **Pages**: Individual dashboard pages (`app/pages/`)
- **Utils**: Formatting and configuration utilities (`app/utils/`)
- **State**: Session management (`app/state/`)

## Development

To extend the dashboard:

1. Add new services in `app/services/`
2. Create reusable components in `app/components/`
3. Add new pages in `app/pages/`
4. Update the main app routing in `app/app.py`

## Troubleshooting

- **No data displayed**: Ensure the data pipeline has been run
- **Import errors**: Check that all required packages are installed
- **Performance issues**: Data is cached; try clearing cache in Settings
- **Port conflicts**: Change the port in the run command

## License

This project is part of the Investment Engine system for educational and research purposes.