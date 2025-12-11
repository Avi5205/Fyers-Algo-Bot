# Fyers Algorithmic Trading

![Logo](images/logo.png)

> Production-grade algorithmic trading system for NSE equities using the Fyers API — real-time streaming, multi-strategy consensus, and Docker-ready deployment.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents
- Features
- System Architecture
- Prerequisites
- Installation
- Configuration
- Usage
- Strategies
- API Docs
- Deployment
- Roadmap
- Disclaimer
- License

---


## Features

- Real-time WebSocket streaming from FYERS
- Candle builder (1-min OHLCV) from ticks
- Multi-strategy consensus (>=2 strategies to trade)
- Paper and Live modes
- Risk management and position sizing
- Dockerized deployment

---

## System Architecture

![Architecture](images/architecture.png)

---

## Quick Start

```bash
git clone https://github.com/yourusername/fyers-algo.git
cd fyers-algo
cp .env.example .env
# Edit .env with FYERS_APP_ID and FYERS_ACCESS_TOKEN
docker-compose up -d
```

---

## Images & Diagrams

Strategy flows:

![EMA Flow](images/strategy_flows/ema.png)
![Swing Flow](images/strategy_flows/swing.png)
![Scalping Flow](images/strategy_flows/scalping.png)

---

## Contributing

Please open issues or pull requests on GitHub. Follow the repository code style and testing guidelines.

---

## License

MIT License.

