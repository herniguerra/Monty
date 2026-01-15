# 🎩 Monty — AI Crypto Trading Assistant

<p align="center">
  <strong>An LLM-powered, human-in-the-loop cryptocurrency trading platform</strong><br>
  <em>Leveraging Gemini 3 Pro for intelligent market analysis, trade proposals, and portfolio management</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.x-green?logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Gemini_3_Pro-AI%20Engine-purple?logo=google" alt="Gemini">
  <img src="https://img.shields.io/badge/CCXT-Multi--Exchange-orange" alt="CCXT">
  <img src="https://img.shields.io/badge/SQLite-Persistence-gray?logo=sqlite" alt="SQLite">
  <img src="https://img.shields.io/badge/Docker-Ready-blue?logo=docker" alt="Docker">
</p>

---

## Table of Contents

- [Overview](#overview)
- [Core Principles](#core-principles)
- [Architecture](#architecture)
- [Features](#features)
  - [Trading Strategies](#1-automated-trading-strategies)
  - [Paper Trading Engine](#2-paper-trading-engine)
  - [Conversational AI](#3-conversational-ai-chat-interface)
  - [Web Dashboard](#4-web-dashboard)
  - [CLI Tools](#5-command-line-interface-cli)
  - [Market Data Services](#6-market-data-services)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Trading Playbook](#trading-playbook)
- [Development Roadmap](#development-roadmap)
- [Technical Details](#technical-details)
- [License](#license)

---

## Overview

**Monty** is an AI-powered cryptocurrency trading assistant designed for users who want to grow their portfolio without the time commitment of full-time market monitoring. Named after *Monetary* and *Monte Carlo* simulations, Monty acts as an intelligent trading butler—warm, approachable, and confidently opinionated.

Unlike autonomous trading bots, Monty operates on a **human-in-the-loop** model: the AI proposes trades based on market analysis, and you decide whether to execute them. This design philosophy prioritizes explainability, risk management, and user control.

### Key Highlights

- 🤖 **Gemini 3 Pro Integration** — Direct SDK integration with Google's latest LLM for reasoning and function calling
- 📊 **4 Built-in Strategies** — RSI Dip, Sentiment Surge, Moonshot Scanner, and Swing Trend Rider
- 💼 **Paper Trading** — Test strategies with $10,000 virtual capital before going live
- 🔍 **Full Transparency** — Context Debug Panel shows exactly what Monty sees and why
- 🌐 **Multi-Exchange Support** — Real-time prices from Binance, Kraken, Coinbase Pro, KuCoin, and Gate.io
- 📰 **Sentiment Analysis** — News aggregation from CryptoPanic and NewsAPI
- 💾 **Persistent State** — Portfolio, positions, and trade history survive server restarts
- 🐳 **Docker Ready** — Deploy anywhere with containerized infrastructure

---

## Core Principles

### 1. Human-in-the-Loop
The AI **proposes**, the human **disposes**. No autonomous execution without explicit approval.

### 2. Explainability First
Every suggestion must explain the "why" and associated risks in simple, non-jargon terms.

### 3. Accuracy-Focused Skepticism
Monty acknowledges uncertainty and provides confidence levels rather than absolute predictions.

### 4. Modular Evolution
Start with paper trading ($10k virtual) and modular strategies that can be toggled and tuned.

### 5. Conviction-Based Advising
Monty **pushes back** on risky ideas. Chasing pumps? Overleveraging? He'll tell you why that's problematic.

### 6. Minimal Abstraction
Explicitly avoids LangChain and other heavy frameworks in favor of direct `google-genai` SDK integration.

### 7. Strict Model Enforcement
Only `gemini-3-pro-preview` is permitted—no older models allowed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MONTY ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌──────────────────┐     ┌──────────────────────┐ │
│  │  Web UI     │────▶│   Flask Routes   │────▶│   Chat Engine        │ │
│  │ Dashboard   │     │  /api/chat       │     │  (Gemini 3 Pro)      │ │
│  └─────────────┘     │  /api/portfolio  │     │                      │ │
│                      │  /api/trades     │     │  ┌────────────────┐  │ │
│  ┌─────────────┐     └──────────────────┘     │  │ Tool Executor  │  │ │
│  │    CLI      │                              │  │ - get_price    │  │ │
│  │  Interface  │──────────────────────────────│  │ - propose_trade│  │ │
│  └─────────────┘                              │  │ - execute_trade│  │ │
│                                               │  │ - portfolio    │  │ │
│                                               │  └────────────────┘  │ │
│                                               └──────────┬───────────┘ │
│                                                          │             │
│  ┌───────────────────────────────────────────────────────▼───────────┐ │
│  │                         CORE SERVICES                              │ │
│  ├───────────────────┬────────────────────┬──────────────────────────┤ │
│  │   Price Sensor    │   News Sensor      │    Paper Trading Engine  │ │
│  │   (CCXT)          │   (CryptoPanic/    │    - Buy/Sell execution  │ │
│  │   - Binance       │    NewsAPI)        │    - Position tracking   │ │
│  │   - Kraken        │                    │    - P&L calculation     │ │
│  │   - Coinbase Pro  │                    │    - Stop-loss/TP        │ │
│  │   - KuCoin        │                    │                          │ │
│  │   - Gate.io       │                    │                          │ │
│  └───────────────────┴────────────────────┴──────────────────────────┘ │
│                                                          │             │
│  ┌───────────────────────────────────────────────────────▼───────────┐ │
│  │                         STRATEGY MODULES                          │ │
│  ├────────────────┬────────────────┬────────────────┬───────────────┤ │
│  │ RSI Dip Buyer  │ Sentiment      │ Moonshot       │ Swing Trend   │ │
│  │ (Mean Revert)  │ Surfer         │ Scanner        │ Rider         │ │
│  │ RSI < 30 → BUY │ News-driven    │ Volume spikes  │ MA Pullbacks  │ │
│  │ RSI > 70 → SELL│ sentiment      │ High-risk/     │ Trend-follow  │ │
│  │                │ trading        │ high-reward    │ ing           │ │
│  └────────────────┴────────────────┴────────────────┴───────────────┘ │
│                                                          │             │
│  ┌───────────────────────────────────────────────────────▼───────────┐ │
│  │                      PERSISTENCE (SQLite)                         │ │
│  │   - Trade proposals (with 30-min TTL)                             │ │
│  │   - Open positions                                                │ │
│  │   - Executed trade history                                        │ │
│  │   - Portfolio state (cash, balances)                              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### 1. Automated Trading Strategies

Four modular strategy classes that can be independently toggled:

| Strategy | Type | Entry Condition | Risk Level |
|----------|------|-----------------|------------|
| **RSI Dip Buyer** | Mean Reversion | RSI < 30 (oversold) | Moderate |
| **Sentiment Surfer** | News-Driven | Bullish sentiment detected | Moderate |
| **Moonshot Scanner** | Breakout | Volume spike + 5%+ move | High |
| **Swing Trend Rider** | Trend-Following | Pullback to 20MA in uptrend | Low-Moderate |

Each strategy outputs a `StrategySignal` containing:
- Signal type (BUY/SELL/HOLD)
- Confidence score (0.0 - 1.0)
- Reasoning explanation
- Metadata (RSI value, sentiment score, etc.)

### 2. Paper Trading Engine

A fully-featured simulation engine for risk-free testing:

- **Initial Capital**: $10,000 virtual USDT
- **Position Tracking**: Entry price, quantity, stop-loss, take-profit
- **P&L Calculation**: Real-time unrealized P&L using live market prices
- **Order Types**: Market orders with stop-loss and take-profit support
- **Database Persistence**: Survives server restarts via SQLite models

**Key Models** (in `app/models.py`):
- `Trade` — Proposed trades with 30-minute TTL expiration
- `Position` — Open positions with entry data
- `ExecutedTrade` — Historical trade records with P&L
- `PortfolioState` — Cash balance and initial capital

### 3. Conversational AI (Chat Interface)

The heart of Monty: a conversational interface powered by **Gemini 3 Pro** with native function calling.

#### System Prompt Highlights
```
You are Monty, a knowledgeable crypto trading assistant. 🎩

- Warm, approachable, confident but not arrogant
- Has OPINIONS and CONVICTION — you don't just agree with everything
- Uses 3-5% position sizing, minimum 2:1 risk-reward
- NEVER executes trades without explicit user approval
```

#### Available Tools (Function Calling)

| Tool | Description |
|------|-------------|
| `get_price(symbol)` | Fetch current price and 24h change |
| `get_portfolio()` | Portfolio summary with positions and P&L |
| `get_market_overview()` | Multi-coin market snapshot |
| `analyze_news_sentiment()` | Aggregate sentiment from news sources |
| `propose_trade(symbol, action, reason)` | Create trade proposal for user approval |
| `execute_approved_trade(trade_id)` | Execute a previously approved trade |
| `get_pending_trades()` | List all pending proposals |
| `get_trade_history(limit)` | Historical executed trades |
| `get_trading_playbook(section)` | Retrieve detailed strategy guidance |

#### Tool-Based Knowledge Retrieval

Monty uses on-demand retrieval to handle extensive trading heuristics. Instead of cramming everything into the system prompt, the `get_trading_playbook` tool fetches relevant sections:
- `strategy` — When to use momentum vs. mean reversion
- `risk` — Position sizing, stop-loss rules, maximum exposure
- `entry` — Aggressive vs. conservative timing
- `psychology` — Handling FOMO, revenge trading, overleveraging

### 4. Web Dashboard

A polished dark-mode SPA built with vanilla HTML/CSS/JavaScript:

- **Chat Interface**: Real-time conversation with tool call visibility
- **Portfolio Panel**: Live portfolio value, cash, P&L percentage
- **Positions Table**: Open positions with real-time unrealized P&L
- **Trade Queue**: Pending proposals with Approve/Reject buttons and TTL countdown
- **Context Debug Panel** (🔍): Full transparency into system prompt and active state
- **Chat Export**: Server-side markdown export to `chat_logs/` folder

### 5. Command-Line Interface (CLI)

A full-featured CLI for terminal-based interaction and debugging:

```bash
# Interactive chat session
python cli.py chat

# Portfolio management
python cli.py portfolio      # View summary
python cli.py positions      # List open positions
python cli.py pending        # List pending trades

# Trade management
python cli.py approve <ID>   # Approve a pending trade
python cli.py reject <ID>    # Reject a pending trade

# Quick trade proposal
python cli.py trade buy BTC --allocation 5
```

### 6. Market Data Services

#### Price Sensor (`app/services/price_sensor.py`)

Multi-exchange price fetching with automatic fallback:

```python
EXCHANGES = ['binance', 'kraken', 'coinbasepro', 'kucoin', 'gate']
```

- **Symbol Normalization**: `btc` → `BTC/USDT`, `BTC/USD` → `BTC/USDT`
- **Ticker Data**: Last price, 24h volume, 24h change percentage
- **OHLCV Data**: Candlestick data for technical analysis

#### News Sensor (`app/services/news_sensor.py`)

Aggregated crypto news for sentiment analysis:

- **Primary**: CryptoPanic API (free tier available)
- **Fallback**: NewsAPI (requires key)

---

## Project Structure

```
Monty/
├── run.py                      # Flask application entry point
├── cli.py                      # Command-line interface
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image configuration
├── docker-compose.yml          # Container orchestration
├── .env                        # Environment variables (API keys)
│
├── app/
│   ├── __init__.py             # Flask app factory
│   ├── config.py               # Configuration settings
│   ├── extensions.py           # Flask-SQLAlchemy, Flask-APScheduler
│   ├── models.py               # SQLAlchemy ORM models
│   │
│   ├── core/
│   │   ├── chat_engine.py      # Gemini chat with function calling
│   │   ├── chat_tools.py       # Tool definitions and executor
│   │   ├── gemini_client.py    # Gemini SDK wrapper
│   │   ├── scheduler_jobs.py   # APScheduler background jobs
│   │   └── trading_playbook.md # Trading knowledge base
│   │
│   ├── agents/
│   │   ├── strategies.py       # Strategy module classes
│   │   ├── strategist.py       # Strategy orchestrator
│   │   ├── paper_trading.py    # Paper trading simulation engine
│   │   └── proposals.py        # Trade proposal management
│   │
│   ├── services/
│   │   ├── price_sensor.py     # CCXT price fetching
│   │   └── news_sensor.py      # News aggregation
│   │
│   ├── web/
│   │   ├── __init__.py         # Blueprint registration
│   │   └── routes.py           # Flask API endpoints
│   │
│   ├── static/                 # CSS, JS, images
│   └── templates/              # Jinja2 HTML templates
│
├── instance/                   # SQLite database (auto-created)
├── chat_logs/                  # Exported chat markdown files
└── LLM Crypto Trading Bot Feasibility.pdf  # Research document
```

---

## Installation

### Prerequisites

- Python 3.10+
- A Gemini API key ([Get one here](https://ai.google.dev/))

### Local Setup

```bash
# Clone the repository
git clone https://github.com/youruser/Monty.git
cd Monty

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Docker Setup

```bash
# Build and run
docker-compose up --build

# Or build manually
docker build -t monty .
docker run -p 5000:5000 --env-file .env monty
```

---

## Configuration

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional - for news sentiment features
NEWSAPI_KEY=your_newsapi_key
CRYPTOPANIC_TOKEN=your_cryptopanic_token
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `NEWSAPI_KEY` | ❌ | NewsAPI.org API key |
| `CRYPTOPANIC_TOKEN` | ❌ | CryptoPanic API token |
| `FLASK_ENV` | ❌ | `development` or `production` |
| `FLASK_DEBUG` | ❌ | `1` for debug mode |

---

## Usage

### Starting the Server

```bash
python run.py
```

The dashboard will be available at: **http://localhost:5050**

### Example Chat Interactions

```
You: What's the current price of SOL?
Monty: [calls get_price("SOL")] SOL is currently trading at $142.50, 
       up 3.2% in the last 24 hours.

You: Should I buy some?
Monty: Let me check the market conditions... [calls get_market_overview, 
       analyze_news_sentiment] SOL is showing strength, but it's already 
       up 3.2% today. If you'd entered this morning, great—but now you'd 
       be chasing. I'd recommend waiting for a pullback to $138-140.

You: OK, propose a trade at those levels
Monty: [calls propose_trade] I've created a limit order proposal:
       • Action: BUY SOL/USDT
       • Target Entry: $139.00
       • Stop-Loss: $132.00 (-5%)
       • Position Size: 5% of portfolio
       
       Approve in the Trade Queue when ready.
```

### Trade Lifecycle

1. **Proposal** — Monty (or user via CLI) creates a trade proposal
2. **Pending** — Trade waits in queue with 30-minute TTL
3. **Approval** — User clicks Approve (or via `cli.py approve <ID>`)
4. **Execution** — Paper trading engine executes the trade
5. **Position** — New position appears in portfolio
6. **Exit** — Sell via chat or automatic stop-loss/take-profit

---

## API Reference

### Chat API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/chat` | POST | Send message, get AI response |
| `GET /api/chat/history` | GET | Retrieve conversation history |
| `POST /api/chat/clear` | POST | Clear conversation history |
| `GET /api/chat/context` | GET | Debug: view system prompt + state |
| `POST /api/chat/export` | POST | Export chat to markdown file |

### Portfolio API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/portfolio` | GET | Portfolio summary with positions |

### Trade API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/trades/pending` | GET | List pending proposals |
| `POST /api/trades/<id>/approve` | POST | Approve and execute trade |
| `POST /api/trades/<id>/reject` | POST | Reject trade proposal |
| `POST /api/trades/reject-all` | POST | Bulk reject all pending |
| `POST /api/scan` | POST | Manually trigger market scan |

### Health Check

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | GET | Service health status |

---

## Trading Playbook

Monty follows a comprehensive trading playbook stored in `app/core/trading_playbook.md`. Key excerpts:

### Position Sizing
- **Default allocation**: 3-5% of portfolio per trade
- **Maximum single-trade risk**: 2% of portfolio
- **Maximum exposure**: 50% deployed at once

### Risk-Reward Rules
- **Minimum R:R ratio**: 2:1 (target must be 2x the stop distance)
- **Stop-loss**: Always defined before entry

### When Monty Pushes Back
- ❌ Chasing a pump (10%+ already moved)
- ❌ Overleveraging (>5% single position)
- ❌ FOMO-driven entries
- ❌ No exit plan defined

### Market Cycle Flow
```
BTC → ETH → Layer-1s (SOL, AVAX) → Mid-caps → Meme coins
       ↑ Risk-off ────────────────────────────── Risk-on ↓
```

---

## Development Roadmap

### ✅ Completed Phases

| Phase | Description |
|-------|-------------|
| 1. Skeleton | Dockerized Flask + SQLite + APScheduler |
| 2. Sensors | Price (CCXT) and News (CryptoPanic/NewsAPI) |
| 3. Strategies | RSI, Sentiment, Moonshot, Swing modules |
| 4. Web UI | Dark-mode SPA dashboard |
| 5. Chat | Gemini function calling + tool visibility |
| 6. Visibility | Context Debug Panel + Swing Trend Rider |
| 7. Trade Management | TTL expiration + batch management |
| 8. Advanced UI | Trade queue + inline approve/reject |
| 9. Persistence | Database-backed portfolio state |

### 🔄 In Progress

- **Maintenance**: API stabilization, frontend state management

### 📋 Future Roadmap

| Feature | Priority |
|---------|----------|
| Telegram Bot | High — Push notifications + 1-tap actions |
| Grid Trading | Medium — Sideways market strategy |
| Web Console | Medium — Live server logs in dashboard |
| Real Exchange Integration | Future — Binance/Coinbase live trading |

---

## Technical Details

### Dependencies

```
Flask                 # Web framework
Flask-SQLAlchemy      # ORM and database
Flask-APScheduler     # Background job scheduling
python-dotenv         # Environment configuration
google-genai          # Gemini SDK (direct integration)
pydantic              # Data validation
ccxt                  # Crypto exchange connectivity
newsapi-python        # News API client
praw                  # Reddit API (optional)
requests              # HTTP client
gunicorn              # Production WSGI server
click                 # CLI framework (via Flask)
```

### Database Schema

```sql
-- Trade Proposals (with TTL)
CREATE TABLE trade (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(10),
    action VARCHAR(10),        -- BUY/SELL
    price FLOAT,
    quantity FLOAT,
    status VARCHAR(20),        -- PENDING/APPROVED/EXECUTED/REJECTED/EXPIRED
    expires_at DATETIME,       -- 30-min TTL
    strategy VARCHAR(50),
    reasoning TEXT
);

-- Open Positions
CREATE TABLE position (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE,
    entry_price FLOAT,
    quantity FLOAT,
    side VARCHAR(10),          -- LONG/SHORT
    stop_loss FLOAT,
    take_profit FLOAT
);

-- Executed Trades
CREATE TABLE executed_trade (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20),
    action VARCHAR(10),
    price FLOAT,
    quantity FLOAT,
    value FLOAT,
    pnl FLOAT
);

-- Portfolio State
CREATE TABLE portfolio_state (
    id INTEGER PRIMARY KEY,
    cash_balance FLOAT DEFAULT 10000.0,
    initial_balance FLOAT DEFAULT 10000.0
);
```

### Gemini Function Calling Flow

```
User Message
     │
     ▼
┌─────────────────────────────┐
│ ChatEngine.chat()           │
├─────────────────────────────┤
│ 1. Build context            │
│ 2. Append history           │
│ 3. Call Gemini API          │
│    with MONTY_TOOLS         │
└─────────────┬───────────────┘
              │
              ▼
        Has function_call?
              │
       ┌──────┴──────┐
       │ YES         │ NO
       ▼             ▼
   Execute Tool    Return Response
       │
       ▼
   Append Result
       │
       ▼
   Call Gemini Again
   (up to 5 iterations)
```

---

## License

This project is proprietary and intended for personal/internal use. See LICENSE file for details.

---

<p align="center">
  <strong>Built with 🧠 by the intersection of AI and markets</strong><br>
  <em>"Missing a trade is better than chasing one."</em> — Monty
</p>
