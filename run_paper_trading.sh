#!/usr/bin/env bash
# Start paper trading simulation
cd "$(dirname "$0")/docker"
docker compose up -d timescaledb
sleep 2
echo "Starting paper trading - Press Ctrl+C to stop and see results"
docker compose run --rm data-service python scripts/run_paper_trading.py
