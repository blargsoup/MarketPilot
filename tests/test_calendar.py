from marketpilot.market import MarketCalendar
from marketpilot.data import MarketDataService


def run():

    market = MarketDataService().get_histories(
        ["QQQ"]
    )

    calendar = MarketCalendar.from_market(
        market
    )

    assert len(calendar) > 1000

    assert calendar.first_date < calendar.last_date

    assert (
        len(calendar.dates)
        == len(set(calendar.dates))
    )

    print("Calendar PASS")


if __name__ == "__main__":
    run()