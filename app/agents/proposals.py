"""
Trade Proposal System
Generates, stores, and manages trade proposals for user approval.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from app.extensions import db
from app.models import Trade


class ProposalStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXECUTED = "EXECUTED"


@dataclass
class TradeProposal:
    """A proposed trade awaiting user approval."""
    symbol: str
    action: str  # BUY or SELL
    reasoning: str
    confidence: float
    suggested_allocation_pct: float
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    strategy_name: Optional[str] = None
    bull_case: Optional[str] = None
    bear_case: Optional[str] = None
    current_price: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_telegram_message(self) -> str:
        """Format for Telegram notification."""
        emoji = "🟢" if self.action == "BUY" else "🔴" if self.action == "SELL" else "⚪"
        
        msg = f"""
{emoji} **{self.action} {self.symbol}**

💡 **Why?** {self.reasoning}

📊 **Confidence:** {self.confidence:.0%}
💰 **Suggested Size:** {self.suggested_allocation_pct:.1f}% of portfolio
"""
        if self.stop_loss_pct:
            msg += f"🛑 **Stop Loss:** -{self.stop_loss_pct:.1f}%\n"
        if self.take_profit_pct:
            msg += f"🎯 **Take Profit:** +{self.take_profit_pct:.1f}%\n"
        
        if self.bull_case and self.bear_case:
            msg += f"""
📈 **Bull Case:** {self.bull_case}
📉 **Bear Case:** {self.bear_case}
"""
        
        msg += "\n_Use the buttons below to approve or reject_"
        return msg.strip()


class ProposalManager:
    """
    Manages trade proposals - creation, storage, and lifecycle.
    """
    
    def __init__(self):
        self.pending_proposals: List[TradeProposal] = []
    
    def create_proposal(self, proposal: TradeProposal) -> Trade:
        """
        Create a new trade proposal and save to database.
        """
        trade = Trade(
            symbol=proposal.symbol,
            action=proposal.action,
            price=proposal.current_price or 0.0,
            quantity=0.0,  # Will be calculated on approval based on allocation
            status=ProposalStatus.PENDING.value,
            strategy=proposal.strategy_name,
            reasoning=proposal.reasoning
        )
        
        db.session.add(trade)
        db.session.commit()
        
        self.pending_proposals.append(proposal)
        
        # Notify Telegram and inject into chat history (inject-on-notify pattern)
        self._notify_telegram(proposal, trade.id)
        
        return trade
    
    def _notify_telegram(self, proposal: TradeProposal, trade_id: int):
        """
        Send Telegram notification and inject into ChatEngine history.
        This ensures users can ask follow-up questions like "why?" naturally.
        """
        try:
            from app.telegram.bot import get_telegram_bot
            from app.core.chat_engine import get_chat_engine
            
            # Format the message
            message = proposal.to_telegram_message()
            
            # 1. Send Telegram notification with inline buttons
            bot = get_telegram_bot()
            if bot:
                bot.send_proposal_notification(message, trade_id)
            
            # 2. Inject into ChatEngine history so Monty knows what was proposed
            engine = get_chat_engine()
            if engine:
                engine.add_message("assistant", f"🚨 I just proposed a trade:\n\n{message}")
                
        except Exception as e:
            print(f"[Telegram] Notification error: {e}")

    
    def get_pending_proposals(self) -> List[Trade]:
        """Get all pending trades from database."""
        return Trade.query.filter_by(status=ProposalStatus.PENDING.value).all()
    
    def approve_proposal(self, trade_id: int) -> Optional[Trade]:
        """Approve a pending trade and execute it."""
        trade = Trade.query.get(trade_id)
        if trade and trade.status == ProposalStatus.PENDING.value:
            trade.status = ProposalStatus.APPROVED.value
            db.session.commit()
            
            # Execute the trade via paper trading engine
            try:
                from app.core.scheduler_jobs import get_paper_engine
                from app.services.price_sensor import PriceSensor
                
                engine = get_paper_engine()
                price_sensor = PriceSensor()
                
                # Get current price
                price_data = price_sensor.get_price(trade.symbol)
                current_price = price_data.price if price_data else trade.price
                
                if trade.action == 'BUY':
                    # execute_buy takes: symbol, current_price, allocation_pct (5 = 5%)
                    result = engine.execute_buy(
                        symbol=trade.symbol,
                        current_price=current_price,
                        allocation_pct=5  # 5% of portfolio
                    )
                    # Returns ExecutedTrade object or None
                    if result:
                        trade.status = ProposalStatus.EXECUTED.value
                        trade.quantity = result.quantity
                        trade.price = current_price
                        db.session.commit()
                        print(f"[Trade] Executed BUY {trade.symbol}: {trade.quantity:.6f} @ ${current_price:.2f}")
                elif trade.action == 'SELL':
                    # execute_sell takes: symbol, current_price, sell_pct (default 100)
                    result = engine.execute_sell(
                        symbol=trade.symbol,
                        current_price=current_price,
                        sell_pct=100
                    )
                    if result:
                        trade.status = ProposalStatus.EXECUTED.value
                        trade.quantity = result.quantity
                        trade.price = current_price
                        db.session.commit()
                        print(f"[Trade] Executed SELL {trade.symbol}: {trade.quantity:.6f} @ ${current_price:.2f}")
            except Exception as e:
                print(f"[Trade] Execution error: {e}")
                import traceback
                traceback.print_exc()
            
            return trade
        return None
    
    def reject_proposal(self, trade_id: int) -> Optional[Trade]:
        """Reject a pending trade."""
        trade = Trade.query.get(trade_id)
        if trade and trade.status == ProposalStatus.PENDING.value:
            trade.status = ProposalStatus.REJECTED.value
            db.session.commit()
            return trade
        return None
