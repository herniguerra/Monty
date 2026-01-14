"""
Scheduler Jobs
Defines the background tasks that run at intervals.
"""
from app.extensions import db
from app.agents.strategist import Strategist
from app.agents.paper_trading import PaperTradingEngine
from datetime import datetime


# Global instances (initialized on first run)
_strategist = None
_paper_engine = None


def get_strategist():
    global _strategist
    if _strategist is None:
        _strategist = Strategist()
    return _strategist


def get_paper_engine():
    global _paper_engine
    if _paper_engine is None:
        _paper_engine = PaperTradingEngine(initial_balance=10000.0)
    return _paper_engine


def scan_market(app):
    """
    Main heartbeat job. Runs every X minutes.
    1. Scan market with the Strategist
    2. Generate proposals
    3. Log everything
    """
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"[{datetime.utcnow()}] 🎩 Monty waking up...")
        print(f"{'='*60}")

        try:
            strategist = get_strategist()
            paper_engine = get_paper_engine()
            
            # Get current portfolio state for the strategist
            portfolio = paper_engine.get_portfolio_summary()
            print(f"💰 Portfolio: ${portfolio['total_value']:,.2f} (P&L: {portfolio['pnl_pct']:+.2f}%)")
            
            # Run the brain
            proposals = strategist.scan_and_propose(portfolio)
            
            if proposals:
                print(f"\n📋 Proposals generated:")
                for i, proposal in enumerate(proposals, 1):
                    print(f"  {i}. {proposal.action} {proposal.symbol} @ ${proposal.current_price:,.2f}")
                    print(f"     Reason: {proposal.reasoning[:80]}...")
                    print(f"     Confidence: {proposal.confidence:.0%}")
                # TODO: Send to Telegram for approval
            else:
                print(f"\n😴 No strong signals. Monty is watching...")
            
            # Check stop-loss / take-profit on existing positions
            for symbol in list(paper_engine.positions.keys()):
                try:
                    price_data = strategist.price_sensor.get_price(symbol)
                    if price_data:
                        paper_engine.check_stop_loss_take_profit(symbol, price_data.price)
                except Exception as e:
                    print(f"  ⚠️ Error checking SL/TP for {symbol}: {e}")

        except Exception as e:
            print(f"❌ Scan failed: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n[{datetime.utcnow()}] ✅ Scan complete. Next scan in 5 minutes.")
        print(f"{'='*60}\n")


def register_jobs(scheduler, app):
    """
    Register all scheduled jobs.
    """
    # Scan every 5 minutes
    scheduler.add_job(
        id='market_scan',
        func=scan_market,
        args=[app],
        trigger='interval',
        minutes=5,
        replace_existing=True
    )
    print("📅 Scheduled: market_scan (every 5 minutes)")
