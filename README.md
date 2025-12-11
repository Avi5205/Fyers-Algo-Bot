# 🚀 Fyers Algorithmic Trading Platform

A production-ready, full-stack algorithmic trading system for NSE equities using Fyers API with real-time WebSocket streaming, multi-strategy consensus engine, and comprehensive risk management.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents
- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Strategies](#-strategies)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)
- [Disclaimer](#-disclaimer)
- [License](#-license)

## ✨ Features

### Core Trading Engine
- **Real-time WebSocket Streaming**: Live tick data from Fyers API
- **Multi-Strategy Consensus**: Trades only when 2+ strategies agree
- **Paper & Live Trading**: Seamless mode switching
- **Session Summaries**: Detailed trade logs and PnL reports
- **Risk Management**: Position sizing, daily loss limits, max concurrent positions
- **1-Minute Candle Building**: Real-time OHLCV aggregation from tick data

### Trading Strategies
1. **EMA Crossover**: Fast/slow moving average trend detection
2. **Swing Trend**: Higher timeframe momentum analysis
3. **Scalping Mean Reversion**: Short-term price snap-back opportunities

### Technical Stack
- **Backend**: Python 3.11, FastAPI, asyncio
- **Database**: TimescaleDB (time-series for candles), PostgreSQL
- **Cache**: Redis
- **Frontend**: React, Recharts (charting)
- **Broker API**: Fyers API v3
- **Deployment**: Docker Compose

## 🏗️ Architecture

\`\`\`
┌─────────────────────────────────────────────────────────┐
│                    Fyers WebSocket                       │
│              (Real-time Tick Streaming)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Real-time Trading Engine  │
        │  • Candle Builder          │
        │  • Strategy Manager        │
        │  • Consensus Logic         │
        └─────────┬──────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  Strategies  │    │   Database   │
│  • EMA       │    │  TimescaleDB │
│  • Swing     │    │  (OHLCV)     │
│  • Scalping  │    └──────────────┘
└──────────────┘
        │
        ▼
┌─────────────────────┐
│  Order Execution    │
│  • Paper Trades     │
│  • Live Orders      │
│    (Fyers API)      │
└─────────────────────┘
\`\`\`

## 📋 Prerequisites

- **Python**: 3.11 or higher
- **Docker & Docker Compose**: Latest version
- **Fyers Account**: 
  - Register at [fyers.in](https://fyers.in)
  - Create API app to get \`APP_ID\`
  - Generate access token (valid 24 hours)
- **Operating System**: macOS, Linux, or Windows WSL2

## 🚀 Installation

### 1. Clone Repository
\`\`\`bash
git clone https://github.com/yourusername/fyers-algo.git
cd fyers-algo
\`\`\`

### 2. Environment Setup
\`\`\`bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
\`\`\`

**\`.env\` contents:**
\`\`\`bash
# Fyers API Credentials
FYERS_APP_ID=YOUR_APP_ID_HERE
FYERS_ACCESS_TOKEN=YOUR_ACCESS_TOKEN_HERE

# Database
DB_PASSWORD=your_secure_password_123

# Trading Parameters
POSITION_SIZE=5000          # ₹5000 per trade
MIN_MOVE_PCT=0.5           # Min 0.5% move
MIN_NET_PROFIT=25          # Min ₹25 profit target
\`\`\`

### 3. Install Dependencies

**Option A: Docker (Recommended)**
\`\`\`bash
docker-compose up -d
\`\`\`

**Option B: Local Python**
\`\`\`bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
\`\`\`

## ⚙️ Configuration

### Trading Symbols
Edit \`app/scripts/realtime_trading_engine.py\`:
\`\`\`python
self.symbols = [
    'NSE:RELIANCE-EQ',
    'NSE:TCS-EQ',
    'NSE:INFY-EQ',
    'NSE:HDFCBANK-EQ',
    'NSE:ICICIBANK-EQ'
]
\`\`\`

### Strategy Parameters
\`\`\`python
# EMA Crossover
fast_period = 9
slow_period = 21

# Swing Trend
lookback_bars = 50
volatility_threshold = 1.5

# Scalping Mean Reversion
short_ema_period = 5
reversion_threshold = 0.3
\`\`\`

## 🎮 Usage

### Paper Trading (Recommended for Testing)
\`\`\`bash
./run_paper_trading.sh
\`\`\`

### Live Trading ⚠️
\`\`\`bash
# CAUTION: Real money!
./run_live_feed.sh
\`\`\`

### Docker Deployment
\`\`\`bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
\`\`\`

## 📊 Strategies

### 1. EMA Crossover Strategy
**Logic**: Detects trend reversals when fast EMA crosses slow EMA
- **BUY**: Fast EMA crosses above slow EMA
- **SELL**: Fast EMA crosses below slow EMA
- **Timeframe**: 1-minute candles
- **Parameters**: Fast=9, Slow=21

### 2. Swing Trend Strategy
**Logic**: Identifies swing high/low breakouts
- **BUY**: Price breaks above recent swing high
- **SELL**: Price breaks below recent swing low
- **Timeframe**: Higher timeframe structure on 1-min data
- **Parameters**: Lookback=50 bars

### 3. Scalping Mean Reversion
**Logic**: Buys oversold, sells overbought (short-term)
- **BUY**: Price >0.3% below 5-EMA
- **SELL**: Price >0.3% above 5-EMA
- **Timeframe**: 1-minute candles
- **Parameters**: EMA=5, Threshold=0.3%

### Consensus Mechanism
\`\`\`python
# Requires 2+ strategies to agree
if buy_votes >= 2 and no_open_position:
    execute_buy()
elif sell_votes >= 2 and has_open_position:
    execute_sell()
\`\`\`

## 📡 API Documentation

### REST Endpoints

#### Start Bot
\`\`\`http
POST /api/bot/start?mode=paper
\`\`\`

#### Get Status
\`\`\`http
GET /api/bot/status
\`\`\`
**Response:**
\`\`\`json
{
  "running": true,
  "mode": "paper",
  "positions": 2,
  "total_trades": 15,
  "total_pnl": 245.50
}
\`\`\`

## 🐳 Deployment

### Production Deployment
\`\`\`bash
# VPS Setup
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sh

# Clone & Start
git clone <your-repo>
cd fyers-algo
docker-compose up -d
\`\`\`

## 🗺️ Roadmap

### Phase 1 ✅ (Complete)
- [x] Real-time WebSocket integration
- [x] Multi-strategy consensus engine
- [x] Paper & live trading modes
- [x] Session summaries & PnL tracking

### Phase 2 🚧 (In Progress)
- [ ] React dashboard with live charts
- [ ] Dynamic universe scanner (500+ NSE stocks)
- [ ] Risk management engine
- [ ] Backtesting module

### Phase 3 📅 (Planned)
- [ ] Machine learning signal integration
- [ ] Options trading strategies
- [ ] Multi-broker support

## ⚠️ Disclaimer

**This software is for educational purposes only. Trading involves substantial risk of loss. Use at your own risk. The authors are not responsible for any financial losses.**

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [Fyers API](https://fyers.in/api) - Broker API
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [TimescaleDB](https://www.timescale.com/) - Time-series database

---

⭐ **Star this repo if you found it helpful!**