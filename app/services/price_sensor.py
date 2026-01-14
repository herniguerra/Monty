"""
Price Sensor Service
Fetches real-time and historical price data using CCXT.
"""
import ccxt
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PriceData:
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    timestamp: datetime


class PriceSensor:
    """
    Connects to exchanges via CCXT to fetch price data.
    Tries multiple exchanges for better coverage.
    """

    # Exchanges to try in order of preference
    EXCHANGES = ['binance', 'kraken', 'coinbasepro', 'kucoin', 'gate']

    def __init__(self, exchange_id: str = None):
        self.exchanges = {}
        # Initialize multiple exchanges for fallback
        for ex_id in self.EXCHANGES:
            try:
                self.exchanges[ex_id] = getattr(ccxt, ex_id)({
                    'enableRateLimit': True,
                })
            except Exception:
                pass
        
        # Primary exchange
        self.primary = exchange_id or 'binance'

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to standard format.
        'btc' -> 'BTC/USDT'
        'BTC' -> 'BTC/USDT'
        'BTC/USD' -> 'BTC/USDT'
        """
        symbol = symbol.upper().strip()
        
        # Already has a quote currency
        if '/' in symbol:
            # Normalize common quote currencies
            if symbol.endswith('/USD'):
                symbol = symbol.replace('/USD', '/USDT')
            return symbol
        
        # Just the base currency, add USDT
        return f"{symbol}/USDT"

    def get_price(self, symbol: str = 'BTC/USDT') -> Optional[PriceData]:
        """
        Fetch current ticker data for a symbol.
        Tries multiple exchanges if needed.
        """
        symbol = self._normalize_symbol(symbol)
        
        # Try each exchange
        for ex_id, exchange in self.exchanges.items():
            try:
                ticker = exchange.fetch_ticker(symbol)
                return PriceData(
                    symbol=symbol,
                    price=ticker['last'],
                    volume_24h=ticker.get('quoteVolume', 0),
                    change_24h=ticker.get('percentage', 0),
                    timestamp=datetime.utcnow()
                )
            except Exception as e:
                # Try next exchange
                continue
        
        # All exchanges failed
        print(f"[PriceSensor] Could not fetch {symbol} from any exchange")
        return None

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """
        Fetch prices for multiple symbols.
        """
        results = {}
        for symbol in symbols:
            data = self.get_price(symbol)
            if data:
                results[symbol] = data
        return results

    def get_ohlcv(self, symbol: str = 'BTC/USDT', timeframe: str = '1h', limit: int = 24) -> List[dict]:
        """
        Fetch OHLCV (candlestick) data.
        Returns list of candles: [timestamp, open, high, low, close, volume]
        """
        symbol = self._normalize_symbol(symbol)
        
        for ex_id, exchange in self.exchanges.items():
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                return [
                    {
                        'timestamp': datetime.utcfromtimestamp(candle[0] / 1000),
                        'open': candle[1],
                        'high': candle[2],
                        'low': candle[3],
                        'close': candle[4],
                        'volume': candle[5]
                    }
                    for candle in ohlcv
                ]
            except Exception:
                continue
        
        print(f"[PriceSensor] Could not fetch OHLCV for {symbol}")
        return []
