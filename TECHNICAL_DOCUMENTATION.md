# TECHNICAL DOCUMENTATION

## Overview
This document describes the architecture, APIs, configuration, strategies, and deployment details for the Fyers Algorithmic Trading Platform.

## Components
1. **Real-time Engine** - Ingests tick stream from Fyers WebSocket, builds 1-min candles, dispatches to strategies.
2. **Strategies** - EMA Crossover, Swing Trend, Scalping Mean Reversion.
3. **Consensus Manager** - Aggregates signals; requires >=2 votes for execution.
4. **Order Manager** - Executes orders to Fyers REST API (paper/live modes).
5. **Storage** - TimescaleDB (Postgres) for historical OHLCV and trades.
6. **Cache** - Redis for ephemeral state and locks.
7. **Frontend** - React + Recharts (dashboard).

## API Endpoints (FastAPI)
- `POST /api/bot/start?mode=paper` - Start bot in paper mode.
- `POST /api/bot/stop` - Stop bot.
- `GET /api/bot/status` - Bot status and metrics.
- `GET /api/trades` - Recent trades.

## Strategy Algorithms (Brief)
### EMA Crossover
- Calculate EMA_fast (9) and EMA_slow (21) on 1-min candles.
- Buy when EMA_fast crosses above EMA_slow.
- Sell when EMA_fast crosses below EMA_slow.

### Swing Trend
- Identify swing highs/lows with lookback (50 bars).
- Enter on breakout of swing high/low after volatility check.

### Scalping Mean Reversion
- Monitor price deviation vs 5-EMA.
- Enter when deviation > 0.3% in opposite direction, small TP/SL.

## Risk Management
- Position sizing based on `POSITION_SIZE` env var.
- Daily loss limit enforced per account.
- Max concurrent positions configurable.

## Deployment
- Use Docker Compose for local and VPS deployment.
- Recommended: run on a VPS with at least 2 vCPUs, 4GB RAM, SSD.
- Use a process supervisor for reliability (systemd, docker restart policies).

## Monitoring & Logs
- Centralized logs via Docker logging driver or external ELK.
- Export metrics for Prometheus and visualize with Grafana.

## Notes
- FYERS `ACCESS_TOKEN` is short-lived; implement refresh workflow.
- Paper mode should always be tested before live.

