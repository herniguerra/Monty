from app.web import bp
from flask import jsonify, render_template, request


# Simple in-memory portfolio state (doesn't require Strategist initialization)
_portfolio_state = {
    'cash': 10000.0,
    'positions': {},
    'total_value': 10000.0,
    'pnl': 0.0,
    'pnl_pct': 0.0,
    'trade_count': 0,
    'runtime_hours': 0
}


@bp.route('/')
def index():
    """Serve the main dashboard."""
    return render_template('index.html')


@bp.route('/health')
def health():
    return jsonify({"status": "healthy"})


@bp.route('/api/portfolio')
def get_portfolio():
    """Get current portfolio state."""
    try:
        from app.core.scheduler_jobs import get_paper_engine
        engine = get_paper_engine()
        summary = engine.get_portfolio_summary()
        # Update our cached state
        _portfolio_state.update(summary)
        return jsonify(summary)
    except Exception as e:
        print(f"[API] Portfolio error: {e}")
        # Return cached/default state
        return jsonify(_portfolio_state)


@bp.route('/api/scan', methods=['POST'])
def trigger_scan():
    """Manually trigger a market scan."""
    try:
        from app.core.scheduler_jobs import get_strategist, get_paper_engine
        strategist = get_strategist()
        engine = get_paper_engine()
        
        portfolio = engine.get_portfolio_summary()
        proposals = strategist.scan_and_propose(portfolio)
        
        return jsonify({
            'status': 'success',
            'proposals_count': len(proposals) if proposals else 0,
            'proposals': [p.to_dict() for p in proposals] if proposals else []
        })
    except Exception as e:
        print(f"[API] Scan error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e),
            'proposals_count': 0,
            'proposals': []
        })


@bp.route('/api/trades/pending')
def get_pending_trades():
    """Get all pending trade proposals."""
    from app.agents.proposals import ProposalManager
    try:
        manager = ProposalManager()
        trades = manager.get_pending_proposals()
        return jsonify([{
            'id': t.id,
            'symbol': t.symbol,
            'action': t.action,
            'price': t.price,
            'status': t.status,
            'strategy': t.strategy,
            'reasoning': t.reasoning
        } for t in trades])
    except Exception as e:
        return jsonify([])


@bp.route('/api/trades/<int:trade_id>/approve', methods=['POST'])
def approve_trade(trade_id):
    """Approve a pending trade."""
    from app.agents.proposals import ProposalManager
    manager = ProposalManager()
    trade = manager.approve_proposal(trade_id)
    if trade:
        return jsonify({'status': 'approved', 'trade_id': trade.id})
    return jsonify({'status': 'error', 'message': 'Trade not found'}), 404


@bp.route('/api/trades/<int:trade_id>/reject', methods=['POST'])
def reject_trade(trade_id):
    """Reject a pending trade."""
    from app.agents.proposals import ProposalManager
    manager = ProposalManager()
    trade = manager.reject_proposal(trade_id)
    if trade:
        return jsonify({'status': 'rejected', 'trade_id': trade.id})
    return jsonify({'status': 'error', 'message': 'Trade not found'}), 404


@bp.route('/api/trades/pending')
def get_pending_trades():
    """Get all pending trades with expiration info."""
    from app.models import Trade
    from datetime import datetime
    
    # First, expire any old pending trades
    expired = Trade.query.filter_by(status='PENDING').all()
    for trade in expired:
        if trade.is_expired:
            trade.status = 'EXPIRED'
    from app.extensions import db
    db.session.commit()
    
    # Get current pending trades
    pending = Trade.query.filter_by(status='PENDING').all()
    return jsonify({
        'trades': [
            {
                'id': t.id,
                'symbol': t.symbol,
                'action': t.action,
                'price': t.price,
                'strategy': t.strategy,
                'reasoning': t.reasoning,
                'time_remaining_mins': t.time_remaining(),
                'created_at': t.created_at.isoformat() if t.created_at else None
            }
            for t in pending
        ],
        'count': len(pending)
    })


@bp.route('/api/trades/reject-all', methods=['POST'])
def reject_all_trades():
    """Reject all pending trades."""
    from app.models import Trade
    from app.extensions import db
    
    pending = Trade.query.filter_by(status='PENDING').all()
    count = len(pending)
    
    for trade in pending:
        trade.status = 'REJECTED'
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'rejected_count': count,
        'message': f'Rejected {count} pending trade(s)'
    })


# ===== CHAT API =====

@bp.route('/api/chat', methods=['POST'])
def chat():
    """Send a message to Monty and get a response."""
    try:
        from app.core.chat_engine import get_chat_engine
        
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        engine = get_chat_engine()
        result = engine.chat(user_message)
        
        return jsonify({
            'response': result.get('response', ''),
            'tool_calls': result.get('tool_calls', []),
            'timestamp': engine.history[-1].timestamp.isoformat() if engine.history else None
        })
    except Exception as e:
        print(f"[API] Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'response': f"Sorry, I encountered an error: {str(e)}",
            'tool_calls': [],
            'error': True
        })


@bp.route('/api/chat/history')
def chat_history():
    """Get chat history."""
    try:
        from app.core.chat_engine import get_chat_engine
        engine = get_chat_engine()
        return jsonify({
            'messages': [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in engine.history
            ]
        })
    except Exception as e:
        return jsonify({'messages': []})


@bp.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    """Clear chat history."""
    try:
        from app.core.chat_engine import get_chat_engine
        engine = get_chat_engine()
        engine.clear_history()
        return jsonify({'status': 'cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/chat/context')
def chat_context():
    """Get Monty's current context for debugging."""
    try:
        from app.core.chat_engine import get_chat_engine, SYSTEM_PROMPT
        from app.core.scheduler_jobs import get_strategist, get_paper_engine
        from app.models import Trade
        
        engine = get_chat_engine()
        
        # Get portfolio
        try:
            paper_engine = get_paper_engine()
            portfolio = paper_engine.get_portfolio_summary()
        except:
            portfolio = {'cash': 10000, 'positions': {}, 'total_value': 10000}
        
        # Get active strategies
        try:
            strategist = get_strategist()
            active_strategies = [
                {'name': s.name, 'description': s.description, 'risk_level': s.risk_level}
                for s in strategist.active_strategies
            ]
        except:
            active_strategies = []
        
        # Get pending trades
        try:
            pending_trades = Trade.query.filter_by(status='PENDING').all()
            pending = [{'id': t.id, 'symbol': t.symbol, 'action': t.action} for t in pending_trades]
        except:
            pending = []
        
        # Get recent trade history
        try:
            recent_trades = Trade.query.order_by(Trade.created_at.desc()).limit(5).all()
            history = [
                {'id': t.id, 'symbol': t.symbol, 'action': t.action, 'status': t.status}
                for t in recent_trades
            ]
        except:
            history = []
        
        return jsonify({
            'system_prompt': SYSTEM_PROMPT,
            'dynamic_context': engine._get_context(),
            'portfolio': portfolio,
            'active_strategies': active_strategies,
            'pending_trades': pending,
            'recent_trades': history,
            'chat_history_length': len(engine.history)
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@bp.route('/api/chat/export', methods=['POST'])
def export_chat():
    """Export chat history to markdown file in chat_logs folder."""
    import os
    from datetime import datetime
    from flask import current_app
    
    try:
        data = request.get_json() or {}
        markdown_content = data.get('markdown', '')
        
        if not markdown_content:
            return jsonify({'error': 'No content to export'}), 400
        
        # Create chat_logs folder if it doesn't exist
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logs_dir = os.path.join(project_root, 'chat_logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'monty-chat-{timestamp}.md'
        filepath = os.path.join(logs_dir, filename)
        
        # Write the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return jsonify({
            'status': 'exported',
            'filename': filename,
            'path': filepath
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
