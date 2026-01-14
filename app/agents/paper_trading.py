"""
Paper Trading Engine
Simulates trade execution for testing without real money.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

from app.agents.proposals import TradeProposal


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


@dataclass
class Position:
    """Represents an open position."""
    symbol: str
    entry_price: float
    quantity: float
    side: str  # LONG or SHORT
    entry_time: datetime = field(default_factory=datetime.utcnow)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class ExecutedTrade:
    """Record of an executed trade."""
    symbol: str
    action: str  # BUY or SELL
    price: float
    quantity: float
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pnl: float = 0.0


class PaperTradingEngine:
    """
    Simulates trading without real money.
    Tracks portfolio, positions, and calculates P&L.
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[ExecutedTrade] = []
        self.start_time = datetime.utcnow()

    @property
    def total_value(self) -> float:
        """Calculate total portfolio value."""
        # For now, just return cash (positions need current prices to value)
        return self.cash_balance + sum(
            pos.quantity * pos.entry_price for pos in self.positions.values()
        )

    @property
    def total_pnl(self) -> float:
        """Calculate total P&L."""
        return self.total_value - self.initial_balance

    @property
    def total_pnl_pct(self) -> float:
        """Calculate total P&L percentage."""
        return (self.total_pnl / self.initial_balance) * 100

    def get_portfolio_summary(self) -> Dict:
        """Get a summary of the current portfolio."""
        return {
            'cash': self.cash_balance,
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'value': pos.quantity * pos.entry_price,
                    'stop_loss': pos.stop_loss,
                    'take_profit': pos.take_profit
                }
                for symbol, pos in self.positions.items()
            },
            'total_value': self.total_value,
            'pnl': self.total_pnl,
            'pnl_pct': self.total_pnl_pct,
            'trade_count': len(self.trade_history),
            'runtime_hours': (datetime.utcnow() - self.start_time).total_seconds() / 3600
        }

    def execute_buy(
        self,
        symbol: str,
        current_price: float,
        allocation_pct: float,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None
    ) -> Optional[ExecutedTrade]:
        """
        Execute a paper buy order.
        """
        # Calculate position size
        allocation_value = self.cash_balance * (allocation_pct / 100)
        quantity = allocation_value / current_price
        
        if allocation_value > self.cash_balance:
            print(f"  ⚠️ Insufficient balance for {symbol}")
            return None
        
        # Deduct from cash
        self.cash_balance -= allocation_value
        
        # Calculate stop loss and take profit prices
        stop_loss_price = current_price * (1 - stop_loss_pct / 100) if stop_loss_pct else None
        take_profit_price = current_price * (1 + take_profit_pct / 100) if take_profit_pct else None
        
        # Add or update position
        if symbol in self.positions:
            # Average into existing position
            existing = self.positions[symbol]
            total_quantity = existing.quantity + quantity
            avg_price = (existing.entry_price * existing.quantity + current_price * quantity) / total_quantity
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=avg_price,
                quantity=total_quantity,
                side="LONG",
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=current_price,
                quantity=quantity,
                side="LONG",
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
        
        # Record trade
        trade = ExecutedTrade(
            symbol=symbol,
            action="BUY",
            price=current_price,
            quantity=quantity,
            value=allocation_value
        )
        self.trade_history.append(trade)
        
        print(f"  📗 Executed: BUY {quantity:.6f} {symbol} @ ${current_price:,.2f} = ${allocation_value:,.2f}")
        return trade

    def execute_sell(
        self,
        symbol: str,
        current_price: float,
        sell_pct: float = 100.0  # Sell percentage of position
    ) -> Optional[ExecutedTrade]:
        """
        Execute a paper sell order.
        """
        if symbol not in self.positions:
            print(f"  ⚠️ No position in {symbol} to sell")
            return None
        
        position = self.positions[symbol]
        sell_quantity = position.quantity * (sell_pct / 100)
        sell_value = sell_quantity * current_price
        
        # Calculate P&L for this trade
        entry_value = sell_quantity * position.entry_price
        pnl = sell_value - entry_value
        
        # Add to cash
        self.cash_balance += sell_value
        
        # Update or remove position
        remaining_quantity = position.quantity - sell_quantity
        if remaining_quantity <= 0:
            del self.positions[symbol]
        else:
            position.quantity = remaining_quantity
        
        # Record trade
        trade = ExecutedTrade(
            symbol=symbol,
            action="SELL",
            price=current_price,
            quantity=sell_quantity,
            value=sell_value,
            pnl=pnl
        )
        self.trade_history.append(trade)
        
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        print(f"  📕 Executed: SELL {sell_quantity:.6f} {symbol} @ ${current_price:,.2f} = ${sell_value:,.2f} (P&L: {pnl_emoji} ${pnl:,.2f})")
        return trade

    def execute_proposal(self, proposal: TradeProposal, current_price: float) -> Optional[ExecutedTrade]:
        """
        Execute a trade proposal.
        """
        if proposal.action == "BUY":
            return self.execute_buy(
                symbol=proposal.symbol,
                current_price=current_price,
                allocation_pct=proposal.suggested_allocation_pct,
                stop_loss_pct=proposal.stop_loss_pct,
                take_profit_pct=proposal.take_profit_pct
            )
        elif proposal.action == "SELL":
            return self.execute_sell(
                symbol=proposal.symbol,
                current_price=current_price
            )
        return None

    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> Optional[ExecutedTrade]:
        """
        Check if stop loss or take profit has been hit.
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # Check stop loss
        if position.stop_loss and current_price <= position.stop_loss:
            print(f"  🛑 Stop loss triggered for {symbol}")
            return self.execute_sell(symbol, current_price)
        
        # Check take profit
        if position.take_profit and current_price >= position.take_profit:
            print(f"  🎯 Take profit triggered for {symbol}")
            return self.execute_sell(symbol, current_price)
        
        return None
