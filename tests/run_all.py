from .test_buy_and_hold import run as buyhold
from .test_strategy import run as strategy


def run():

    buyhold()

    strategy()

    print()
    print("All tests passed.")


if __name__ == "__main__":
    run()