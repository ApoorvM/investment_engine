"""Application entry point for the Investment Engine."""

from __future__ import annotations

import argparse

from backtest.engine import run_backtest
from indicators.technical import build_indicators_for_universe
from ingestion.cleaning import process_ohlcv_universe
from ingestion.ohlcv import download_universe_ohlcv
from reports.performance import analyze_backtest
from risk.portfolio import run_portfolio_risk
from strategies.screening import run_basic_screen
from strategies.signals import generate_signals
from universe.constituents import fetch_index_constituents
from utils.config import load_settings
from utils.logging import setup_logging
from utils.paths import ensure_storage_directories, project_root


def run_health_check() -> None:
    """Run a local health check."""
    settings = load_settings()
    directories = ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Investment Engine health check started")
    logger.info("Project root: %s", project_root())
    logger.info("Default index: %s", settings["market"]["default_index"])
    logger.info("Storage directories ready: %s", len(directories))

    print("Investment Engine Phase 1 health check passed.")
    print(f"Project: {settings['project']['name']}")
    print(f"Default index: {settings['market']['default_index']}")
    print("Storage directories:")
    for directory in directories:
        print(f"  - {directory}")


def run_fetch_universe(index_name: str) -> None:
    """Fetch and save an index constituent universe."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Fetching universe for %s", index_name)
    snapshot = fetch_index_constituents(index_name=index_name, settings=settings)
    logger.info(
        "Saved %s universe snapshot with %s rows to %s",
        snapshot.index_name,
        snapshot.row_count,
        snapshot.snapshot_path,
    )

    print(f"Fetched {snapshot.row_count} constituents for {snapshot.index_name}.")
    print(f"Snapshot date: {snapshot.snapshot_date}")
    print(f"Source: {snapshot.source_url}")
    print(f"Snapshot parquet: {snapshot.snapshot_path}")
    print(f"Latest parquet: {snapshot.latest_path}")


def run_fetch_prices(
    index_name: str,
    start_date: str | None,
    end_date: str | None,
    symbols: list[str] | None,
    limit: int | None,
    full_refresh: bool,
) -> None:
    """Download and save historical OHLCV prices."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Downloading OHLCV data for %s", index_name)
    batch = download_universe_ohlcv(
        index_name=index_name,
        settings=settings,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        limit=limit,
        incremental=not full_refresh,
    )
    logger.info(
        "OHLCV batch complete: %s successful, %s failed",
        batch.successful_symbols,
        batch.failed_symbols,
    )

    print(f"OHLCV download complete for {batch.index_name}.")
    print(f"Requested symbols: {batch.requested_symbols}")
    print(f"Successful symbols: {batch.successful_symbols}")
    print(f"Failed symbols: {batch.failed_symbols}")
    for result in batch.results:
        output = result.output_path if result.output_path else result.message
        print(
            f"  - {result.symbol}: {result.status}, mode={result.mode}, "
            f"start={result.start_date}, rows={result.row_count}, {output}"
        )


def run_process_prices(
    index_name: str,
    symbols: list[str] | None,
    limit: int | None,
) -> None:
    """Clean and save processed OHLCV data."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Processing OHLCV data for %s", index_name)
    batch = process_ohlcv_universe(
        index_name=index_name,
        settings=settings,
        symbols=symbols,
        limit=limit,
    )
    logger.info(
        "OHLCV processing complete: %s successful, %s failed",
        batch.successful_files,
        batch.failed_files,
    )

    print(f"OHLCV processing complete for {batch.index_name}.")
    print(f"Requested files: {batch.requested_files}")
    print(f"Successful files: {batch.successful_files}")
    print(f"Failed files: {batch.failed_files}")
    for result in batch.results:
        output = result.output_path if result.output_path else "; ".join(result.warnings)
        warning_text = f", warnings={len(result.warnings)}" if result.warnings else ""
        print(
            f"  - {result.symbol}: {result.status}, rows_in={result.rows_in}, "
            f"rows_out={result.rows_out}{warning_text}, {output}"
        )


def run_build_indicators(
    index_name: str,
    symbols: list[str] | None,
    limit: int | None,
) -> None:
    """Build technical indicators from processed OHLCV data."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Building indicators for %s", index_name)
    batch = build_indicators_for_universe(
        index_name=index_name,
        settings=settings,
        symbols=symbols,
        limit=limit,
    )
    logger.info(
        "Indicator build complete: %s successful, %s failed",
        batch.successful_files,
        batch.failed_files,
    )

    print(f"Indicator build complete for {batch.index_name}.")
    print(f"Requested files: {batch.requested_files}")
    print(f"Successful files: {batch.successful_files}")
    print(f"Failed files: {batch.failed_files}")
    for result in batch.results:
        output = result.output_path if result.output_path else result.message
        print(
            f"  - {result.symbol}: {result.status}, rows_in={result.rows_in}, "
            f"rows_out={result.rows_out}, {output}"
        )


def run_screen(
    index_name: str,
    symbols: list[str] | None,
    limit: int | None,
) -> None:
    """Run the basic screening engine."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Running basic screen for %s", index_name)
    result = run_basic_screen(
        index_name=index_name,
        settings=settings,
        symbols=symbols,
        limit=limit,
    )
    logger.info(
        "Screen complete: %s symbols screened, %s watchlist",
        result.screened_symbols,
        result.watchlist_symbols,
    )

    print(f"Screen complete for {result.index_name}.")
    print(f"Screened symbols: {result.screened_symbols}")
    print(f"Watchlist symbols: {result.watchlist_symbols}")
    print(f"Parquet output: {result.output_parquet_path}")
    print(f"CSV output: {result.output_csv_path}")


def run_risk(
    index_name: str,
    symbols: list[str] | None,
    limit: int | None,
) -> None:
    """Run portfolio risk management on screened candidates."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Running risk sizing for %s", index_name)
    result = run_portfolio_risk(
        index_name=index_name,
        settings=settings,
        symbols=symbols,
        limit=limit,
    )
    logger.info(
        "Risk sizing complete: %s selected, allocated %.2f",
        result.selected_symbols,
        result.total_allocated_capital,
    )

    print(f"Risk sizing complete for {result.index_name}.")
    print(f"Input symbols: {result.input_symbols}")
    print(f"Selected symbols: {result.selected_symbols}")
    print(f"Total allocated capital: {result.total_allocated_capital:.2f}")
    print(f"Parquet output: {result.output_parquet_path}")
    print(f"CSV output: {result.output_csv_path}")


def run_signals(
    index_name: str,
    symbols: list[str] | None,
) -> None:
    """Generate final risk-aware signals."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Generating final signals for %s", index_name)
    result = generate_signals(
        index_name=index_name,
        settings=settings,
        symbols=symbols,
    )
    logger.info(
        "Signal generation complete: %s buy candidates, %s watchlist",
        result.buy_candidates,
        result.watchlist_symbols,
    )

    print(f"Signal generation complete for {result.index_name}.")
    print(f"Total symbols: {result.total_symbols}")
    print(f"Buy candidates: {result.buy_candidates}")
    print(f"Watchlist symbols: {result.watchlist_symbols}")
    print(f"Parquet output: {result.output_parquet_path}")
    print(f"CSV output: {result.output_csv_path}")


def run_backtest_command(
    index_name: str,
    start_date: str | None,
    end_date: str | None,
    symbols: list[str] | None,
) -> None:
    """Run a historical backtest."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Running backtest for %s", index_name)
    result = run_backtest(
        index_name=index_name,
        settings=settings,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
    )
    logger.info(
        "Backtest complete: periods=%s, trades=%s, total_return=%.2f%%",
        result.periods,
        result.trades,
        result.total_return * 100,
    )

    print(f"Backtest complete for {result.index_name}.")
    print(f"Periods: {result.periods}")
    print(f"Trades: {result.trades}")
    print(f"Start equity: {result.start_equity:.2f}")
    print(f"End equity: {result.end_equity:.2f}")
    print(f"Total return: {result.total_return:.2%}")
    print(f"Equity curve: {result.equity_curve_path}")
    print(f"Trade log: {result.trades_path}")


def run_analyze_command(index_name: str) -> None:
    """Run performance analytics for saved backtest outputs."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Analyzing backtest performance for %s", index_name)
    result = analyze_backtest(index_name=index_name, settings=settings)
    logger.info(
        "Performance analysis complete: CAGR=%.2f%%, Sharpe=%.2f, max drawdown=%.2f%%",
        result.cagr * 100,
        result.sharpe,
        result.max_drawdown * 100,
    )

    print(f"Performance analysis complete for {result.index_name}.")
    print(f"Total return: {result.total_return:.2%}")
    print(f"CAGR: {result.cagr:.2%}")
    print(f"Sharpe: {result.sharpe:.2f}")
    print(f"Max drawdown: {result.max_drawdown:.2%}")
    print(f"Win rate: {result.win_rate:.2%}")
    print(f"Metrics parquet: {result.metrics_path}")
    print(f"Metrics CSV: {result.metrics_csv_path}")
    print(f"Markdown report: {result.markdown_report_path}")


def run_daily_update(index_name: str) -> None:
    """Run the complete daily update pipeline for fresh signals."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Starting daily update pipeline for %s", index_name)

    try:
        # Step 1: Fetch latest universe (check for constituent changes)
        logger.info("Step 1: Fetching universe")
        run_fetch_universe(index_name=index_name)

        # Step 2: Fetch latest prices (incremental update)
        logger.info("Step 2: Fetching latest prices")
        run_fetch_prices(
            index_name=index_name,
            start_date=None,  # Use default incremental
            end_date=None,
            symbols=None,
            limit=None,
            full_refresh=False,
        )

        # Step 3: Process/clean prices
        logger.info("Step 3: Processing prices")
        run_process_prices(
            index_name=index_name,
            symbols=None,
            limit=None,
        )

        # Step 4: Build technical indicators
        logger.info("Step 4: Building indicators")
        run_build_indicators(
            index_name=index_name,
            symbols=None,
            limit=None,
        )

        # Step 5: Run screening
        logger.info("Step 5: Running screening")
        run_screen(
            index_name=index_name,
            symbols=None,
            limit=None,
        )

        # Step 6: Apply risk management
        logger.info("Step 6: Applying risk management")
        run_risk(
            index_name=index_name,
            symbols=None,
            limit=None,
        )

        # Step 7: Generate final signals
        logger.info("Step 7: Generating final signals")
        run_signals(
            index_name=index_name,
            symbols=None,
        )

        logger.info("Daily update pipeline complete for %s", index_name)
        print(f"Daily update complete for {index_name}.")
        print("All data refreshed and new signals generated.")

    except Exception as e:
        logger.error("Daily update failed: %s", str(e))
        print(f"Daily update failed: {str(e)}")
        raise


def run_full_pipeline(
    index_name: str,
    start_date: str | None,
    end_date: str | None,
    symbols: list[str] | None,
    limit: int | None,
    full_refresh: bool,
    skip_backtest: bool,
) -> None:
    """Run the complete data, signal, and optional backtest pipeline."""
    settings = load_settings()
    ensure_storage_directories(settings)
    logger = setup_logging(settings)

    logger.info("Starting full pipeline for %s", index_name)
    print(f"Running full pipeline for {index_name}.")

    run_fetch_universe(index_name=index_name)
    run_fetch_prices(
        index_name=index_name,
        start_date=start_date,
        end_date=end_date,
        symbols=symbols,
        limit=limit,
        full_refresh=full_refresh,
    )
    run_process_prices(index_name=index_name, symbols=symbols, limit=limit)
    run_build_indicators(index_name=index_name, symbols=symbols, limit=limit)
    run_screen(index_name=index_name, symbols=symbols, limit=limit)
    run_risk(index_name=index_name, symbols=symbols, limit=limit)
    run_signals(index_name=index_name, symbols=symbols)

    if not skip_backtest:
        run_backtest_command(
            index_name=index_name,
            start_date=None,
            end_date=end_date,
            symbols=symbols,
        )
        run_analyze_command(index_name=index_name)

    logger.info("Full pipeline complete for %s", index_name)
    print(f"Full pipeline complete for {index_name}.")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Investment Engine")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("health", help="Run local project health check")

    pipeline_parser = subparsers.add_parser(
        "run-pipeline",
        help="Run complete pipeline: universe, prices, processing, indicators, screening, risk, signals, backtest, analytics",
    )
    pipeline_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier configured in settings.toml",
    )
    pipeline_parser.add_argument(
        "--start",
        default=None,
        help="Optional price download start date in YYYY-MM-DD format.",
    )
    pipeline_parser.add_argument(
        "--end",
        default=None,
        help="Optional price download/backtest end date in YYYY-MM-DD format.",
    )
    pipeline_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to process, for example INFY RELIANCE.",
    )
    pipeline_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional symbol limit for smoke tests, for example --limit 3.",
    )
    pipeline_parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Ignore existing OHLCV parquet files and download from the configured start date.",
    )
    pipeline_parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="Stop after final signal generation.",
    )

    fetch_parser = subparsers.add_parser(
        "fetch-universe",
        help="Fetch latest index constituents and save parquet snapshots",
    )
    fetch_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier configured in settings.toml",
    )

    prices_parser = subparsers.add_parser(
        "fetch-prices",
        aliases=["download-ohlcv"],
        help="Download historical OHLCV data for a saved universe",
    )
    prices_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with a saved latest universe snapshot",
    )
    prices_parser.add_argument(
        "--start",
        default=None,
        help="Start date in YYYY-MM-DD format. Defaults to settings.toml.",
    )
    prices_parser.add_argument(
        "--end",
        default=None,
        help="Optional end date in YYYY-MM-DD format. yfinance treats this as exclusive.",
    )
    prices_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to download, for example INFY RELIANCE.",
    )
    prices_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for smoke tests, for example --limit 3.",
    )
    prices_parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Ignore existing parquet files and download from the configured start date.",
    )

    process_parser = subparsers.add_parser(
        "process-prices",
        help="Clean raw OHLCV parquet files and save processed parquet outputs",
    )
    process_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with raw OHLCV files",
    )
    process_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to process, for example INFY RELIANCE.",
    )
    process_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for smoke tests, for example --limit 3.",
    )

    indicator_parser = subparsers.add_parser(
        "build-indicators",
        aliases=["calculate-indicators"],
        help="Build technical indicators from processed OHLCV parquet files",
    )
    indicator_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with processed OHLCV files",
    )
    indicator_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to process, for example INFY RELIANCE.",
    )
    indicator_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for smoke tests, for example --limit 3.",
    )

    screen_parser = subparsers.add_parser(
        "screen",
        aliases=["screen-stocks"],
        help="Run basic momentum, trend, volatility, and liquidity screens",
    )
    screen_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with indicator files",
    )
    screen_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to screen, for example INFY RELIANCE.",
    )
    screen_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for smoke tests, for example --limit 3.",
    )

    risk_parser = subparsers.add_parser(
        "risk",
        aliases=["size-positions"],
        help="Apply portfolio risk rules to the latest screen output",
    )
    risk_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with latest screen output",
    )
    risk_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to risk-size, for example INFY RELIANCE.",
    )
    risk_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit after risk ranking, for example --limit 5.",
    )

    signal_parser = subparsers.add_parser(
        "signals",
        aliases=["generate-signals"],
        help="Generate final risk-aware buy/watchlist/hold/avoid signals",
    )
    signal_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with latest screen and risk outputs",
    )
    signal_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to include, for example INFY RELIANCE.",
    )

    backtest_parser = subparsers.add_parser(
        "backtest",
        aliases=["run-backtest"],
        help="Run a historical monthly rebalance backtest",
    )
    backtest_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with indicator history",
    )
    backtest_parser.add_argument(
        "--start",
        default=None,
        help="Optional backtest start date in YYYY-MM-DD format.",
    )
    backtest_parser.add_argument(
        "--end",
        default=None,
        help="Optional backtest end date in YYYY-MM-DD format.",
    )
    backtest_parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional NSE symbols to include, for example INFY RELIANCE.",
    )

    analyze_parser = subparsers.add_parser(
        "analyze-performance",
        help="Analyze saved backtest equity curve and trade log",
    )
    analyze_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier with saved backtest outputs",
    )

    daily_parser = subparsers.add_parser(
        "daily-update",
        help="Run complete daily update pipeline: fetch universe/prices, process, indicators, screen, risk, signals",
    )
    daily_parser.add_argument(
        "--index",
        default="NIFTY50",
        help="Index identifier to update",
    )

    return parser.parse_args()


def main() -> None:
    """Run the selected command."""
    args = parse_args()
    if args.command == "run-pipeline":
        run_full_pipeline(
            index_name=args.index,
            start_date=args.start,
            end_date=args.end,
            symbols=args.symbols,
            limit=args.limit,
            full_refresh=args.full_refresh,
            skip_backtest=args.skip_backtest,
        )
        return
    if args.command == "fetch-universe":
        run_fetch_universe(index_name=args.index)
        return
    if args.command in {"fetch-prices", "download-ohlcv"}:
        run_fetch_prices(
            index_name=args.index,
            start_date=args.start,
            end_date=args.end,
            symbols=args.symbols,
            limit=args.limit,
            full_refresh=args.full_refresh,
        )
        return
    if args.command == "process-prices":
        run_process_prices(
            index_name=args.index,
            symbols=args.symbols,
            limit=args.limit,
        )
        return
    if args.command in {"build-indicators", "calculate-indicators"}:
        run_build_indicators(
            index_name=args.index,
            symbols=args.symbols,
            limit=args.limit,
        )
        return
    if args.command in {"screen", "screen-stocks"}:
        run_screen(
            index_name=args.index,
            symbols=args.symbols,
            limit=args.limit,
        )
        return
    if args.command in {"risk", "size-positions"}:
        run_risk(
            index_name=args.index,
            symbols=args.symbols,
            limit=args.limit,
        )
        return
    if args.command in {"signals", "generate-signals"}:
        run_signals(
            index_name=args.index,
            symbols=args.symbols,
        )
        return
    if args.command in {"backtest", "run-backtest"}:
        run_backtest_command(
            index_name=args.index,
            start_date=args.start,
            end_date=args.end,
            symbols=args.symbols,
        )
        return
    if args.command == "analyze-performance":
        run_analyze_command(index_name=args.index)
        return
    if args.command == "daily-update":
        run_daily_update(index_name=args.index)
        return

    run_health_check()


if __name__ == "__main__":
    main()
