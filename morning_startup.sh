#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================================="
echo "🚀 FYERS ALGO TRADING - MORNING STARTUP"
echo "=========================================================================="
echo ""

CURRENT_HOUR=$(date +%H)
echo "📅 Current Time: ${CURRENT_HOUR}:$(date +%M) IST"
echo ""

echo "=========================================================================="
echo "🔐 Token Management"
echo "=========================================================================="
echo ""

update_timestamp() {
    echo "$(date +%Y-%m-%d)" > app/.token_timestamp
}

# Check for .env in both locations
ENV_FILE=""
if [[ -f "app/.env" ]]; then
    ENV_FILE="app/.env"
elif [[ -f ".env" ]]; then
    ENV_FILE=".env"
fi

TOKEN_VALID=false
if [[ -n "$ENV_FILE" ]]; then
    ACCESS_TOKEN=$(grep "FYERS_ACCESS_TOKEN" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'" | xargs)
    
    if [[ -n "$ACCESS_TOKEN" ]]; then
        echo "✅ Found token: ${ACCESS_TOKEN:0:25}..."
        
        TIMESTAMP_FILE="${ENV_FILE%/.env}/.token_timestamp"
        if [[ -f "$TIMESTAMP_FILE" ]]; then
            LAST_GEN=$(cat "$TIMESTAMP_FILE")
            TODAY=$(date +%Y-%m-%d)
            
            if [[ "$LAST_GEN" == "$TODAY" ]]; then
                echo "✅ Valid until 6 AM tomorrow"
                TOKEN_VALID=true
            else
                echo "⚠️  Expired (generated: $LAST_GEN)"
            fi
        elif [[ ${CURRENT_HOUR} -lt 6 ]]; then
            TOKEN_VALID=true
        fi
    fi
else
    echo "❌ .env not found"
    ENV_FILE="app/.env"  # Default location
fi

echo ""

if [[ "$TOKEN_VALID" == false ]]; then
    echo "🔑 NEW TOKEN REQUIRED"
    echo ""
    echo "Options:"
    echo "  1. Generate via browser (Docker)"
    echo "  2. Paste manually (quickest!)"
    echo ""
    read -p "Choose (1/2): " opt
    
    if [[ "$opt" == "1" ]]; then
        echo ""
        echo "🌐 Starting Docker..."
        cd docker
        docker compose up -d timescaledb
        sleep 2
        
        echo "Running token generator..."
        docker compose run --rm data-service python scripts/generate_token.py
        
        cd ..
        
        if grep -q "FYERS_ACCESS_TOKEN" "$ENV_FILE" 2>/dev/null; then
            echo "✅ Token saved!"
            update_timestamp
            TOKEN_VALID=true
        else
            echo "⚠️  Falling back to manual paste"
            opt="2"
        fi
    fi
    
    if [[ "$opt" == "2" ]]; then
        echo ""
        echo "=========================================================================="
        echo "📋 PASTE YOUR TOKEN"
        echo "=========================================================================="
        echo ""
        echo "Format: APPID:ACCESS_TOKEN_STRING"
        echo "Example: ABC123-100:eyJ0eXAiOiJKV1Qi..."
        echo ""
        read -p "Access Token: " NEW_TOKEN
        
        if [[ -z "$NEW_TOKEN" ]]; then
            echo "❌ No token provided"
            exit 1
        fi
        
        # Ensure directory exists
        mkdir -p "$(dirname "$ENV_FILE")"
        
        # Backup and update
        [[ -f "$ENV_FILE" ]] && cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        
        if [[ -f "$ENV_FILE" ]] && grep -q "FYERS_ACCESS_TOKEN" "$ENV_FILE"; then
            sed -i.bak "s|^FYERS_ACCESS_TOKEN=.*|FYERS_ACCESS_TOKEN=\"${NEW_TOKEN}\"|" "$ENV_FILE"
            rm -f "${ENV_FILE}.bak"
        else
            echo "FYERS_ACCESS_TOKEN=\"${NEW_TOKEN}\"" >> "$ENV_FILE"
        fi
        
        update_timestamp
        echo ""
        echo "✅ Token saved to: $ENV_FILE"
        TOKEN_VALID=true
        
        # Restart containers
        echo "🔄 Restarting containers..."
        cd docker
        docker compose down 2>/dev/null || true
        sleep 2
        cd ..
    fi
fi

[[ "$TOKEN_VALID" == false ]] && { echo "❌ No valid token"; exit 1; }

echo ""
echo "✅ Token ready!"
echo ""

# Market hours check
if [[ ${CURRENT_HOUR} -lt 9 || ${CURRENT_HOUR} -ge 16 ]]; then
    echo "⚠️  Outside market hours (9 AM - 4 PM)"
    read -p "Continue? (y/N): " confirm
    [[ ! "$confirm" =~ ^[Yy]$ ]] && { echo "See you at 9 AM! 🌅"; exit 0; }
fi

echo "=========================================================================="
echo "💾 Starting Services"
echo "=========================================================================="
cd docker
docker compose up -d timescaledb
sleep 3
echo "✅ TimescaleDB running"
cd ..
echo ""

echo "📥 Checking historical data..."
mkdir -p logs
LAST=$(find logs -name "download_*.log" -mtime -1 2>/dev/null | wc -l | xargs)
if [[ "$LAST" -eq 0 ]]; then
    cd docker
    docker compose run --rm data-service python scripts/download_historical_data.py | tee ../logs/download_$(date +%Y%m%d_%H%M%S).log
    cd ..
else
    echo "✅ Recent data found"
fi
echo ""

echo "📡 Starting live feed..."
cd docker
docker compose up -d --force-recreate data-service
sleep 3
docker compose exec -d data-service python scripts/live_data_feed.py
cd ..
echo "✅ Live feed started"
echo ""

echo "⏳ Stabilizing (30s)..."
for i in {30..1}; do printf "\r   %2d..." "$i"; sleep 1; done
echo ""
echo ""

echo "=========================================================================="
echo "💰 PAPER TRADING - Press Ctrl+C to stop"
echo "=========================================================================="
echo ""
cd docker
docker compose run --rm data-service python scripts/run_paper_trading.py

trap 'echo ""; cd "$PROJECT_ROOT/docker"; docker compose stop; echo "✅ Stopped"' EXIT
