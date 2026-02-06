"""
Test data builders for creating complex test objects.

Provides fluent API builders for:
- Option contracts
- Stock contracts
- Orders (market, limit, stop)
- Positions (open, closed)
- Market data (OHLCV, Greeks)

Example:
    contract = ContractBuilder().spy().call().atm().dte(5).build()
    order = OrderBuilder().buy().limit_price(3.50).build()
"""

# TODO: Implement builders in Chunk 4
