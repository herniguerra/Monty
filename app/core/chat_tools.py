"""
Monty Chat Tools
Function definitions for Gemini's native function calling.
These tools allow Monty to take actions during a conversation.
"""
from typing import Any, Dict, List, Optional
from google.genai import types


# Tool definitions for Gemini function calling
MONTY_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_price",
                description="Get the current price and 24h change for a cryptocurrency symbol",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "symbol": types.Schema(
                            type=types.Type.STRING,
                            description="Trading pair symbol, e.g., 'BTC/USDT', 'ETH/USDT', 'SOL/USDT'"
                        )
                    },
                    required=["symbol"]
                )
            ),
            types.FunctionDeclaration(
                name="get_portfolio",
                description="Get the current portfolio state including cash, positions, total value, and P&L",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="get_market_overview",
                description="Get an overview of the current market conditions for the watchlist (BTC, ETH, SOL)",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="analyze_news_sentiment",
                description="Analyze current crypto news and return sentiment (BULLISH/BEARISH/NEUTRAL)",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="propose_trade",
                description="Create a trade proposal for user approval. Does NOT execute immediately.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "symbol": types.Schema(
                            type=types.Type.STRING,
                            description="Trading pair symbol, e.g., 'BTC/USDT'"
                        ),
                        "action": types.Schema(
                            type=types.Type.STRING,
                            description="Trade action: 'BUY' or 'SELL'"
                        ),
                        "reason": types.Schema(
                            type=types.Type.STRING,
                            description="Reason for this trade proposal"
                        ),
                        "allocation_pct": types.Schema(
                            type=types.Type.NUMBER,
                            description="Percentage of portfolio to allocate (1-10%)"
                        )
                    },
                    required=["symbol", "action", "reason"]
                )
            ),
            types.FunctionDeclaration(
                name="execute_approved_trade",
                description="Execute a trade that has already been approved by the user. Requires trade_id.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "trade_id": types.Schema(
                            type=types.Type.INTEGER,
                            description="ID of the approved trade to execute"
                        )
                    },
                    required=["trade_id"]
                )
            ),
            types.FunctionDeclaration(
                name="get_pending_trades",
                description="Get all pending trade proposals awaiting user approval",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="get_trade_history",
                description="Get recent trade history",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "limit": types.Schema(
                            type=types.Type.INTEGER,
                            description="Number of recent trades to return (default 10)"
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="get_trading_playbook",
                description="Get detailed trading guidance from the playbook. Use this when you need in-depth knowledge about trading strategies, risk management, entry timing, or market psychology. Sections: strategy_selection, risk_management, entry_timing, market_cycles, psychology, decision_framework, or 'all' for full playbook.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "section": types.Schema(
                            type=types.Type.STRING,
                            description="Section to retrieve: 'strategy_selection', 'risk_management', 'entry_timing', 'market_cycles', 'psychology', 'decision_framework', or 'all'"
                        )
                    }
                )
            )
        ]
    )
]


class ToolExecutor:
    """
    Executes tool calls made by the LLM.
    """
    
    def __init__(self):
        from app.services.price_sensor import PriceSensor
        from app.services.news_sensor import NewsSensor
        from app.core.scheduler_jobs import get_paper_engine, get_strategist
        
        self.price_sensor = PriceSensor()
        self.news_sensor = NewsSensor()
        self._get_paper_engine = get_paper_engine
        self._get_strategist = get_strategist

    def execute(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call and return the result.
        """
        try:
            if function_name == "get_price":
                return self._get_price(args.get("symbol", "BTC/USDT"))
            elif function_name == "get_portfolio":
                return self._get_portfolio()
            elif function_name == "get_market_overview":
                return self._get_market_overview()
            elif function_name == "analyze_news_sentiment":
                return self._analyze_sentiment()
            elif function_name == "propose_trade":
                return self._propose_trade(args)
            elif function_name == "execute_approved_trade":
                return self._execute_trade(args.get("trade_id"))
            elif function_name == "get_pending_trades":
                return self._get_pending_trades()
            elif function_name == "get_trade_history":
                return self._get_trade_history(args.get("limit", 10))
            elif function_name == "get_trading_playbook":
                return self._get_playbook(args.get("section", "all"))
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            return {"error": str(e)}

    def _get_price(self, symbol: str) -> Dict[str, Any]:
        data = self.price_sensor.get_price(symbol)
        if data:
            return {
                "symbol": data.symbol,
                "price": data.price,
                "change_24h": f"{data.change_24h:+.2f}%",
                "volume_24h": data.volume_24h
            }
        return {"error": f"Could not fetch price for {symbol}"}

    def _get_portfolio(self) -> Dict[str, Any]:
        try:
            engine = self._get_paper_engine()
            return engine.get_portfolio_summary()
        except:
            return {
                "cash": 10000.0,
                "positions": {},
                "total_value": 10000.0,
                "pnl": 0.0,
                "pnl_pct": 0.0
            }

    def _get_market_overview(self) -> Dict[str, Any]:
        watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        prices = self.price_sensor.get_multiple_prices(watchlist)
        return {
            symbol: {
                "price": f"${data.price:,.2f}",
                "change_24h": f"{data.change_24h:+.2f}%"
            }
            for symbol, data in prices.items()
        }

    def _analyze_sentiment(self) -> Dict[str, Any]:
        try:
            news = self.news_sensor.get_crypto_news(limit=5)
            headlines = [item.title for item in news]
            
            if not headlines:
                return {"sentiment": "NEUTRAL", "confidence": 0.0, "message": "No recent news found"}
            
            strategist = self._get_strategist()
            sentiment = strategist.gemini.analyze_sentiment(headlines)
            return sentiment
        except Exception as e:
            return {"sentiment": "NEUTRAL", "confidence": 0.0, "error": str(e)}

    def _propose_trade(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.agents.proposals import TradeProposal, ProposalManager
        from app.models import Trade
        from app.extensions import db
        
        symbol = args.get("symbol", "BTC/USDT")
        action = args.get("action", "HOLD")
        reason = args.get("reason", "User requested trade")
        allocation = args.get("allocation_pct", 3.0)
        
        # Get current price
        price_data = self.price_sensor.get_price(symbol)
        current_price = price_data.price if price_data else 0
        
        # Create trade in database
        trade = Trade(
            symbol=symbol,
            action=action,
            price=current_price,
            quantity=0,
            status="PENDING",
            strategy="chat_request",
            reasoning=reason
        )
        db.session.add(trade)
        db.session.commit()
        
        return {
            "status": "proposed",
            "trade_id": trade.id,
            "message": f"Trade proposal created: {action} {symbol} at ${current_price:,.2f}. Awaiting your approval."
        }

    def _get_pending_trades(self) -> Dict[str, Any]:
        from app.models import Trade
        trades = Trade.query.filter_by(status="PENDING").all()
        return {
            "pending_count": len(trades),
            "trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "action": t.action,
                    "price": t.price,
                    "reason": t.reasoning
                }
                for t in trades
            ]
        }

    def _get_trade_history(self, limit: int) -> Dict[str, Any]:
        try:
            engine = self._get_paper_engine()
            history = engine.trade_history[-limit:] if engine.trade_history else []
            return {
                "count": len(history),
                "trades": [
                    {
                        "symbol": t.symbol,
                        "action": t.action,
                        "price": t.price,
                        "quantity": t.quantity,
                        "pnl": t.pnl
                    }
                    for t in history
                ]
            }
        except:
            return {"count": 0, "trades": []}

    def _execute_trade(self, trade_id: int) -> Dict[str, Any]:
        """
        Execute a pending trade via the paper trading engine.
        """
        from app.models import Trade
        from app.extensions import db
        
        if not trade_id:
            return {"error": "No trade_id provided"}
        
        # Find the pending trade
        trade = Trade.query.filter_by(id=trade_id, status="PENDING").first()
        if not trade:
            return {"error": f"No pending trade found with ID {trade_id}"}
        
        try:
            engine = self._get_paper_engine()
            portfolio = engine.get_portfolio_summary()
            
            # Calculate quantity based on 5% allocation (or use stored allocation)
            allocation_pct = 5.0  # Default 5%
            cash = portfolio.get('cash', 0)
            
            if trade.action == "BUY":
                # Get current price
                price_data = self.price_sensor.get_price(trade.symbol)
                if not price_data:
                    return {"error": f"Could not get current price for {trade.symbol}"}
                
                current_price = price_data.price
                allocation_amount = cash * (allocation_pct / 100)
                quantity = allocation_amount / current_price
                
                # Execute buy
                result = engine.execute_buy(
                    symbol=trade.symbol,
                    current_price=current_price,
                    allocation_pct=allocation_pct
                )
                success = result is not None
                
                if success:
                    trade.status = "EXECUTED"
                    trade.quantity = quantity
                    trade.price = current_price
                    db.session.commit()
                    
                    return {
                        "status": "executed",
                        "trade_id": trade.id,
                        "action": "BUY",
                        "symbol": trade.symbol,
                        "quantity": quantity,
                        "price": current_price,
                        "total_cost": quantity * current_price,
                        "message": f"Successfully bought {quantity:.6f} {trade.symbol.split('/')[0]} at ${current_price:,.2f}"
                    }
                else:
                    return {"error": "Insufficient funds for this trade"}
                    
            elif trade.action == "SELL":
                # Get current price
                price_data = self.price_sensor.get_price(trade.symbol)
                if not price_data:
                    return {"error": f"Could not get current price for {trade.symbol}"}
                
                current_price = price_data.price
                
                # Check if we have this position
                positions = portfolio.get('positions', {})
                if trade.symbol not in positions:
                    return {"error": f"No position in {trade.symbol} to sell"}
                
                position = positions[trade.symbol]
                quantity = position.get('quantity', 0)
                
                # Execute sell (100% of position)
                result = engine.execute_sell(
                    symbol=trade.symbol,
                    current_price=current_price,
                    sell_pct=100.0
                )
                success = result is not None
                
                if success:
                    trade.status = "EXECUTED"
                    trade.quantity = quantity
                    trade.price = current_price
                    db.session.commit()
                    
                    return {
                        "status": "executed",
                        "trade_id": trade.id,
                        "action": "SELL",
                        "symbol": trade.symbol,
                        "quantity": quantity,
                        "price": current_price,
                        "total_proceeds": quantity * current_price,
                        "message": f"Successfully sold {quantity:.6f} {trade.symbol.split('/')[0]} at ${current_price:,.2f}"
                    }
                else:
                    return {"error": "Failed to execute sell"}
            else:
                return {"error": f"Unknown action: {trade.action}"}
                
        except Exception as e:
            return {"error": f"Execution failed: {str(e)}"}

    def _get_playbook(self, section: str = "all") -> Dict[str, Any]:
        """
        Get trading playbook content, optionally filtered by section.
        """
        import os
        
        # Load the playbook file
        playbook_path = os.path.join(
            os.path.dirname(__file__), 
            'trading_playbook.md'
        )
        
        try:
            with open(playbook_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            return {"error": "Trading playbook not found"}
        
        # Section mappings (header text in the markdown)
        section_map = {
            "strategy_selection": "## 1. STRATEGY SELECTION",
            "risk_management": "## 2. RISK MANAGEMENT",
            "entry_timing": "## 3. ENTRY TIMING",
            "market_cycles": "## 4. CRYPTO-SPECIFIC KNOWLEDGE",
            "psychology": "## 5. PSYCHOLOGY & DISCIPLINE",
            "decision_framework": "## 7. PRACTICAL DECISION FRAMEWORK",
            "push_back": "## 6. WHEN MONTY SHOULD PUSH BACK",
        }
        
        if section == "all" or section not in section_map:
            return {
                "section": "full_playbook",
                "content": content,
                "available_sections": list(section_map.keys())
            }
        
        # Extract specific section
        section_start = section_map[section]
        start_idx = content.find(section_start)
        
        if start_idx == -1:
            return {"error": f"Section '{section}' not found in playbook"}
        
        # Find next section (or end of file)
        next_section_idx = len(content)
        for header in section_map.values():
            idx = content.find(header, start_idx + len(section_start))
            if idx != -1 and idx < next_section_idx:
                next_section_idx = idx
        
        section_content = content[start_idx:next_section_idx].strip()
        
        return {
            "section": section,
            "content": section_content,
            "available_sections": list(section_map.keys())
        }
