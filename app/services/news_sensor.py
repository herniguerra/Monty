"""
News Sensor Service
Fetches crypto news headlines for sentiment analysis.
"""
import os
import requests
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published_at: datetime
    description: Optional[str] = None


class NewsSensor:
    """
    Fetches news from various sources.
    Primary: NewsAPI (requires API key)
    Fallback: CryptoPanic (free tier)
    """

    def __init__(self):
        self.newsapi_key = os.environ.get('NEWSAPI_KEY')
        self.cryptopanic_token = os.environ.get('CRYPTOPANIC_TOKEN')

    def get_crypto_news(self, query: str = 'cryptocurrency', limit: int = 10) -> List[NewsItem]:
        """
        Fetch recent news articles related to crypto.
        """
        # Try CryptoPanic first (crypto-specific, free tier available)
        news = self._fetch_cryptopanic(limit)
        if news:
            return news

        # Fallback to NewsAPI if available
        if self.newsapi_key:
            return self._fetch_newsapi(query, limit)

        return []

    def _fetch_cryptopanic(self, limit: int) -> List[NewsItem]:
        """
        Fetch from CryptoPanic API (free tier).
        """
        try:
            url = "https://cryptopanic.com/api/posts/"
            params = {
                'auth_token': self.cryptopanic_token or 'free',
                'public': 'true',
                'filter': 'hot',
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('results', [])[:limit]:
                    results.append(NewsItem(
                        title=item.get('title', ''),
                        source=item.get('source', {}).get('title', 'Unknown'),
                        url=item.get('url', ''),
                        published_at=datetime.fromisoformat(
                            item.get('published_at', '').replace('Z', '+00:00')
                        ) if item.get('published_at') else datetime.utcnow(),
                        description=None
                    ))
                return results
        except Exception as e:
            print(f"[NewsSensor] CryptoPanic error: {e}")
        return []

    def _fetch_newsapi(self, query: str, limit: int) -> List[NewsItem]:
        """
        Fetch from NewsAPI.
        """
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'sortBy': 'publishedAt',
                'pageSize': limit,
                'apiKey': self.newsapi_key
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = []
                for article in data.get('articles', []):
                    results.append(NewsItem(
                        title=article.get('title', ''),
                        source=article.get('source', {}).get('name', 'Unknown'),
                        url=article.get('url', ''),
                        published_at=datetime.fromisoformat(
                            article.get('publishedAt', '').replace('Z', '+00:00')
                        ) if article.get('publishedAt') else datetime.utcnow(),
                        description=article.get('description')
                    ))
                return results
        except Exception as e:
            print(f"[NewsSensor] NewsAPI error: {e}")
        return []
