#!/usr/bin/env python3
"""Generate mock IBKR snapshot data for test fixtures."""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List


def generate_historical_bars(
    base_price: float,
    start_time: datetime,
    num_bars: int,
    trend: str = "up",  # "up", "down", "sideways", "volatile"
    volume_profile: str = "normal",  # "normal", "high", "low"
) -> List[Dict[str, Any]]:
    """Generate realistic historical bar data."""
    bars = []
    price = base_price

    for i in range(num_bars):
        bar_time = start_time + timedelta(minutes=i)

        # Price movement based on trend
        if trend == "up":
            price_change = 0.02 + (0.05 * (i / num_bars))  # Gradual uptrend
        elif trend == "down":
            price_change = -0.02 - (0.05 * (i / num_bars))
        elif trend == "volatile":
            price_change = 0.10 * math.sin(i / 5)  # Oscillating
        else:  # sideways
            price_change = 0.01 * ((i % 3) - 1)  # Tight range

        price += price_change

        # OHLC generation
        bar_open = price
        bar_high = price + abs(price_change) * 0.5
        bar_low = price - abs(price_change) * 0.3
        bar_close = price + price_change * 0.1

        # Volume based on profile
        if volume_profile == "high":
            volume = int(800000 + (i * 10000))
        elif volume_profile == "low":
            volume = int(200000 + (i * 1000))
        else:
            volume = int(500000 + (i * 5000))

        # WAP calculation (weighted average price)
        wap = (bar_high + bar_low + bar_close) / 3

        bars.append(
            {
                "datetime": bar_time.isoformat(),
                "open": round(bar_open, 2),
                "high": round(bar_high, 2),
                "low": round(bar_low, 2),
                "close": round(bar_close, 2),
                "volume": volume,
                "wap": round(wap, 2),
                "barCount": 1,
            }
        )

    return bars


def generate_option_chain(
    underlying_price: float,
    expiry_date: str,
    iv_level: float = 15.0,
    spread_width: float = 0.10,
) -> List[Dict[str, Any]]:
    """Generate realistic option chain data."""
    options = []

    # Generate 5 strikes above current price
    strikes: List[float] = [
        float(round(underlying_price + (i * 5), 0)) for i in range(-2, 8)
    ]  # 2 ITM, 8 OTM strikes

    for strike in strikes:
        # Calls (more liquid)
        moneyness: float = strike - underlying_price
        delta_raw: float = 0.50 - (moneyness / underlying_price) * 2
        delta: float = max(0.05, min(0.95, delta_raw))

        mid_price: float = max(0.10, abs(underlying_price - strike) * 0.02)

        call_option = {
            "symbol": f"SPY{expiry_date.replace('-', '')}C{int(strike*1000):08d}",
            "strike": strike,
            "expiry": expiry_date.replace("-", ""),
            "right": "C",
            "bid": round(mid_price - spread_width / 2, 2),
            "ask": round(mid_price + spread_width / 2, 2),
            "last": round(mid_price, 2),
            "volume": int(5000 - abs(moneyness) * 100),
            "openInterest": int(10000 - abs(moneyness) * 200),
            "impliedVol": round(iv_level + abs(moneyness) * 0.5, 2),
            "delta": round(delta, 4),
            "gamma": round(0.02 / (1 + abs(moneyness)), 4),
            "theta": round(-0.05 - abs(moneyness) * 0.01, 4),
            "vega": round(0.10 + abs(moneyness) * 0.02, 4),
        }
        options.append(call_option)

        # Puts (less liquid, only add a few)
        if len([o for o in options if o["right"] == "P"]) < 3:
            put_delta: float = delta - 1.0
            put_option: Dict[str, Any] = call_option.copy()
            symbol_str: str = str(put_option["symbol"])
            put_option["symbol"] = symbol_str.replace("C", "P")
            put_option["right"] = "P"
            put_option["delta"] = round(put_delta, 4)
            volume_val: float = float(put_option["volume"])
            put_option["volume"] = int(volume_val * 0.6)
            options.append(put_option)

    return options[:10]  # Return top 10 most relevant


def create_scenario_1_normal_market() -> Dict[str, Any]:
    """Scenario 1: Normal market conditions."""
    timestamp = datetime(2026, 2, 6, 14, 0, 0)
    start_time = datetime(2026, 2, 6, 9, 30, 0)

    return {
        "scenario": "normal_market",
        "timestamp": timestamp.isoformat(),
        "symbols": {
            "SPY": {
                "currentPrice": 689.26,
                "historicalBars": generate_historical_bars(
                    base_price=687.50,
                    start_time=start_time,
                    num_bars=60,
                    trend="up",
                    volume_profile="normal",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=689.26,
                    expiry_date="2026-02-07",
                    iv_level=14.0,
                    spread_width=0.08,
                ),
            },
            "QQQ": {
                "currentPrice": 621.65,
                "historicalBars": generate_historical_bars(
                    base_price=620.00,
                    start_time=start_time,
                    num_bars=60,
                    trend="up",
                    volume_profile="normal",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=621.65,
                    expiry_date="2026-02-07",
                    iv_level=16.0,
                    spread_width=0.10,
                ),
            },
            "IWM": {
                "currentPrice": 215.40,
                "historicalBars": generate_historical_bars(
                    base_price=214.80,
                    start_time=start_time,
                    num_bars=60,
                    trend="sideways",
                    volume_profile="low",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=215.40,
                    expiry_date="2026-02-07",
                    iv_level=18.0,
                    spread_width=0.15,
                ),
            },
        },
    }


def create_scenario_2_high_volatility() -> Dict[str, Any]:
    """Scenario 2: High volatility market."""
    timestamp = datetime(2026, 2, 6, 14, 0, 0)
    start_time = datetime(2026, 2, 6, 9, 30, 0)

    return {
        "scenario": "high_volatility",
        "timestamp": timestamp.isoformat(),
        "symbols": {
            "SPY": {
                "currentPrice": 685.20,
                "historicalBars": generate_historical_bars(
                    base_price=682.00,
                    start_time=start_time,
                    num_bars=60,
                    trend="volatile",
                    volume_profile="high",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=685.20,
                    expiry_date="2026-02-07",
                    iv_level=32.0,
                    spread_width=0.30,
                ),
            },
            "QQQ": {
                "currentPrice": 618.50,
                "historicalBars": generate_historical_bars(
                    base_price=615.00,
                    start_time=start_time,
                    num_bars=60,
                    trend="volatile",
                    volume_profile="high",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=618.50,
                    expiry_date="2026-02-07",
                    iv_level=35.0,
                    spread_width=0.35,
                ),
            },
            "IWM": {
                "currentPrice": 213.80,
                "historicalBars": generate_historical_bars(
                    base_price=212.00,
                    start_time=start_time,
                    num_bars=60,
                    trend="volatile",
                    volume_profile="normal",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=213.80,
                    expiry_date="2026-02-07",
                    iv_level=38.0,
                    spread_width=0.40,
                ),
            },
        },
    }


def create_scenario_3_low_volatility() -> Dict[str, Any]:
    """Scenario 3: Low volatility (complacency)."""
    timestamp = datetime(2026, 2, 6, 14, 0, 0)
    start_time = datetime(2026, 2, 6, 9, 30, 0)

    return {
        "scenario": "low_volatility",
        "timestamp": timestamp.isoformat(),
        "symbols": {
            "SPY": {
                "currentPrice": 690.15,
                "historicalBars": generate_historical_bars(
                    base_price=689.80,
                    start_time=start_time,
                    num_bars=60,
                    trend="sideways",
                    volume_profile="low",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=690.15,
                    expiry_date="2026-02-07",
                    iv_level=9.0,
                    spread_width=0.03,
                ),
            },
            "QQQ": {
                "currentPrice": 622.30,
                "historicalBars": generate_historical_bars(
                    base_price=622.00,
                    start_time=start_time,
                    num_bars=60,
                    trend="sideways",
                    volume_profile="low",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=622.30,
                    expiry_date="2026-02-07",
                    iv_level=10.0,
                    spread_width=0.04,
                ),
            },
            "IWM": {
                "currentPrice": 215.80,
                "historicalBars": generate_historical_bars(
                    base_price=215.70,
                    start_time=start_time,
                    num_bars=60,
                    trend="sideways",
                    volume_profile="low",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=215.80,
                    expiry_date="2026-02-07",
                    iv_level=12.0,
                    spread_width=0.06,
                ),
            },
        },
    }


def create_scenario_4_market_open() -> Dict[str, Any]:
    """Scenario 4: Market open high volume."""
    timestamp = datetime(2026, 2, 6, 9, 35, 0)
    start_time = datetime(2026, 2, 6, 9, 30, 0)

    return {
        "scenario": "market_open",
        "timestamp": timestamp.isoformat(),
        "symbols": {
            "SPY": {
                "currentPrice": 688.50,
                "historicalBars": generate_historical_bars(
                    base_price=689.00,  # Gapped down from close
                    start_time=start_time,
                    num_bars=30,  # First 30 minutes
                    trend="down",
                    volume_profile="high",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=688.50,
                    expiry_date="2026-02-07",
                    iv_level=18.0,
                    spread_width=0.20,  # Wider during open
                ),
            },
            "QQQ": {
                "currentPrice": 620.80,
                "historicalBars": generate_historical_bars(
                    base_price=621.50,
                    start_time=start_time,
                    num_bars=30,
                    trend="down",
                    volume_profile="high",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=620.80,
                    expiry_date="2026-02-07",
                    iv_level=20.0,
                    spread_width=0.25,
                ),
            },
            "IWM": {
                "currentPrice": 215.00,
                "historicalBars": generate_historical_bars(
                    base_price=215.40,
                    start_time=start_time,
                    num_bars=30,
                    trend="sideways",
                    volume_profile="normal",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=215.00,
                    expiry_date="2026-02-07",
                    iv_level=19.0,
                    spread_width=0.18,
                ),
            },
        },
    }


def create_scenario_5_end_of_day() -> Dict[str, Any]:
    """Scenario 5: End of day closing activity."""
    timestamp = datetime(2026, 2, 6, 15, 50, 0)
    start_time = datetime(2026, 2, 6, 15, 45, 0)

    return {
        "scenario": "end_of_day",
        "timestamp": timestamp.isoformat(),
        "symbols": {
            "SPY": {
                "currentPrice": 689.80,
                "historicalBars": generate_historical_bars(
                    base_price=689.50,
                    start_time=start_time,
                    num_bars=15,  # Last 15 minutes
                    trend="sideways",
                    volume_profile="low",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=689.80,
                    expiry_date="2026-02-06",  # 0 DTE
                    iv_level=25.0,  # Elevated for 0DTE
                    spread_width=0.35,  # Wide spreads on 0DTE
                ),
            },
            "QQQ": {
                "currentPrice": 621.90,
                "historicalBars": generate_historical_bars(
                    base_price=621.70,
                    start_time=start_time,
                    num_bars=15,
                    trend="up",
                    volume_profile="low",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=621.90,
                    expiry_date="2026-02-06",
                    iv_level=28.0,
                    spread_width=0.40,
                ),
            },
            "IWM": {
                "currentPrice": 215.60,
                "historicalBars": generate_historical_bars(
                    base_price=215.50,
                    start_time=start_time,
                    num_bars=15,
                    trend="sideways",
                    volume_profile="low",
                ),
                "optionChain": generate_option_chain(
                    underlying_price=215.60,
                    expiry_date="2026-02-06",
                    iv_level=30.0,
                    spread_width=0.45,
                ),
            },
        },
    }


def main() -> None:
    """Generate all mock snapshot scenarios."""
    output_dir = Path("tests/fixtures/ibkr_snapshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        ("snapshot_normal_market.json", create_scenario_1_normal_market()),
        ("snapshot_high_volatility.json", create_scenario_2_high_volatility()),
        ("snapshot_low_volatility.json", create_scenario_3_low_volatility()),
        ("snapshot_market_open.json", create_scenario_4_market_open()),
        ("snapshot_end_of_day.json", create_scenario_5_end_of_day()),
    ]

    for filename, data in scenarios:
        filepath = output_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Created: {filepath}")

    print(f"\n✅ Generated {len(scenarios)} mock snapshot scenarios")
    print(f"📁 Location: {output_dir}")


if __name__ == "__main__":
    main()
