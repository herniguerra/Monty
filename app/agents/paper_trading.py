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
    Now persists to database for state preservation across restarts.
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[ExecutedTrade] = []
        self.start_time = datetime.utcnow()
        
        # Try to load state from database
        self._load_from_db()
    
    def _load_from_db(self):
        """Load portfolio state from database."""
        try:
            from app.models import Position as PositionModel, PortfolioState, ExecutedTrade as TradeModel
            from app.extensions import db
            
            # Load portfolio state
            state = PortfolioState.query.first()
            if state:
                self.cash_balance = state.cash_balance
                self.initial_balance = state.initial_balance
                self.start_time = state.start_time
                print(f"[PaperTrading] Loaded portfolio: ${self.cash_balance:,.2f} cash")
            
            # Load positions
            db_positions = PositionModel.query.all()
            for p in db_positions:
                self.positions[p.symbol] = Position(
                    symbol=p.symbol,
                    entry_price=p.entry_price,
                    quantity=p.quantity,
                    side=p.side,
                    entry_time=p.entry_time,
                    stop_loss=p.stop_loss,
                    take_profit=p.take_profit
                )
            if db_positions:
                print(f"[PaperTrading] Loaded {len(db_positions)} positions")
            
            # Load trade history
            db_trades = TradeModel.query.order_by(TradeModel.timestamp.desc()).limit(50).all()
            for t in db_trades:
                self.trade_history.append(ExecutedTrade(
                    symbol=t.symbol,
                    action=t.action,
                    price=t.price,
                    quantity=t.quantity,
                    value=t.value,
                    timestamp=t.timestamp,
                    pnl=t.pnl
                ))
            if db_trades:
                print(f"[PaperTrading] Loaded {len(db_trades)} trade history")
                
        except Exception as e:
            print(f"[PaperTrading] DB load skipped (first run?): {e}")
    
    def _save_to_db(self):
        """Save portfolio state to database."""
        try:
            from app.models import Position as PositionModel, PortfolioState, ExecutedTrade as TradeModel
            from app.extensions import db
            
            # Save portfolio state
            state = PortfolioState.query.first()
            if state:
                state.cash_balance = self.cash_balance
            else:
                state = PortfolioState(
                    cash_balance=self.cash_balance,
                    initial_balance=self.initial_balance,
                    start_time=self.start_time
                )
                db.session.add(state)
            
            # Sync positions
            PositionModel.query.delete()
            for symbol, pos in self.positions.items():
                db_pos = PositionModel(
                    symbol=symbol,
                    entry_price=pos.entry_price,
                    quantity=pos.quantity,
                    side=pos.side,
                    entry_time=pos.entry_time,
                    stop_loss=pos.stop_loss,
                    take_profit=pos.take_profit
                )
                db.session.add(db_pos)
            
            db.session.commit()
        except Exception as e:
            print(f"[PaperTrading] DB save failed: {e}")

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
        """Get a summary of the current portfolio with real-time prices."""
        # Fetch current prices for all positions
        positions_with_pnl = {}
        total_position_value = 0
        total_unrealized_pnl = 0
        
        for symbol, pos in self.positions.items():
            try:
                from app.services.price_sensor import PriceSensor
                price_sensor = PriceSensor()
                price_data = price_sensor.get_price(symbol)
                current_price = price_data.price if price_data else pos.entry_price
            except:
                current_price = pos.entry_price
            
            current_value = pos.quantity * current_price
            entry_value = pos.quantity * pos.entry_price
            position_pnl = current_value - entry_value
            position_pnl_pct = ((current_price - pos.entry_price) / pos.entry_price * 100) if pos.entry_price else 0
            
            total_position_value += current_value
            total_unrealized_pnl += position_pnl
            
            positions_with_pnl[symbol] = {
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': current_price,
                'value': current_value,
                'pnl': position_pnl,
                'pnl_pct': position_pnl_pct,
                'stop_loss': pos.stop_loss,
                'take_profit': pos.take_profit
            }
        
        total_value = self.cash_balance + total_position_value
        total_pnl = total_value - self.initial_balance
        total_pnl_pct = (total_pnl / self.initial_balance * 100) if self.initial_balance else 0
        
        return {
            'cash': self.cash_balance,
            'positions': positions_with_pnl,
            'total_value': total_value,
            'pnl': total_pnl,
            'pnl_pct': total_pnl_pct,
            'unrealized_pnl': total_unrealized_pnl,
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
        self._save_to_db()
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
        self._save_to_db()
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
