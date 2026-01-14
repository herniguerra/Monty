"""
Gemini Client
Direct interface to Gemini 3 Pro Preview API.
No LangChain — just the google-genai SDK.
"""
import os
from google import genai
from google.genai import types
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# The one and only model we use
MODEL_ID = "gemini-3-pro-preview"


class GeminiClient:
    """
    Wrapper around the Gemini API for Monty's intelligence layer.
    """

    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        self.client = genai.Client(api_key=api_key)

    def analyze_sentiment(self, headlines: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment of news headlines.
        Returns structured sentiment data.
        """
        prompt = f"""You are a crypto market sentiment analyst. Analyze the following headlines and provide:
1. Overall sentiment: BULLISH, BEARISH, or NEUTRAL
2. Confidence: 0.0 to 1.0
3. Key themes detected
4. Any urgent signals (regulatory news, hacks, major announcements)

Headlines:
{chr(10).join(f'- {h}' for h in headlines)}

Respond in JSON format:
{{
    "sentiment": "BULLISH|BEARISH|NEUTRAL",
    "confidence": 0.0-1.0,
    "themes": ["theme1", "theme2"],
    "urgent": true|false,
    "summary": "Brief summary of market mood"
}}"""

        response = self.client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
        )
        
        # Parse the JSON response
        import json
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "sentiment": "NEUTRAL",
                "confidence": 0.5,
                "themes": [],
                "urgent": False,
                "summary": "Could not parse sentiment"
            }

    def generate_trade_proposal(
        self,
        price_data: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        portfolio: Dict[str, float],
        risk_level: str = "moderate"
    ) -> Dict[str, Any]:
        """
        The Strategist: Generate a trade proposal based on market conditions.
        Uses internal "debate" to weigh bull vs bear case.
        """
        prompt = f"""You are Monty, a friendly crypto trading assistant. You help users make informed decisions.

Current Market Data:
{price_data}

Sentiment Analysis:
{sentiment_data}

Current Portfolio:
{portfolio}

Risk Level: {risk_level}

Your task:
1. First, argue the BULL case (why we should buy)
2. Then, argue the BEAR case (why we should sell or hold)
3. Weigh both sides and make a final recommendation

Respond in JSON format:
{{
    "bull_case": "Brief bull argument",
    "bear_case": "Brief bear argument",
    "recommendation": "BUY|SELL|HOLD",
    "symbol": "BTC/USDT",
    "confidence": 0.0-1.0,
    "reasoning": "Plain English explanation for the user",
    "suggested_allocation_pct": 0-100,
    "stop_loss_pct": 0-100,
    "take_profit_pct": 0-100
}}

Remember: Be helpful but honest. If uncertain, recommend HOLD."""

        response = self.client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json"
            )
        )
        
        import json
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "recommendation": "HOLD",
                "confidence": 0.0,
                "reasoning": "Could not generate proposal"
            }

    def chat(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Simple chat interface for user questions.
        """
        system_context = """You are Monty, a friendly crypto trading assistant. 
You help users understand the market in simple terms. 
You never give financial advice, only information and analysis.
Keep responses concise and accessible to non-traders."""

        if context:
            system_context += f"\n\nCurrent context:\n{context}"

        response = self.client.models.generate_content(
            model=MODEL_ID,
            contents=[
                types.Content(role="user", parts=[types.Part(text=system_context)]),
                types.Content(role="user", parts=[types.Part(text=user_message)])
            ],
            config=types.GenerateContentConfig(
                temperature=0.7
            )
        )
        
        return response.text
