"""
Strategy Modules
Each strategy is a self-contained unit that can be toggled on/off.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategySignal:
    """Output from a strategy module."""
    strategy_name: str
    signal: Signal
    symbol: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    metadata: Optional[Dict[str, Any]] = None


class BaseStrategy(ABC):
    """
    Base class for all strategy modules.
    Each strategy takes market data and returns a signal.
    """
    
    name: str = "BaseStrategy"
    description: str = "Base strategy class"
    enabled: bool = True
    
    # Strategy-specific settings (can be overridden per-strategy)
    risk_level: str = "moderate"  # conservative, moderate, aggressive
    time_horizon: str = "swing"   # scalp, swing, position

    @abstractmethod
    def analyze(self, price_data: Dict[str, Any], sentiment_data: Optional[Dict[str, Any]] = None) -> Optional[StrategySignal]:
        """
        Run the strategy analysis.
        Returns a StrategySignal if conditions are met, None otherwise.
        """
        pass


class RSIDipStrategy(BaseStrategy):
    """
    RSI Oversold/Overbought Strategy.
    Buy when RSI < 30 (oversold), Sell when RSI > 70 (overbought).
    """
    
    name = "RSI Dip Buyer"
    description = "Buys when RSI indicates oversold conditions"
    
    def __init__(self, oversold_threshold: int = 30, overbought_threshold: int = 70):
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold

    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI from closing prices."""
        if len(closes) < period + 1:
            return 50.0  # Neutral if not enough data
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def analyze(self, price_data: Dict[str, Any], sentiment_data: Optional[Dict[str, Any]] = None) -> Optional[StrategySignal]:
        """Analyze using RSI."""
        # Expect price_data to have 'ohlcv' with closing prices
        ohlcv = price_data.get('ohlcv', [])
        symbol = price_data.get('symbol', 'UNKNOWN')
        
        if not ohlcv or len(ohlcv) < 15:
            return None
        
        closes = [candle['close'] for candle in ohlcv]
        rsi = self._calculate_rsi(closes)
        
        if rsi < self.oversold_threshold:
            return StrategySignal(
                strategy_name=self.name,
                signal=Signal.BUY,
                symbol=symbol,
                confidence=min(0.9, (self.oversold_threshold - rsi) / self.oversold_threshold + 0.5),
                reasoning=f"RSI at {rsi:.1f} indicates oversold conditions. Potential bounce incoming.",
                metadata={"rsi": rsi}
            )
        elif rsi > self.overbought_threshold:
            return StrategySignal(
                strategy_name=self.name,
                signal=Signal.SELL,
                symbol=symbol,
                confidence=min(0.9, (rsi - self.overbought_threshold) / (100 - self.overbought_threshold) + 0.5),
                reasoning=f"RSI at {rsi:.1f} indicates overbought conditions. Consider taking profits.",
                metadata={"rsi": rsi}
            )
        
        return None  # No signal


class SentimentSurgeStrategy(BaseStrategy):
    """
    Sentiment-based Strategy.
    Acts on strong sentiment signals from news analysis.
    """
    
    name = "Sentiment Surfer"
    description = "Trades based on news sentiment shifts"
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold

    def analyze(self, price_data: Dict[str, Any], sentiment_data: Optional[Dict[str, Any]] = None) -> Optional[StrategySignal]:
        """Analyze sentiment data."""
        if not sentiment_data:
            return None
        
        sentiment = sentiment_data.get('sentiment', 'NEUTRAL')
        confidence = sentiment_data.get('confidence', 0.0)
        symbol = price_data.get('symbol', 'BTC/USDT')
        
        if confidence < self.confidence_threshold:
            return None
        
        if sentiment == 'BULLISH':
            return StrategySignal(
                strategy_name=self.name,
                signal=Signal.BUY,
                symbol=symbol,
                confidence=confidence,
                reasoning=f"Strong bullish sentiment detected: {sentiment_data.get('summary', 'Positive news flow')}",
                metadata={"themes": sentiment_data.get('themes', [])}
            )
        elif sentiment == 'BEARISH':
            return StrategySignal(
                strategy_name=self.name,
                signal=Signal.SELL,
                symbol=symbol,
                confidence=confidence,
                reasoning=f"Strong bearish sentiment detected: {sentiment_data.get('summary', 'Negative news flow')}",
                metadata={"themes": sentiment_data.get('themes', [])}
            )
        
        return None


class MoonshotScannerStrategy(BaseStrategy):
    """
    Low-cap opportunity scanner.
    Looks for unusual volume + price action on smaller coins.
    HIGH RISK - use small allocations.
    """
    
    name = "Moonshot Scanner"
    description = "Scans for breakout opportunities in smaller caps"
    risk_level = "aggressive"
    
    def __init__(self, volume_spike_threshold: float = 2.0, price_change_threshold: float = 5.0):
        self.volume_spike_threshold = volume_spike_threshold  # 2x normal volume
        self.price_change_threshold = price_change_threshold  # 5% move

    def analyze(self, price_data: Dict[str, Any], sentiment_data: Optional[Dict[str, Any]] = None) -> Optional[StrategySignal]:
        """Look for unusual activity."""
        symbol = price_data.get('symbol', 'UNKNOWN')
        change_24h = price_data.get('change_24h', 0)
        volume_ratio = price_data.get('volume_ratio', 1.0)  # current vs average
        
        # Check for breakout conditions
        if change_24h > self.price_change_threshold and volume_ratio > self.volume_spike_threshold:
            return StrategySignal(
                strategy_name=self.name,
                signal=Signal.BUY,
                symbol=symbol,
                confidence=0.6,  # Lower confidence for moonshots
                reasoning=f"🚀 Potential breakout: {symbol} up {change_24h:.1f}% with {volume_ratio:.1f}x volume. HIGH RISK.",
                metadata={"change_24h": change_24h, "volume_ratio": volume_ratio}
            )
        
        return None


class SwingTrendStrategy(BaseStrategy):
    """
    Swing Trading Strategy.
    Looks for assets in uptrend that have pulled back to support.
    
    Entry conditions:
    1. Price above 20-period MA (uptrend)
    2. Price pulled back near the MA (within 2%)
    3. Recent candle shows bounce (close > open)
    
    This is a trend-following strategy with pullback entries.
    """
    
    name = "Swing Trend Rider"
    description = "Buys uptrend pullbacks to moving average support"
    risk_level = "moderate"
    time_horizon = "swing"
    
    def __init__(self, ma_period: int = 20, pullback_threshold: float = 2.0):
        self.ma_period = ma_period
        self.pullback_threshold = pullback_threshold  # % distance from MA to consider "at support"

    def _calculate_sma(self, closes: List[float], period: int) -> float:
        """Calculate simple moving average."""
        if len(closes) < period:
            return 0.0
        return sum(closes[-period:]) / period

    def _is_uptrend(self, closes: List[float]) -> bool:
        """Check if price is in uptrend (above MA and MA is rising)."""
        if len(closes) < self.ma_period + 5:
            return False
        
        current_ma = self._calculate_sma(closes, self.ma_period)
        previous_ma = self._calculate_sma(closes[:-5], self.ma_period)
        current_price = closes[-1]
        
        # Uptrend: price above MA AND MA is rising
        return current_price > current_ma and current_ma > previous_ma

    def _is_at_support(self, closes: List[float]) -> tuple[bool, float]:
        """Check if price has pulled back to MA support."""
        if len(closes) < self.ma_period:
            return False, 0.0
        
        current_ma = self._calculate_sma(closes, self.ma_period)
        current_price = closes[-1]
        
        # Calculate distance from MA as percentage
        distance_pct = ((current_price - current_ma) / current_ma) * 100
        
        # At support if within threshold% of MA
        return 0 <= distance_pct <= self.pullback_threshold, distance_pct

    def _has_bounce(self, ohlcv: List[Dict]) -> bool:
        """Check if the most recent candle shows a bounce (bullish)."""
        if len(ohlcv) < 2:
            return False
        
        latest = ohlcv[-1]
        previous = ohlcv[-2]
        
        # Bounce conditions:
        # 1. Green candle (close > open)
        # 2. Higher low than previous candle
        # 3. Close in upper half of candle range
        is_green = latest['close'] > latest['open']
        higher_low = latest['low'] > previous['low']
        
        candle_range = latest['high'] - latest['low']
        if candle_range == 0:
            return is_green
        
        close_position = (latest['close'] - latest['low']) / candle_range
        strong_close = close_position > 0.5
        
        return is_green and higher_low and strong_close

    def analyze(self, price_data: Dict[str, Any], sentiment_data: Optional[Dict[str, Any]] = None) -> Optional[StrategySignal]:
        """Analyze for swing trade setup."""
        ohlcv = price_data.get('ohlcv', [])
        symbol = price_data.get('symbol', 'UNKNOWN')
        
        if not ohlcv or len(ohlcv) < self.ma_period + 5:
            return None
        
        closes = [candle['close'] for candle in ohlcv]
        
        # Check all conditions
        is_uptrend = self._is_uptrend(closes)
        at_support, distance = self._is_at_support(closes)
        has_bounce = self._has_bounce(ohlcv)
        
        # All three conditions must be met
        if is_uptrend and at_support and has_bounce:
            ma_value = self._calculate_sma(closes, self.ma_period)
            current_price = closes[-1]
            
            # Confidence based on how cleanly conditions are met
            confidence = 0.65
            if distance < 1.0:  # Very close to MA = higher confidence
                confidence = 0.75
            
            return StrategySignal(
                strategy_name=self.name,
                signal=Signal.BUY,
                symbol=symbol,
                confidence=confidence,
                reasoning=f"Swing setup: {symbol} in uptrend, pulled back {distance:.1f}% to {self.ma_period}-MA (${ma_value:,.2f}), showing bounce. Entry near support.",
                metadata={
                    "ma_period": self.ma_period,
                    "ma_value": ma_value,
                    "current_price": current_price,
                    "distance_from_ma_pct": distance,
                    "suggested_stop": ma_value * 0.97,  # 3% below MA
                    "suggested_target": current_price * 1.06  # 6% target (2:1 R:R)
                }
            )
        
        return None


# Registry of all available strategies
STRATEGY_REGISTRY = {
    "rsi_dip": RSIDipStrategy,
    "sentiment_surge": SentimentSurgeStrategy,
    "moonshot_scanner": MoonshotScannerStrategy,
    "swing_trend": SwingTrendStrategy,
}
