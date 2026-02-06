"""Test snapshot fixture loading and structure."""

from typing import Any, Dict


def test_normal_market_snapshot_structure(snapshot_normal_market: Dict[str, Any]) -> None:
    """Verify normal market snapshot has correct structure."""
    assert snapshot_normal_market["scenario"] == "normal_market"
    assert "timestamp" in snapshot_normal_market
    assert "symbols" in snapshot_normal_market

    # Verify all symbols present
    assert "SPY" in snapshot_normal_market["symbols"]
    assert "QQQ" in snapshot_normal_market["symbols"]
    assert "IWM" in snapshot_normal_market["symbols"]

    # Verify SPY data structure
    spy = snapshot_normal_market["symbols"]["SPY"]
    assert "currentPrice" in spy
    assert "historicalBars" in spy
    assert "optionChain" in spy

    # Verify data completeness
    assert spy["currentPrice"] > 0
    assert len(spy["historicalBars"]) == 60
    assert len(spy["optionChain"]) == 10


def test_all_scenarios_load(all_scenario_snapshots: Dict[str, Dict[str, Any]]) -> None:
    """Verify all 5 scenarios load successfully."""
    assert len(all_scenario_snapshots) == 5

    expected_scenarios = [
        "normal_market",
        "high_volatility",
        "low_volatility",
        "market_open",
        "end_of_day",
    ]

    for scenario_name in expected_scenarios:
        assert scenario_name in all_scenario_snapshots
        snapshot = all_scenario_snapshots[scenario_name]
        assert snapshot["scenario"] == scenario_name
        assert len(snapshot["symbols"]) == 3


def test_option_chain_greeks(snapshot_normal_market: Dict[str, Any]) -> None:
    """Verify option chain has Greeks data."""
    spy_options = snapshot_normal_market["symbols"]["SPY"]["optionChain"]

    for option in spy_options:
        assert "delta" in option
        assert "gamma" in option
        assert "theta" in option
        assert "vega" in option
        assert "impliedVol" in option


def test_historical_bars_ohlcv(snapshot_normal_market: Dict[str, Any]) -> None:
    """Verify historical bars have OHLCV data."""
    spy_bars = snapshot_normal_market["symbols"]["SPY"]["historicalBars"]

    for bar in spy_bars:
        assert "open" in bar
        assert "high" in bar
        assert "low" in bar
        assert "close" in bar
        assert "volume" in bar
        assert "wap" in bar
        assert bar["high"] >= bar["low"]
        assert bar["volume"] > 0


def test_high_volatility_characteristics(snapshot_high_volatility: Dict[str, Any]) -> None:
    """Verify high volatility snapshot has elevated IV."""
    spy_options = snapshot_high_volatility["symbols"]["SPY"]["optionChain"]

    # At least some options should have elevated IV (>25%)
    high_iv_count = sum(1 for opt in spy_options if opt["impliedVol"] > 25.0)
    assert high_iv_count > 0, "Expected elevated IV in high volatility scenario"


def test_low_volatility_characteristics(snapshot_low_volatility: Dict[str, Any]) -> None:
    """Verify low volatility snapshot has compressed IV."""
    spy_options = snapshot_low_volatility["symbols"]["SPY"]["optionChain"]

    # Average IV should be low (<15%)
    avg_iv = sum(opt["impliedVol"] for opt in spy_options) / len(spy_options)
    assert avg_iv < 15.0, f"Expected low average IV in low volatility scenario, got {avg_iv:.2f}"

    # At least 50% of options should have IV < 12%
    low_iv_count = sum(1 for opt in spy_options if opt["impliedVol"] < 12.0)
    assert (
        low_iv_count >= len(spy_options) / 2
    ), f"Expected at least 50% options with IV < 12%, got {low_iv_count}/{len(spy_options)}"


def test_market_open_bar_count(snapshot_market_open: Dict[str, Any]) -> None:
    """Verify market open snapshot has 30 minutes of data."""
    spy_bars = snapshot_market_open["symbols"]["SPY"]["historicalBars"]
    assert len(spy_bars) == 30, "Market open should have 30 bars (first 30 minutes)"


def test_end_of_day_expiry(snapshot_end_of_day: Dict[str, Any]) -> None:
    """Verify end of day snapshot has 0 DTE options."""
    spy_options = snapshot_end_of_day["symbols"]["SPY"]["optionChain"]

    # All options should expire today (2026-02-06)
    for opt in spy_options:
        assert opt["expiry"] == "20260206", "Expected 0 DTE options in end of day"


def test_option_chain_structure(snapshot_normal_market: Dict[str, Any]) -> None:
    """Verify option chain has proper structure."""
    spy_options = snapshot_normal_market["symbols"]["SPY"]["optionChain"]

    for option in spy_options:
        # Required fields
        assert "symbol" in option
        assert "strike" in option
        assert "expiry" in option
        assert "right" in option  # C or P

        # Pricing fields
        assert "bid" in option
        assert "ask" in option
        assert "last" in option

        # Volume/OI
        assert "volume" in option
        assert "openInterest" in option

        # Greeks
        assert "delta" in option
        assert "gamma" in option
        assert "theta" in option
        assert "vega" in option
        assert "impliedVol" in option

        # Validate right is C or P
        assert option["right"] in ["C", "P"]

        # Validate bid/ask spread
        assert option["ask"] >= option["bid"]


def test_historical_bars_chronological(snapshot_normal_market: Dict[str, Any]) -> None:
    """Verify historical bars are in chronological order."""
    spy_bars = snapshot_normal_market["symbols"]["SPY"]["historicalBars"]

    for i in range(1, len(spy_bars)):
        prev_time = spy_bars[i - 1]["datetime"]
        curr_time = spy_bars[i]["datetime"]
        assert curr_time > prev_time, "Historical bars should be in chronological order"


def test_price_consistency(snapshot_normal_market: Dict[str, Any]) -> None:
    """Verify current price is reasonable vs historical bars."""
    spy_data = snapshot_normal_market["symbols"]["SPY"]
    current_price = spy_data["currentPrice"]
    last_bar = spy_data["historicalBars"][-1]

    # Current price should be within 5% of last bar close
    price_diff_pct = abs(current_price - last_bar["close"]) / last_bar["close"]
    assert price_diff_pct < 0.05, "Current price too far from last bar close"


def test_all_symbols_present(all_scenario_snapshots: Dict[str, Dict[str, Any]]) -> None:
    """Verify all scenarios have SPY, QQQ, IWM data."""
    for scenario_name, snapshot in all_scenario_snapshots.items():
        assert "SPY" in snapshot["symbols"], f"{scenario_name} missing SPY"
        assert "QQQ" in snapshot["symbols"], f"{scenario_name} missing QQQ"
        assert "IWM" in snapshot["symbols"], f"{scenario_name} missing IWM"

        # Each symbol should have complete data
        for symbol in ["SPY", "QQQ", "IWM"]:
            sym_data = snapshot["symbols"][symbol]
            assert sym_data["currentPrice"] > 0
            assert len(sym_data["historicalBars"]) > 0
            assert len(sym_data["optionChain"]) == 10
