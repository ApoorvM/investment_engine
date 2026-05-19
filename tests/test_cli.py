import sys

import main


def test_readme_cli_aliases_parse(monkeypatch):
    commands = [
        "download-ohlcv",
        "calculate-indicators",
        "screen-stocks",
        "size-positions",
        "generate-signals",
        "run-backtest",
    ]

    for command in commands:
        monkeypatch.setattr(sys, "argv", ["main.py", command, "--index", "NIFTY50"])
        args = main.parse_args()
        assert args.command == command
        assert args.index == "NIFTY50"


def test_run_pipeline_command_parse(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "run-pipeline",
            "--index",
            "NIFTY50",
            "--symbols",
            "INFY",
            "RELIANCE",
            "--limit",
            "2",
            "--skip-backtest",
        ],
    )

    args = main.parse_args()

    assert args.command == "run-pipeline"
    assert args.symbols == ["INFY", "RELIANCE"]
    assert args.limit == 2
    assert args.skip_backtest is True
