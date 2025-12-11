<div align="center">

![Fyers Algorithmic Trading](images/logo.png)

# 🚀 Fyers Algorithmic Trading Platform

**Production-grade algorithmic trading system for NSE equities using the Fyers API**  
Real-time streaming • Multi-strategy consensus • Docker-ready deployment

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [API Docs](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#️-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Usage](#-usage)
- [Strategies](#-strategies)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Roadmap](#️-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

<div align="center">

| Feature | Description |
|---------|-------------|
| 📡 **Real-time Streaming** | WebSocket-based live market data from Fyers API |
| 📊 **Candle Builder** | Converts tick data into 1-minute OHLCV candles |
| 🎯 **Multi-Strategy** | EMA Crossover, Swing Trend, Scalping strategies |
| 🤝 **Consensus Logic** | Execute trades only when ≥2 strategies agree |
| 📝 **Dual Trading Modes** | Paper trading for testing, Live mode for production |
| ⚖️ **Risk Management** | Configurable position sizing and daily loss limits |
| 💾 **TimescaleDB** | Efficient time-series data storage |
| 🐳 **Docker Ready** | Complete Docker Compose setup included |
| 🔄 **Auto-Recovery** | Graceful error handling and reconnection logic |
| 📈 **Live Dashboard** | Real-time monitoring and trade visualization |

</div>

---

## 🏗️ Architecture

```
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
```

---

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Python** 3.11 or higher
- **Docker** & Docker Compose (recommended)
- **PostgreSQL** with TimescaleDB extension
- **Redis** (optional, for caching)
- **Fyers Account** with API credentials ([Get API access](https://fyers.in/))

---

## 🚀 Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Avi5205/Fyers-Algo-Bot.git
cd Fyers-Algo-Bot

# Copy environment configuration
cp .env.example .env

# Edit .env with your Fyers credentials
nano .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/Avi5205/Fyers-Algo-Bot.git
cd Fyers-Algo-Bot

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
./setup_weeks_2_5.sh

# Copy and configure environment
cp .env.example .env
nano .env
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Fyers API Credentials
FYERS_APP_ID=YOUR_APP_ID_HERE
FYERS_ACCESS_TOKEN=YOUR_ACCESS_TOKEN_HERE

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fyers_trading
DB_USER=postgres
DB_PASSWORD=your_secure_password

# Trading Parameters
POSITION_SIZE=5000              # Position size in INR
MIN_MOVE_PCT=0.5                # Minimum price move percentage
MAX_DAILY_LOSS=10000            # Maximum daily loss limit
MIN_STRATEGY_CONSENSUS=2        # Minimum strategies to agree

# Risk Management
STOP_LOSS_PCT=1.5               # Stop loss percentage
TAKE_PROFIT_PCT=2.5             # Take profit percentage

# Logging
LOG_LEVEL=INFO
```

### Strategy Configuration

Edit `app/scripts/realtime_trading_engine.py` to customize:

- **Symbol List**: NSE equity symbols to trade
- **EMA Parameters**: Fast (9) and Slow (21) EMA periods
- **Swing Parameters**: Lookback period (50), breakout threshold
- **Scalping Parameters**: Mean reversion threshold (0.3%)

Example:

```python
SYMBOLS = [
    "NSE:SBIN-EQ",
    "NSE:RELIANCE-EQ",
    "NSE:TCS-EQ",
    "NSE:INFY-EQ"
]

EMA_FAST = 9
EMA_SLOW = 21
SWING_LOOKBACK = 50
SCALP_THRESHOLD = 0.003
```

---

## 🎮 Usage

### Starting the Bot

#### Paper Trading Mode (Recommended for Testing)

```bash
# Using shell script
./run_paper_trading.sh

# Or via Docker
docker-compose exec backend python app/scripts/realtime_trading_engine.py --mode=paper
```

#### Live Trading Mode (⚠️ Real Money)

```bash
# Using shell script
./run_live_feed.sh

# Or via Docker
docker-compose exec backend python app/scripts/realtime_trading_engine.py --mode=live
```

### Running Backtests

```bash
# Run all backtests
./run_all_backtests.sh

# Run specific strategy backtest
python app/scripts/backtest_ema.py
python app/scripts/backtest_swing.py
python app/scripts/backtest_scalping.py
```

### Morning Startup Routine

```bash
# Automated morning startup script
./morning_startup.sh
```

This script will:
1. Check system health
2. Verify database connectivity
3. Validate API credentials
4. Start trading bot in specified mode

---

## 📊 Strategies

### 1. EMA Crossover Strategy

**Logic**: Classic trend-following strategy using exponential moving averages.

- **Entry Signal**: Fast EMA (9) crosses above Slow EMA (21)
- **Exit Signal**: Fast EMA crosses below Slow EMA
- **Best For**: Trending markets
- **Timeframe**: 1-minute candles

```python
if fast_ema > slow_ema and prev_fast_ema <= prev_slow_ema:
    signal = "BUY"
elif fast_ema < slow_ema and prev_fast_ema >= prev_slow_ema:
    signal = "SELL"
```

### 2. Swing Trend Strategy

**Logic**: Identifies swing highs and lows for breakout trades.

- **Entry Signal**: Price breaks above recent swing high with volume confirmation
- **Exit Signal**: Price breaks below recent swing low
- **Best For**: Volatile markets with clear swing patterns
- **Lookback**: 50 candles

```python
swing_high = max(high_prices[-50:])
swing_low = min(low_prices[-50:])

if close > swing_high * (1 + breakout_threshold):
    signal = "BUY"
elif close < swing_low * (1 - breakout_threshold):
    signal = "SELL"
```

### 3. Scalping Mean Reversion

**Logic**: Quick trades based on price deviation from short-term EMA.

- **Entry Signal**: Price deviates >0.3% from 5-EMA
- **Exit Signal**: Price returns to 5-EMA or hits TP/SL
- **Best For**: Range-bound markets
- **Holding Period**: 1-5 minutes

```python
deviation = (close - ema_5) / ema_5

if deviation < -0.003:  # Oversold
    signal = "BUY"
elif deviation > 0.003:  # Overbought
    signal = "SELL"
```

### Consensus Mechanism

The bot executes trades only when **at least 2 strategies agree**:

```python
signals = {
    'ema': strategy_ema.get_signal(),
    'swing': strategy_swing.get_signal(),
    'scalp': strategy_scalp.get_signal()
}

buy_votes = sum(1 for s in signals.values() if s == "BUY")
sell_votes = sum(1 for s in signals.values() if s == "SELL")

if buy_votes >= 2:
    execute_trade("BUY")
elif sell_votes >= 2:
    execute_trade("SELL")
```

---

## 📡 API Documentation

The FastAPI backend provides RESTful endpoints for bot control and monitoring.

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Start Trading Bot

```http
POST /api/bot/start?mode={paper|live}
```

**Parameters:**
- `mode` (query): Trading mode - `paper` or `live`

**Response:**
```json
{
  "status": "success",
  "message": "Bot started in paper mode",
  "timestamp": "2024-12-11T10:30:00Z"
}
```

#### 2. Stop Trading Bot

```http
POST /api/bot/stop
```

**Response:**
```json
{
  "status": "success",
  "message": "Bot stopped successfully",
  "timestamp": "2024-12-11T15:30:00Z"
}
```

#### 3. Get Bot Status

```http
GET /api/bot/status
```

**Response:**
```json
{
  "running": true,
  "mode": "paper",
  "uptime": "5h 23m",
  "positions": {
    "open": 2,
    "closed": 15
  },
  "performance": {
    "total_trades": 17,
    "winning_trades": 12,
    "losing_trades": 5,
    "win_rate": 70.59,
    "total_pnl": 1245.50,
    "today_pnl": 245.50
  },
  "strategies": {
    "ema": {"active": true, "signals": 8},
    "swing": {"active": true, "signals": 6},
    "scalp": {"active": true, "signals": 12}
  }
}
```

#### 4. Get Recent Trades

```http
GET /api/trades?limit=50
```

**Parameters:**
- `limit` (query, optional): Number of trades to return (default: 50)

**Response:**
```json
{
  "trades": [
    {
      "id": 1234,
      "symbol": "NSE:SBIN-EQ",
      "side": "BUY",
      "quantity": 10,
      "entry_price": 625.50,
      "exit_price": 628.75,
      "pnl": 32.50,
      "strategy": "consensus",
      "entry_time": "2024-12-11T10:15:00Z",
      "exit_time": "2024-12-11T10:45:00Z",
      "status": "closed"
    }
  ],
  "total": 17
}
```

#### 5. Get Market Data

```http
GET /api/market/{symbol}
```

**Parameters:**
- `symbol` (path): Trading symbol (e.g., `NSE:SBIN-EQ`)

**Response:**
```json
{
  "symbol": "NSE:SBIN-EQ",
  "last_price": 625.50,
  "change": 2.35,
  "change_pct": 0.38,
  "volume": 1250000,
  "indicators": {
    "ema_9": 624.20,
    "ema_21": 622.80,
    "rsi": 58.5
  },
  "timestamp": "2024-12-11T10:30:00Z"
}
```

### Interactive Documentation

Access the interactive Swagger UI at:
```
http://localhost:8000/docs
```

Access the ReDoc documentation at:
```
http://localhost:8000/redoc
```

---

## 🌐 Deployment

### Production Deployment Checklist

- [ ] Use environment variables for all secrets
- [ ] Enable SSL/TLS for API endpoints
- [ ] Set up database backups (daily recommended)
- [ ] Configure monitoring and alerting
- [ ] Use Redis for caching
- [ ] Set up log aggregation
- [ ] Enable rate limiting
- [ ] Test failover procedures

### Recommended VPS Setup

**Minimum Requirements:**
- 2 vCPUs
- 4GB RAM
- 50GB SSD
- Ubuntu 22.04 LTS

**Recommended Providers:**
- DigitalOcean
- AWS EC2
- Google Cloud Compute
- Linode

### Docker Production Deployment

```bash
# Production compose file
docker-compose -f docker-compose.prod.yml up -d

# Enable auto-restart
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend

# View production logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### Systemd Service (Alternative to Docker)

Create `/etc/systemd/system/fyers-bot.service`:

```ini
[Unit]
Description=Fyers Algo Trading Bot
After=network.target postgresql.service

[Service]
Type=simple
User=trading
WorkingDirectory=/opt/fyers-bot
Environment="PATH=/opt/fyers-bot/.venv/bin"
ExecStart=/opt/fyers-bot/.venv/bin/python app/scripts/realtime_trading_engine.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable fyers-bot
sudo systemctl start fyers-bot
sudo systemctl status fyers-bot
```

---

## 🗺️ Roadmap

### Phase 1: Core Trading Engine ✅

- [x] Real-time WebSocket data streaming
- [x] Candle builder (1-min OHLCV)
- [x] Multi-strategy implementation
- [x] Consensus mechanism
- [x] Paper trading mode
- [x] Live trading mode
- [x] Basic risk management

### Phase 2: Enhanced Features 🚧

- [ ] React-based trading dashboard
- [ ] Advanced charting with indicators
- [ ] Market scanner for opportunities
- [ ] Comprehensive backtesting framework
- [ ] Performance analytics dashboard
- [ ] Trade journal with notes
- [ ] Mobile app notifications

### Phase 3: Advanced Capabilities 🔮

- [ ] Machine learning signal generation
- [ ] Options trading strategies
- [ ] Multi-broker support (Zerodha, Angel One)
- [ ] Portfolio optimization
- [ ] Automated strategy discovery
- [ ] Social trading features
- [ ] Cloud-based deployment

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### How to Contribute

1. **Fork the repository**
   ```bash
   git clone https://github.com/Avi5205/Fyers-Algo-Bot.git
   cd Fyers-Algo-Bot
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow PEP 8 style guidelines
   - Add tests for new features

3. **Test your changes**
   ```bash
   pytest tests/
   ```

4. **Submit a pull request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure all tests pass

### Development Guidelines

- Use type hints for function parameters
- Write docstrings for all functions
- Keep functions small and focused
- Add unit tests for new functionality
- Update documentation as needed

### Code Style

```python
def calculate_ema(prices: list[float], period: int) -> float:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: List of price values
        period: EMA period
        
    Returns:
        float: Calculated EMA value
    """
    pass
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Avi Gaur

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## ⚠️ Disclaimer

**IMPORTANT**: This software is for educational and research purposes only. 

- Trading in equities involves substantial risk of loss
- Past performance does not guarantee future results
- The authors are not responsible for any financial losses
- Always test strategies thoroughly in paper trading mode
- Consult with a financial advisor before live trading
- Use at your own risk

---

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/Avi5205/Fyers-Algo-Bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Avi5205/Fyers-Algo-Bot/discussions)
- **Email**: [akgpcamp@gmail.com]

---

## 🙏 Acknowledgments

- [Fyers API](https://fyers.in/) for excellent trading infrastructure
- [FastAPI](https://fastapi.tiangolo.com/) for the robust web framework
- [TimescaleDB](https://www.timescale.com/) for time-series database
- All contributors who help improve this project

---

<div align="center">

**Made with ❤️ by [Avi Gaur](https://github.com/Avi5205)**

⭐ Star this repo if you find it helpful!

</div>
