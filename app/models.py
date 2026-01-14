from app.extensions import db
from datetime import datetime, timedelta

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    action = db.Column(db.String(10), nullable=False) # BUY / SELL
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # When this proposal expires
    status = db.Column(db.String(20), default='PENDING') # PENDING, APPROVED, EXECUTED, REJECTED, EXPIRED
    strategy = db.Column(db.String(50))
    reasoning = db.Column(db.Text)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set expiration to 30 minutes from creation by default
        if not self.expires_at and not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.expires_at:
            self.expires_at = (self.created_at or datetime.utcnow()) + timedelta(minutes=30)
    
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
