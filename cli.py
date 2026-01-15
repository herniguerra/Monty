"""
Monty CLI - Command-line interface for testing and debugging.
Usage: python cli.py <command> [options]
"""
import click
import sys
import os

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_app_context():
    """Get Flask app context for database operations."""
    from app import create_app
    app = create_app()
    return app.app_context()


@click.group()
def cli():
    """Monty Trading Assistant CLI"""
    pass


@cli.command()
def chat():
    """Interactive chat with Monty."""
    click.echo("🎩 Monty CLI Chat")
    click.echo("=" * 50)
    click.echo("Type your messages. Type 'quit' or 'exit' to leave.\n")
    
    with get_app_context():
        from app.core.chat_engine import ChatEngine
        engine = ChatEngine()
        
        while True:
            try:
                user_input = click.prompt("You", prompt_suffix="> ")
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    click.echo("\n👋 Goodbye!")
                    break
                
                if not user_input.strip():
                    continue
                
                click.echo("\n🎩 Monty is thinking...")
                result = engine.chat(user_input)
                
                # Show tool calls
                if result.get('tool_calls'):
                    click.echo("\n📦 Tool Calls:")
                    for tc in result['tool_calls']:
                        click.echo(f"   • {tc['tool']}({tc.get('args', {})})")
                
                # Show response
                click.echo(f"\n🎩 Monty: {result['response']}\n")
                
            except KeyboardInterrupt:
                click.echo("\n\n👋 Goodbye!")
                break
            except Exception as e:
                click.echo(f"\n❌ Error: {e}\n")


@cli.command()
def portfolio():
    """Show current portfolio summary."""
    with get_app_context():
        from app.core.scheduler_jobs import get_paper_engine
        engine = get_paper_engine()
        summary = engine.get_portfolio_summary()
        
        click.echo("\n💰 Portfolio Summary")
        click.echo("=" * 40)
        click.echo(f"Cash:        ${summary['cash']:,.2f}")
        click.echo(f"Total Value: ${summary['total_value']:,.2f}")
        click.echo(f"P&L:         ${summary['pnl']:,.2f} ({summary['pnl_pct']:+.2f}%)")
        click.echo(f"Trades:      {summary['trade_count']}")
        click.echo()


@cli.command()
def positions():
    """List all open positions."""
    with get_app_context():
        from app.core.scheduler_jobs import get_paper_engine
        engine = get_paper_engine()
        
        if not engine.positions:
            click.echo("\n📭 No open positions.\n")
            return
        
        click.echo("\n📊 Open Positions")
        click.echo("=" * 60)
        click.echo(f"{'Symbol':<15} {'Qty':>12} {'Entry':>12} {'Value':>12}")
        click.echo("-" * 60)
        
        for symbol, pos in engine.positions.items():
            value = pos.quantity * pos.entry_price
            click.echo(f"{symbol:<15} {pos.quantity:>12.6f} ${pos.entry_price:>10.2f} ${value:>10.2f}")
        
        click.echo()


@cli.command()
def pending():
    """List pending trade proposals."""
    with get_app_context():
        from app.agents.proposals import ProposalManager
        manager = ProposalManager()
        trades = manager.get_pending_proposals()
        
        if not trades:
            click.echo("\n📭 No pending trades.\n")
            return
        
        click.echo("\n⏳ Pending Trades")
        click.echo("=" * 60)
        
        for trade in trades:
            click.echo(f"  #{trade.id}: {trade.action} {trade.symbol} @ ${trade.price:,.2f}")
            click.echo(f"         Reason: {trade.reasoning[:50]}...")
        
        click.echo()


@cli.command()
@click.argument('trade_id', type=int)
def approve(trade_id):
    """Approve a pending trade."""
    with get_app_context():
        from app.agents.proposals import ProposalManager
        manager = ProposalManager()
        trade = manager.approve_proposal(trade_id)
        
        if trade:
            click.echo(f"\n✅ Trade #{trade_id} approved and executed!")
            click.echo(f"   {trade.action} {trade.symbol} @ ${trade.price:,.2f}")
        else:
            click.echo(f"\n❌ Trade #{trade_id} not found or already processed.")
        click.echo()


@cli.command()
@click.argument('trade_id', type=int)
def reject(trade_id):
    """Reject a pending trade."""
    with get_app_context():
        from app.agents.proposals import ProposalManager
        manager = ProposalManager()
        trade = manager.reject_proposal(trade_id)
        
        if trade:
            click.echo(f"\n🚫 Trade #{trade_id} rejected.")
        else:
            click.echo(f"\n❌ Trade #{trade_id} not found or already processed.")
        click.echo()


@cli.command()
@click.argument('action', type=click.Choice(['buy', 'sell']))
@click.argument('symbol')
@click.option('--allocation', '-a', default=5.0, help='Allocation percentage (default: 5%)')
def trade(action, symbol, allocation):
    """Propose a trade (buy or sell)."""
    # Normalize symbol
    if '/' not in symbol:
        symbol = f"{symbol.upper()}/USDT"
    
    with get_app_context():
        from app.core.chat_engine import ChatEngine
        engine = ChatEngine()
        
        click.echo(f"\n🎩 Requesting Monty to {action.upper()} {symbol}...")
        
        result = engine.chat(f"{action} some {symbol.split('/')[0]}")
        
        if result.get('tool_calls'):
            for tc in result['tool_calls']:
                if tc['tool'] == 'propose_trade':
                    click.echo(f"\n✅ Trade proposed!")
                    if tc.get('result', {}).get('trade_id'):
                        click.echo(f"   Trade ID: {tc['result']['trade_id']}")
                        click.echo(f"   Run 'python cli.py approve {tc['result']['trade_id']}' to execute")
        
        click.echo(f"\n🎩 Monty: {result['response'][:200]}...\n")


if __name__ == '__main__':
    cli()
