from datetime import date

import pytest

from app.index_calc import compute_index_levels

SHARES = {"AAA": 100, "BBB": 200}
D1, D2, D3 = date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)


def test_first_day_is_base_level_with_no_return():
    result = compute_index_levels({D1: {"AAA": 10.0, "BBB": 5.0}}, SHARES)
    assert result == [(D1, 1000.0, None)]


def test_level_follows_market_cap_change():
    prices = {
        D1: {"AAA": 10.0, "BBB": 5.0},  # cap = 1000 + 1000 = 2000
        D2: {"AAA": 11.0, "BBB": 5.5},  # cap = 1100 + 1100 = 2200 (+10%)
        D3: {"AAA": 11.0, "BBB": 5.5},  # unchanged
    }
    result = compute_index_levels(prices, SHARES)
    assert [r[1] for r in result] == pytest.approx([1000.0, 1100.0, 1100.0])
    assert result[1][2] == pytest.approx(0.10)
    assert result[2][2] == pytest.approx(0.0)


def test_dates_are_sorted_regardless_of_input_order():
    prices = {
        D2: {"AAA": 11.0, "BBB": 5.5},
        D1: {"AAA": 10.0, "BBB": 5.0},
    }
    result = compute_index_levels(prices, SHARES)
    assert [r[0] for r in result] == [D1, D2]


def test_larger_company_has_more_weight():
    # Only the large company moves: the index should move by its weight (50%) of the change.
    prices = {
        D1: {"AAA": 10.0, "BBB": 5.0},
        D2: {"AAA": 12.0, "BBB": 5.0},  # cap 2200 vs 2000
    }
    result = compute_index_levels(prices, SHARES)
    assert result[1][1] == pytest.approx(1100.0)


def test_missing_price_is_rejected():
    prices = {D1: {"AAA": 10.0, "BBB": 5.0}, D2: {"AAA": 11.0}}
    with pytest.raises(ValueError, match="missing prices"):
        compute_index_levels(prices, SHARES)


def test_no_constituents_is_rejected():
    with pytest.raises(ValueError, match="constituent"):
        compute_index_levels({D1: {"AAA": 10.0}}, {})


def test_no_prices_returns_empty_list():
    assert compute_index_levels({}, SHARES) == []
