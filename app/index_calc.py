"""Pure index calculation logic, kept free of database and web code so it is easy to test."""

from collections.abc import Mapping
from datetime import date

BASE_LEVEL = 1000.0


def compute_index_levels(
    prices_by_date: Mapping[date, Mapping[str, float]],
    shares: Mapping[str, int],
    base_level: float = BASE_LEVEL,
) -> list[tuple[date, float, float | None]]:
    """Compute a market-cap-weighted index level for each date.

    The index is set to ``base_level`` on the first date, and every later level is
    scaled by the change in total market capitalisation:

        level_t = base_level * (sum(price_t * shares)) / (sum(price_base * shares))

    Returns a list of ``(date, level, daily_return)`` sorted by date. The first
    daily return is ``None``.

    Raises ``ValueError`` if there are no constituents, or if any constituent has
    no price on a date (an index should never be calculated from incomplete data).
    """
    if not shares:
        raise ValueError("at least one constituent is required")
    if not prices_by_date:
        return []

    def market_cap(day: date) -> float:
        day_prices = prices_by_date[day]
        missing = sorted(set(shares) - set(day_prices))
        if missing:
            raise ValueError(f"missing prices for {missing} on {day.isoformat()}")
        return sum(day_prices[ticker] * count for ticker, count in shares.items())

    days = sorted(prices_by_date)
    base_cap = market_cap(days[0])

    results: list[tuple[date, float, float | None]] = []
    previous: float | None = None
    for day in days:
        level = base_level * market_cap(day) / base_cap
        daily_return = None if previous is None else level / previous - 1
        results.append((day, level, daily_return))
        previous = level
    return results
