from app.extensions import db
from datetime import datetime, timedelta

def default_expires_at():
    return datetime.utcnow() + timedelta(minutes=30)

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    action = db.Column(db.String(10), nullable=False) # BUY / SELL
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=default_expires_at)  # Auto-expire after 30 min
    status = db.Column(db.String(20), default='PENDING') # PENDING, APPROVED, EXECUTED, REJECTED, EXPIRED
    strategy = db.Column(db.String(50))
    reasoning = db.Column(db.Text)
    
    @property
    def is_expired(self):
        """Check if this trade proposal has expired."""
        if self.status != 'PENDING':
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False
    
    def time_remaining(self):
        """Get time remaining before expiration in minutes."""
        if not self.expires_at or self.status != 'PENDING':
            return None
        remaining = self.expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds() / 60))

    def __repr__(self):
        return f'<Trade {self.action} {self.symbol} @ {self.price}>'


class Position(db.Model):
    """Persisted open position in the paper trading portfolio."""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, unique=True)
    entry_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    side = db.Column(db.String(10), default='LONG')  # LONG or SHORT
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    stop_loss = db.Column(db.Float, nullable=True)
    take_profit = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return f'<Position {self.side} {self.symbol} x{self.quantity:.6f}>'


class ExecutedTrade(db.Model):
    """Persisted record of an executed trade."""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(10), nullable=False)  # BUY or SELL
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    pnl = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<ExecutedTrade {self.action} {self.symbol} @ {self.price}>'


class PortfolioState(db.Model):
    """Persisted portfolio state (cash balance, initial balance)."""
    id = db.Column(db.Integer, primary_key=True)
    cash_balance = db.Column(db.Float, nullable=False, default=10000.0)
    initial_balance = db.Column(db.Float, nullable=False, default=10000.0)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PortfolioState cash=${self.cash_balance:.2f}>'


class Settings(db.Model):
    """Global application settings."""
    id = db.Column(db.Integer, primary_key=True)
    scan_interval_minutes = db.Column(db.Integer, nullable=False, default=5)
    initial_balance = db.Column(db.Float, nullable=False, default=10000.0)
    trade_expiry_minutes = db.Column(db.Integer, nullable=False, default=30)
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings row."""
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def __repr__(self):
        return f'<Settings scan={self.scan_interval_minutes}min, balance=${self.initial_balance}>'
