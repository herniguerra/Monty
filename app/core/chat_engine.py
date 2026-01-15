"""
Monty Chat Engine
Handles conversations with function calling support.
"""
import os
import json
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime

from google import genai
from google.genai import types

from app.core.chat_tools import MONTY_TOOLS, ToolExecutor


MODEL_ID = "gemini-3-pro-preview"

SYSTEM_PROMPT = """You are Monty, a knowledgeable crypto trading assistant. 🎩

## YOUR PERSONALITY
- Warm, approachable, confident but not arrogant
- Explains trading concepts clearly for non-experts
- Has OPINIONS and CONVICTION - you don't just agree with everything
- Honest about uncertainty, but confident about proven principles
- Uses emojis sparingly (not every message)

## YOUR ACTIVE STRATEGY MODULES
You have automated scanners running these strategies:
1. **RSI Dip Strategy** - Mean reversion: buys oversold assets (RSI<30) expecting bounce
2. **Sentiment Surge Strategy** - News-driven: buys when positive news detected
3. **Swing Trend Rider** - Trend-following: buys uptrend pullbacks to moving average support
4. **Moonshot Scanner** - High-risk breakouts: scans for explosive moves (use with caution)

## TRADING KNOWLEDGE (Apply This)

### Strategy Selection for Manual Trades
1. **Momentum (Buy Strength)**: Use in clear uptrends. Buy assets up 3%+ with volume.
   - DON'T use if asset already moved 10%+ ("chasing")
2. **Mean Reversion (Buy Weakness)**: Use in range-bound markets. Buy oversold at support.
   - DON'T fight a clear trend
3. **Rotation/Laggard**: When leaders moved, capital rotates to laggards.
   - ETH-SOL have ~0.8 correlation. If ETH up 5% and SOL only 2%, SOL often catches up.

### Risk Management (ALWAYS APPLY)
- Position size: 3-5% of portfolio per trade (NEVER more than 5% without explicit request)
- Stop-loss: ALWAYS define before entry
- Risk-reward: Minimum 2:1 (potential gain must be 2x potential loss)
- Don't chase: If something moved 10%+, wait for pullback

### Market Cycles (Capital Flow)
BTC → ETH → Layer-1s (SOL, AVAX) → Mid-caps → Meme coins (peak speculation)

## WHEN TO PUSH BACK (Be Opinionated!)

You are the expert. If the user suggests something risky, PUSH BACK politely:

❌ User wants to chase a pump → "That's already up 8% - I'd wait for a pullback. Chasing often means buying the top."
❌ User wants to go all-in → "I'd recommend 5% max. Smaller positions often outperform."
❌ User shows FOMO → "Missing a trade is better than chasing one. Let's find a better setup."
✅ User has a sound idea → Validate it AND add insight: "Good thinking! And to add..."

## CAPABILITIES (Tools)
- get_price, get_portfolio, get_market_overview, analyze_news_sentiment
- propose_trade, execute_approved_trade, get_pending_trades
- get_trading_playbook: Use this to retrieve detailed trading guidance when you need more depth on strategies, risk management, entry timing, or psychology

## RULES
1. NEVER execute trades without explicit user approval
2. When proposing: State entry, stop-loss, target, and WHY
3. Before any proposal: Is R:R ≥ 2:1? Is position size ≤ 5%?
4. If user asks for predictions: "I can analyze, but can't predict. Here's what the data shows..."
5. If user asks detailed strategy questions, use get_trading_playbook to provide expert answers
6. **PROACTIVE RESEARCH**: If user asks for a trade recommendation WITHOUT specifying a coin (e.g., "propose a trade", "find me an opportunity", "what should I buy?"):
   - FIRST call get_market_overview() to see current prices and 24h changes
   - THEN call analyze_news_sentiment() to gauge market mood
   - ANALYZE the data to find the best opportunity based on your strategy knowledge
   - FINALLY propose_trade() with your researched recommendation and explain your reasoning
7. **TRADE ID ACCURACY**: When you call propose_trade(), the tool returns a `trade_id`. ALWAYS use the EXACT trade_id from the tool result when referring to the trade. Never make up or guess trade IDs. If the tool returns an error, inform the user.

Current context will be provided with each message.
"""



@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_calls: Optional[List[Dict]] = None


class ChatEngine:
    """
    Manages a conversation with Monty, including tool calling.
    """
    
    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        self.tool_executor = ToolExecutor()
        self.history: List[ChatMessage] = []
        self.max_history = 20  # Keep last 20 messages for context

    def _get_context(self) -> str:
        """
        Build current context string to inject into the conversation.
        """
        try:
            portfolio = self.tool_executor._get_portfolio()
            context = f"""
Current Portfolio State:
- Total Value: ${portfolio.get('total_value', 10000):,.2f}
- Cash: ${portfolio.get('cash', 10000):,.2f}
- P&L: ${portfolio.get('pnl', 0):,.2f} ({portfolio.get('pnl_pct', 0):+.2f}%)
- Open Positions: {len(portfolio.get('positions', {}))}
- Trades Made: {portfolio.get('trade_count', 0)}

Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""
            return context.strip()
        except Exception as e:
            return f"Context unavailable: {e}"

    def _build_messages(self, user_message: str) -> List[types.Content]:
        """
        Build the message list for the API call.
        """
        messages = []
        
        # System context
        context = self._get_context()
        system_content = f"{SYSTEM_PROMPT}\n\n--- CURRENT CONTEXT ---\n{context}"
        
        # Add conversation history (last N messages)
        for msg in self.history[-self.max_history:]:
            messages.append(types.Content(
                role="user" if msg.role == "user" else "model",
                parts=[types.Part(text=msg.content)]
            ))
        
        # Add current user message with system context prepended to first message
        if not messages:
            # First message - include system prompt
            messages.append(types.Content(
                role="user",
                parts=[types.Part(text=f"{system_content}\n\nUser: {user_message}")]
            ))
        else:
            messages.append(types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            ))
        
        return messages

    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Send a message to Monty and get a response.
        Handles tool calling automatically.
        Returns dict with 'response' and 'tool_calls'.
        """
        # Add user message to history
        self.history.append(ChatMessage(role="user", content=user_message))
        
        # Build messages
        messages = self._build_messages(user_message)
        
        # Track tool calls for visibility
        tool_calls_made = []
        
        # Initial API call with tools
        try:
            response = self.client.models.generate_content(
                model=MODEL_ID,
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=MONTY_TOOLS,
                    temperature=0.7
                )
            )
        except Exception as e:
            error_msg = f"Sorry, I'm having trouble connecting right now. Error: {e}"
            self.history.append(ChatMessage(role="assistant", content=error_msg))
            return {"response": error_msg, "tool_calls": []}
        
        # Handle tool calls if any
        max_tool_iterations = 5
        iteration = 0
        
        while iteration < max_tool_iterations:
            iteration += 1
            
            # Check if response has function calls
            if not response.candidates or not response.candidates[0].content.parts:
                break
            
            parts = response.candidates[0].content.parts
            function_calls = [p for p in parts if hasattr(p, 'function_call') and p.function_call]
            
            if not function_calls:
                # No more function calls, we have the final response
                break
            
            # Execute each function call
            tool_results = []
            for part in function_calls:
                fc = part.function_call
                func_name = fc.name
                func_args = dict(fc.args) if fc.args else {}
                
                print(f"[Chat] Calling tool: {func_name}({func_args})")
                result = self.tool_executor.execute(func_name, func_args)
                
                # Track for UI visibility
                tool_calls_made.append({
                    "tool": func_name,
                    "args": func_args,
                    "result": result,  # Full result for API
                    "result_preview": str(result)[:200]  # Truncated for UI
                })
                
                tool_results.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=func_name,
                        response=result
                    )
                ))
            
            # Add function results and continue conversation
            messages.append(types.Content(role="model", parts=parts))
            messages.append(types.Content(role="user", parts=tool_results))
            
            # Get next response
            try:
                response = self.client.models.generate_content(
                    model=MODEL_ID,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        tools=MONTY_TOOLS,
                        temperature=0.7
                    )
                )
            except Exception as e:
                error_msg = f"Error during tool processing: {e}"
                self.history.append(ChatMessage(role="assistant", content=error_msg))
                return {"response": error_msg, "tool_calls": tool_calls_made}
        
        # Extract final text response
        final_text = ""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    final_text += part.text
        
        if not final_text:
            final_text = "I processed your request but don't have a response to show."
        
        # Add to history
        self.history.append(ChatMessage(role="assistant", content=final_text, tool_calls=tool_calls_made))
        
        return {"response": final_text, "tool_calls": tool_calls_made}

    def chat_stream(self, user_message: str) -> Generator[Dict[str, Any], None, None]:
        """
        Stream response tokens as they arrive.
        Yields dicts:
          {"type": "text", "delta": "..."}
          {"type": "tool_call", "tool": "...", "args": {...}}
          {"type": "tool_result", "tool": "...", "result": {...}}
          {"type": "done", "full_response": "...", "tool_calls": [...]}
        """
        # Add user message to history
        self.history.append(ChatMessage(role="user", content=user_message))
        
        # Build messages
        messages = self._build_messages(user_message)
        
        # Track tool calls and full response for final yield
        tool_calls_made = []
        full_response = ""
        
        max_tool_iterations = 5
        iteration = 0
        
        while iteration < max_tool_iterations:
            iteration += 1
            
            try:
                # Use streaming API
                stream = self.client.models.generate_content_stream(
                    model=MODEL_ID,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        tools=MONTY_TOOLS,
                        temperature=0.7
                    )
                )
            except Exception as e:
                error_msg = f"Sorry, I'm having trouble connecting right now. Error: {e}"
                self.history.append(ChatMessage(role="assistant", content=error_msg))
                yield {"type": "text", "delta": error_msg}
                yield {"type": "done", "full_response": error_msg, "tool_calls": []}
                return
            
            # Collect chunks and detect function calls
            collected_parts = []
            text_in_this_stream = ""
            
            for chunk in stream:
                if not chunk.candidates or not chunk.candidates[0].content.parts:
                    continue
                
                for part in chunk.candidates[0].content.parts:
                    collected_parts.append(part)
                    
                    # Stream text immediately
                    if hasattr(part, 'text') and part.text:
                        yield {"type": "text", "delta": part.text}
                        text_in_this_stream += part.text
                        full_response += part.text
            
            # Check if there were function calls in this stream
            function_calls = [p for p in collected_parts 
                              if hasattr(p, 'function_call') and p.function_call]
            
            if not function_calls:
                # No function calls, we're done streaming
                break
            
            # Execute function calls
            tool_results = []
            for part in function_calls:
                fc = part.function_call
                func_name = fc.name
                func_args = dict(fc.args) if fc.args else {}
                
                # Notify about tool call
                yield {"type": "tool_call", "tool": func_name, "args": func_args}
                
                print(f"[Chat Stream] Calling tool: {func_name}({func_args})")
                result = self.tool_executor.execute(func_name, func_args)
                
                # Notify about result
                yield {"type": "tool_result", "tool": func_name, "result": result}
                
                tool_calls_made.append({
                    "tool": func_name,
                    "args": func_args,
                    "result": result,
                    "result_preview": str(result)[:200]
                })
                
                tool_results.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=func_name,
                        response=result
                    )
                ))
            
            # Add function call parts and results to messages, continue loop
            messages.append(types.Content(role="model", parts=collected_parts))
            messages.append(types.Content(role="user", parts=tool_results))
        
        # Ensure we have some response
        if not full_response:
            full_response = "I processed your request but don't have a response to show."
            yield {"type": "text", "delta": full_response}
        
        # Add to history
        self.history.append(ChatMessage(role="assistant", content=full_response, tool_calls=tool_calls_made))
        
        # Final done event
        yield {"type": "done", "full_response": full_response, "tool_calls": tool_calls_made}

    def clear_history(self):
        """Clear conversation history."""
        self.history = []

    def add_message(self, role: str, content: str):
        """Add a message to history (for injecting user actions like approve/reject)."""
        self.history.append(ChatMessage(role=role, content=content))


# Global chat engine instance
_chat_engine = None

def get_chat_engine() -> ChatEngine:
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = ChatEngine()
    return _chat_engine
