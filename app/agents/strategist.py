"""
The Strategist
Main orchestrator that combines signals from all strategies,
runs the Bull/Bear debate, and generates final trade proposals.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.agents.strategies import (
    BaseStrategy, StrategySignal, Signal,
    RSIDipStrategy, SentimentSurgeStrategy, MoonshotScannerStrategy,
    SwingTrendStrategy, STRATEGY_REGISTRY
)
from app.agents.proposals import TradeProposal, ProposalManager
from app.core.gemini_client import GeminiClient
from app.services.price_sensor import PriceSensor, PriceData
from app.services.news_sensor import NewsSensor


@dataclass
class StrategyConfig:
    """Configuration for a strategy instance."""
    strategy_id: str
    enabled: bool = True
    risk_override: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class Strategist:
    """
    The main brain of Monty.
    Orchestrates data gathering, strategy execution, and proposal generation.
    """
    
    def __init__(self):
        self.gemini = GeminiClient()
        self.price_sensor = PriceSensor()
        self.news_sensor = NewsSensor()
        self.proposal_manager = ProposalManager()
        
        # Default watchlist
        self.watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        # Active strategies with their configs
        self.active_strategies: List[BaseStrategy] = [
            RSIDipStrategy(),
            SentimentSurgeStrategy(),
            SwingTrendStrategy(),  # New: trend-following pullback entries
        ]
        
        # Global settings
        self.max_allocation_per_trade = 5.0  # Max 5% per trade
        self.min_confidence_threshold = 0.6  # Minimum confidence to propose

    def add_strategy(self, strategy: BaseStrategy):
        """Add a strategy to the active list."""
        self.active_strategies.append(strategy)

    def remove_strategy(self, strategy_name: str):
        """Remove a strategy by name."""
        self.active_strategies = [s for s in self.active_strategies if s.name != strategy_name]

    def gather_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Gather all relevant data for a symbol.
        """
        # Get current price
        price_data = self.price_sensor.get_price(symbol)
        
        # Get OHLCV for technical analysis
        ohlcv = self.price_sensor.get_ohlcv(symbol, timeframe='1h', limit=50)
        
        return {
            'symbol': symbol,
            'current_price': price_data.price if price_data else 0,
            'change_24h': price_data.change_24h if price_data else 0,
            'volume_24h': price_data.volume_24h if price_data else 0,
            'ohlcv': ohlcv
        }

    def gather_sentiment_data(self) -> Dict[str, Any]:
        """
        Gather and analyze news sentiment.
        """
        news = self.news_sensor.get_crypto_news(limit=10)
        if not news:
            return {'sentiment': 'NEUTRAL', 'confidence': 0.0, 'themes': [], 'urgent': False}
        
        headlines = [item.title for item in news]
        
        try:
            sentiment = self.gemini.analyze_sentiment(headlines)
            return sentiment
        except Exception as e:
            print(f"[Strategist] Sentiment analysis failed: {e}")
            return {'sentiment': 'NEUTRAL', 'confidence': 0.0, 'themes': [], 'urgent': False}

    def run_strategies(self, price_data: Dict[str, Any], sentiment_data: Dict[str, Any]) -> List[StrategySignal]:
        """
        Run all active strategies and collect signals.
        """
        signals = []
        
        for strategy in self.active_strategies:
            if not strategy.enabled:
                continue
            
            try:
                signal = strategy.analyze(price_data, sentiment_data)
                if signal:
                    signals.append(signal)
                    print(f"  📊 [{strategy.name}] {signal.signal.value} {signal.symbol} (conf: {signal.confidence:.2f})")
            except Exception as e:
                print(f"  ⚠️ [{strategy.name}] Error: {e}")
        
        return signals

    def debate_and_decide(
        self,
        signals: List[StrategySignal],
        price_data: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        portfolio: Dict[str, float]
    ) -> Optional[TradeProposal]:
        """
        The Bull/Bear Debate.
        Takes strategy signals and uses Gemini to synthesize a final decision.
        """
        if not signals:
            return None
        
        # Aggregate signals
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        sell_signals = [s for s in signals if s.signal == Signal.SELL]
        
        # If conflicting signals, let Gemini decide
        if buy_signals and sell_signals:
            print("  ⚖️ Conflicting signals detected, running debate...")
        
        # Use the strongest signal as primary
        all_signals = buy_signals + sell_signals
        primary_signal = max(all_signals, key=lambda s: s.confidence)
        
        # Generate detailed proposal using Gemini
        try:
            proposal_data = self.gemini.generate_trade_proposal(
                price_data=price_data,
                sentiment_data=sentiment_data,
                portfolio=portfolio,
                risk_level="moderate"
            )
            
            # Build the final proposal
            return TradeProposal(
                symbol=primary_signal.symbol,
                action=proposal_data.get('recommendation', primary_signal.signal.value),
                reasoning=proposal_data.get('reasoning', primary_signal.reasoning),
                confidence=proposal_data.get('confidence', primary_signal.confidence),
                suggested_allocation_pct=min(
                    proposal_data.get('suggested_allocation_pct', 3.0),
                    self.max_allocation_per_trade
                ),
                stop_loss_pct=proposal_data.get('stop_loss_pct'),
                take_profit_pct=proposal_data.get('take_profit_pct'),
                strategy_name=primary_signal.strategy_name,
                bull_case=proposal_data.get('bull_case'),
                bear_case=proposal_data.get('bear_case'),
                current_price=price_data.get('current_price')
            )
            
        except Exception as e:
            print(f"  ⚠️ Gemini proposal generation failed: {e}")
            # Fallback to strategy signal directly
            return TradeProposal(
                symbol=primary_signal.symbol,
                action=primary_signal.signal.value,
                reasoning=primary_signal.reasoning,
                confidence=primary_signal.confidence,
                suggested_allocation_pct=3.0,
                strategy_name=primary_signal.strategy_name,
                current_price=price_data.get('current_price')
            )

    def scan_and_propose(self, portfolio: Optional[Dict[str, float]] = None) -> List[TradeProposal]:
        """
        Main entry point: Scan the market and generate proposals.
        Called by the scheduler every X minutes.
        """
        if portfolio is None:
            portfolio = {'USDT': 10000.0}  # Default paper trading balance
        
        proposals = []
        print(f"\n🔍 Monty is analyzing the market...")
        
        # Get sentiment once (applies to all symbols)
        sentiment_data = self.gather_sentiment_data()
        print(f"  📰 Sentiment: {sentiment_data.get('sentiment')} (conf: {sentiment_data.get('confidence', 0):.2f})")
        
        # Analyze each symbol in watchlist
        for symbol in self.watchlist:
            print(f"\n  📈 Analyzing {symbol}...")
            
            try:
                # Gather data
                price_data = self.gather_market_data(symbol)
                print(f"    Price: ${price_data['current_price']:,.2f} ({price_data['change_24h']:+.2f}%)")
                
                # Run strategies
                signals = self.run_strategies(price_data, sentiment_data)
                
                # If we have signals above threshold, generate proposal
                strong_signals = [s for s in signals if s.confidence >= self.min_confidence_threshold]
                
                if strong_signals:
                    proposal = self.debate_and_decide(strong_signals, price_data, sentiment_data, portfolio)
                    if proposal and proposal.confidence >= self.min_confidence_threshold:
                        proposals.append(proposal)
                        print(f"    ✅ Proposal generated: {proposal.action} {proposal.symbol}")
                        
            except Exception as e:
                print(f"    ❌ Error analyzing {symbol}: {e}")
        
        print(f"\n🎯 Scan complete. {len(proposals)} proposal(s) generated.")
        return proposals
