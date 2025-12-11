#!/usr/bin/env bash
# Start live WebSocket feed
cd "$(dirname "$0")/docker"
docker compose up -d timescaledb
sleep 2
echo "Starting Fyers live WebSocket feed - Press Ctrl+C to stop"
docker compose run --rm data-service python scripts/live_data_feed.py
