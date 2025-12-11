#!/usr/bin/env bash
# Run all strategies on all symbols
cd "$(dirname "$0")/docker"
docker compose up -d timescaledb
sleep 2
docker compose run --rm data-service python scripts/run_multi_strategy_backtest.py
