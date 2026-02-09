"""
Unit tests for MarketDataPipeline.

Tests marker data fetching, indicator calculation, and quality validation.
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.integrations.market_data_pipeline import (
    MarketDataPipeline,
    IndicatorSet,
    InsufficientDataError,
    AlphaLearningViolationError,
)


@pytest.fixture
def mock_market_data_provider():
    """Mock MarketDataProvider with snapshot=True enforcement."""
    provider = MagicMock()
    provider.request_market_data = MagicMock(
        return_value={
            "symbol": "SPY",
            "last": 450.0,
            "bid": 449.95,
            "ask": 450.05,
            "volume": 1000000,
            "timestamp": datetime.now(timezone.utc),
        }
    )
    provider.request_historical_data = MagicMock(
        return_value=[
            {
                "open": 450.0 + i * 0.1,
                "high": 451.0 + i * 0.1,
                "low": 449.0 + i * 0.1,
                "close": 450.0 + i * 0.1,
                "volume": 10000,
            }
            for i in range(60)
        ]
    )
    provider.contract_manager = MagicMock()
    provider.contract_manager.qualify_contract = MagicMock(return_value=MagicMock(symbol="SPY"))
    return provider


@pytest.fixture
def pipeline(mock_market_data_provider):
    """MarketDataPipeline instance with mocked provider."""
    return MarketDataPipeline(mock_market_data_provider, staleness_threshold_seconds=300.0)


class TestMarketDataPipeline:
    """Test MarketDataPipeline functionality."""

    @pytest.mark.asyncio
    async def test_fetch_market_data_success(self, pipeline, mock_market_data_provider):
        """Test successful market data fetch with indicators."""
        market_data = await pipeline.fetch_market_data("SPY", timeout=30.0)

        assert market_data.symbol == "SPY"
        assert market_data.last_price == 450.0
        assert market_data.bid == 449.95
        assert market_data.ask == 450.05
        assert market_data.volume == 1000000
        assert market_data.ema_fast > 0
        assert market_data.ema_slow > 0
        assert 0 <= market_data.rsi <= 100
        assert market_data.vwap > 0
        assert not market_data.is_stale
        assert market_data.data_quality_score > 0.5

    @pytest.mark.asyncio
    async def test_alpha_learning_1_hour_limit_enforced(self, pipeline):
        """Test that historical data >60 minutes is rejected (alpha learning)."""
        with pytest.raises(AlphaLearningViolationError) as exc_info:
            await pipeline.fetch_historical_data("SPY", duration_minutes=120, timeout=30.0)

        assert "1-hour limit" in str(exc_info.value)
        assert "60 minutes" in str(exc_info.value) or "1-hour" in str(exc_info.value)

    def test_calculate_ema_success(self, pipeline):
        """Test EMA calculation."""
        prices = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0])
        ema = pipeline._calculate_ema(prices, period=8)

        assert isinstance(ema, float)
        assert ema > 100.0
        assert ema < 110.0

    def test_calculate_ema_insufficient_data(self, pipeline):
        """Test EMA calculation fails with insufficient data."""
        prices = np.array([100.0, 101.0, 102.0])

        with pytest.raises(InsufficientDataError):
            pipeline._calculate_ema(prices, period=8)

    def test_calculate_rsi_success(self, pipeline):
        """Test RSI calculation."""
        # Create price series with upward trend
        prices = np.array([100.0 + i for i in range(20)])
        rsi = pipeline._calculate_rsi(prices, period=14)

        assert isinstance(rsi, float)
        assert 0 <= rsi <= 100
        assert rsi > 50  # Upward trend should have RSI > 50

    def test_calculate_rsi_insufficient_data(self, pipeline):
        """Test RSI calculation fails with insufficient data."""
        prices = np.array([100.0, 101.0, 102.0])

        with pytest.raises(InsufficientDataError):
            pipeline._calculate_rsi(prices, period=14)

    def test_calculate_vwap_success(self, pipeline):
        """Test VWAP calculation."""
        closes = np.array([100.0, 101.0, 102.0, 103.0, 104.0])
        highs = np.array([101.0, 102.0, 103.0, 104.0, 105.0])
        lows = np.array([99.0, 100.0, 101.0, 102.0, 103.0])
        volumes = np.array([10000, 10000, 10000, 10000, 10000])

        vwap = pipeline._calculate_vwap(closes, highs, lows, volumes)

        assert isinstance(vwap, float)
        assert 99.0 <= vwap <= 105.0

    def test_calculate_bollinger_success(self, pipeline):
        """Test Bollinger Band calculation."""
        prices = np.array([100.0 + i * 0.5 for i in range(30)])
        upper, lower, middle = pipeline._calculate_bollinger(prices, period=20, std=2)

        assert isinstance(upper, float)
        assert isinstance(lower, float)
        assert isinstance(middle, float)
        assert upper > middle > lower

    def test_calculate_bollinger_insufficient_data(self, pipeline):
        """Test Bollinger calculation fails with insufficient data."""
        prices = np.array([100.0, 101.0, 102.0])

        with pytest.raises(InsufficientDataError):
            pipeline._calculate_bollinger(prices, period=20)

    def test_validate_data_quality_fresh_complete(self, pipeline):
        """Test data quality validation with fresh complete data."""
        quote = {
            "last": 450.0,
            "bid": 449.95,
            "ask": 450.05,
            "volume": 1000000,
            "timestamp": datetime.now(timezone.utc),
        }
        indicators = IndicatorSet(
            ema_fast=450.0,
            ema_slow=449.0,
            rsi=55.0,
            vwap=450.0,
            bollinger_upper=455.0,
            bollinger_lower=445.0,
            bollinger_middle=450.0,
        )

        quality = pipeline._validate_data_quality(quote, indicators)

        assert not quality.is_stale
        assert quality.staleness_seconds < 5.0
        assert len(quality.missing_fields) == 0
        assert quality.score == 1.0

    def test_validate_data_quality_stale_data(self, pipeline):
        """Test data quality validation detects stale data."""
        stale_timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)
        quote = {
            "last": 450.0,
            "bid": 449.95,
            "ask": 450.05,
            "volume": 1000000,
            "timestamp": stale_timestamp,
        }
        indicators = IndicatorSet(
            ema_fast=450.0,
            ema_slow=449.0,
            rsi=55.0,
            vwap=450.0,
            bollinger_upper=455.0,
            bollinger_lower=445.0,
            bollinger_middle=450.0,
        )

        quality = pipeline._validate_data_quality(quote, indicators)

        assert quality.is_stale
        assert quality.staleness_seconds > 300.0
        assert quality.score < 1.0

    def test_validate_data_quality_missing_fields(self, pipeline):
        """Test data quality validation detects missing fields."""
        quote = {
            "last": 450.0,
            "bid": 0,  # Missing bid
            "ask": 0,  # Missing ask
            "volume": 0,  # Missing volume
            "timestamp": datetime.now(timezone.utc),
        }
        indicators = IndicatorSet(
            ema_fast=450.0,
            ema_slow=449.0,
            rsi=55.0,
            vwap=450.0,
            bollinger_upper=455.0,
            bollinger_lower=445.0,
            bollinger_middle=450.0,
        )

        quality = pipeline._validate_data_quality(quote, indicators)

        assert not quality.is_stale
        assert "bid" in quality.missing_fields
        assert "ask" in quality.missing_fields
        assert "volume" in quality.missing_fields
        assert quality.score < 1.0

    def test_calculate_indicators_insufficient_bars(self, pipeline):
        """Test indicator calculation fails with insufficient bars."""
        bars = [
            {"close": 100.0 + i, "high": 101.0, "low": 99.0, "volume": 10000} for i in range(10)
        ]

        with pytest.raises(InsufficientDataError) as exc_info:
            pipeline._calculate_indicators(bars)

        assert "21 bars" in str(exc_info.value)
