import argparse

from marketpilot.application import Application


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh market data from Yahoo Finance",
    )

    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run full historical backtest",
    )

    args = parser.parse_args()

    app = Application()

    app.run(
        refresh=args.refresh,
        backtest=args.backtest,
    )


if __name__ == "__main__":

    main()