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
        
        msg += "\nReply /approve or /reject"
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
        return trade
    
    def get_pending_proposals(self) -> List[Trade]:
        """Get all pending trades from database."""
        return Trade.query.filter_by(status=ProposalStatus.PENDING.value).all()
    
    def approve_proposal(self, trade_id: int) -> Optional[Trade]:
        """Approve a pending trade."""
        trade = Trade.query.get(trade_id)
        if trade and trade.status == ProposalStatus.PENDING.value:
            trade.status = ProposalStatus.APPROVED.value
            db.session.commit()
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
