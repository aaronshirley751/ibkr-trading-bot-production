#!/usr/bin/env python3
"""Snapshot structure validation script.

This script validates the structure and completeness of captured IBKR snapshots.
Can be used to verify snapshot files after capture during market hours.
"""

import json
import sys
from pathlib import Path


def validate_snapshot_file(snapshot_path: Path) -> bool:
    """Validate snapshot file structure and content.

    Args:
        snapshot_path: Path to snapshot JSON file

    Returns:
        True if validation passes, False otherwise
    """
    if not snapshot_path.exists():
        print(f"❌ File not found: {snapshot_path}")
        return False

    try:
        with open(snapshot_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False

    print("Snapshot Validation Report:")
    print("=" * 60)
    print(f"Scenario: {data.get('scenario', 'MISSING')}")
    print(f"Timestamp: {data.get('timestamp', 'MISSING')}")

    if "symbols" not in data:
        print("❌ Missing 'symbols' key")
        return False

    print(f"Symbols: {list(data['symbols'].keys())}")
    print()

    all_valid = True

    for symbol, sym_data in data["symbols"].items():
        print(f"{symbol}:")

        # Check current price
        current_price = sym_data.get("currentPrice", 0)
        if current_price == 0:
            print("  ❌ Missing or zero current price")
            all_valid = False
        else:
            print(f"  ✓ Current Price: ${current_price:.2f}")

        # Check historical bars
        hist_bars = sym_data.get("historicalBars", [])
        if len(hist_bars) < 20:
            print(f"  ⚠ Low historical bars: {len(hist_bars)} (expected 20+)")
            all_valid = False
        else:
            print(f"  ✓ Historical Bars: {len(hist_bars)}")

        # Check option chain
        option_chain = sym_data.get("optionChain", [])
        if len(option_chain) < 10:
            print(f"  ⚠ Low option data: {len(option_chain)} (expected 10+)")
            all_valid = False
        else:
            print(f"  ✓ Option Contracts: {len(option_chain)}")

        # Check Greeks presence (can be nested or direct properties)
        options_with_greeks = sum(
            1
            for opt in option_chain
            if (opt.get("greeks") and opt["greeks"].get("delta") is not None)
            or (opt.get("delta") is not None)
        )
        print(
            f"  {'✓' if options_with_greeks > 0 else '⚠'} Options with Greeks: {options_with_greeks}/{len(option_chain)}"
        )

        if options_with_greeks == 0 and len(option_chain) > 0:
            all_valid = False

        print()

    if all_valid:
        print("✅ Snapshot structure validated - all checks passed")
        return True
    else:
        print("⚠ Snapshot has warnings - review issues above")
        return False


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_snapshot.py <snapshot_file.json>")
        print("\nExamples:")
        print(
            "  python validate_snapshot.py tests/fixtures/ibkr_snapshots/snapshot_normal_latest.json"
        )
        print(
            "  python validate_snapshot.py tests/fixtures/ibkr_snapshots/snapshot_validation_test_latest.json"
        )
        sys.exit(1)

    snapshot_path = Path(sys.argv[1])
    success = validate_snapshot_file(snapshot_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
