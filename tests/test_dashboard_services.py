import pandas as pd

from app.services.market_data import MarketDataService
from app.services.portfolio import PortfolioService
from app.services.signals import SignalsService
from app.utils.formatting import format_percentage


def test_market_enrichment_does_not_create_duplicate_columns():
    frame = pd.DataFrame(
        {
            "Symbol": ["ONGC"],
            "Company_Name": [pd.NA],
            "Sector": [pd.NA],
            "Signal": ["BUY"],
        }
    )

    enriched = MarketDataService.enrich_with_universe(frame, index_name="nifty50")

    assert "Company_Name_Universe" not in enriched.columns
    assert "Sector_Universe" not in enriched.columns
    assert enriched.loc[0, "Company_Name"] == "Oil & Natural Gas Corporation Ltd."
    assert enriched.loc[0, "Sector"] == "Oil Gas & Consumable Fuels"


def test_signals_service_returns_filterable_sector_columns():
    signals = SignalsService.get_latest_signals(index_name="nifty50")

    assert not signals.empty
    assert "Company_Name" in signals.columns
    assert "Sector" in signals.columns
    assert not any(column.endswith("_x") or column.endswith("_y") for column in signals.columns)


def test_portfolio_service_exposes_risk_percentage():
    positions = PortfolioService.get_risk_positions(index_name="nifty50")

    assert not positions.empty
    assert "Risk_Percentage" in positions.columns
    assert positions["Risk_Percentage"].notna().all()


def test_percentage_formatter_handles_ratios_and_scores():
    assert format_percentage(0.125) == "12.50%"
    assert format_percentage(94.75) == "94.75%"
