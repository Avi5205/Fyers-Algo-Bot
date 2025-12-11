cd /Users/avinash/Developer/Algo\ Trading/Fyers/fyers-algo

# Create Nifty 50 universe file
cat > app/config/nifty50_symbols.py << 'EOF'
"""
Nifty 50 stock universe for scanning
"""

NIFTY50_SYMBOLS = [
    "NSE:RELIANCE-EQ",
    "NSE:TCS-EQ", 
    "NSE:HDFCBANK-EQ",
    "NSE:INFY-EQ",
    "NSE:ICICIBANK-EQ",
    "NSE:HINDUNILVR-EQ",
    "NSE:ITC-EQ",
    "NSE:SBIN-EQ",
    "NSE:BHARTIARTL-EQ",
    "NSE:KOTAKBANK-EQ",
    "NSE:LT-EQ",
    "NSE:AXISBANK-EQ",
    "NSE:ASIANPAINT-EQ",
    "NSE:MARUTI-EQ",
    "NSE:SUNPHARMA-EQ",
    "NSE:TITAN-EQ",
    "NSE:ULTRACEMCO-EQ",
    "NSE:BAJFINANCE-EQ",
    "NSE:NESTLEIND-EQ",
    "NSE:TECHM-EQ",
    "NSE:WIPRO-EQ",
    "NSE:HCLTECH-EQ",
    "NSE:POWERGRID-EQ",
    "NSE:NTPC-EQ",
    "NSE:ONGC-EQ",
    "NSE:TATASTEEL-EQ",
    "NSE:HINDALCO-EQ",
    "NSE:COALINDIA-EQ",
    "NSE:DIVISLAB-EQ",
    "NSE:DRREDDY-EQ",
    "NSE:BAJAJFINSV-EQ",
    "NSE:BAJAJ-AUTO-EQ",
    "NSE:ADANIPORTS-EQ",
    "NSE:GRASIM-EQ",
    "NSE:JSWSTEEL-EQ",
    "NSE:HEROMOTOCO-EQ",
    "NSE:CIPLA-EQ",
    "NSE:BRITANNIA-EQ",
    "NSE:APOLLOHOSP-EQ",
    "NSE:EICHERMOT-EQ",
    "NSE:INDUSINDBK-EQ",
    "NSE:TATAMOTORS-EQ",
    "NSE:M&M-EQ",
    "NSE:BPCL-EQ",
    "NSE:TATACONSUM-EQ",
    "NSE:HINDZINC-EQ",
    "NSE:UPL-EQ",
    "NSE:ADANIENT-EQ",
    "NSE:TRENT-EQ",
    "NSE:SHRIRAMFIN-EQ"
]
EOF

# Create multi-stock scanner
cat > scripts/run_stock_scanner.py << 'EOF'
"""
Multi-Stock Scanner - Finds best trading opportunities across Nifty 50
"""
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger
from core.timescale_client import TimescaleClient
from analytics.strategies.ema_crossover import EmaCrossoverStrategy
from analytics.strategies.swing_trend import SwingTrendStrategy
from analytics.strategies.scalping_mean_reversion import ScalpingMeanReversionStrategy
import sys
sys.path.append('/app')
from config.nifty50_symbols import NIFTY50_SYMBOLS


async def scan_stock(db, symbol, strategies):
    """Scan a single stock with all strategies"""
    opportunities = []
    
    # Get last 100 candles for analysis
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=2)
    
    try:
        candles = await db.fetch_candles(symbol, '1m', start, end)
        if not candles or len(candles) < 50:
            return opportunities
        
        latest_price = candles[-1]['close']
        
        for strategy in strategies:
            # Reset strategy state
            strategy.positions = {}
            
            # Run strategy on recent candles
            for candle in candles[-50:]:
                await strategy.on_candle(candle)
            
            # Check if strategy has an open position (signal generated)
            if symbol in strategy.positions:
                position = strategy.positions[symbol]
                signal_strength = abs(latest_price - position['entry_price']) / latest_price
                
                opportunities.append({
                    'symbol': symbol,
                    'strategy': strategy.name,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'current_price': latest_price,
                    'signal_strength': signal_strength,
                    'timestamp': datetime.now()
                })
    
    except Exception as e:
        logger.error(f"Error scanning {symbol}: {e}")
    
    return opportunities


async def main():
    logger.info("="*70)
    logger.info("NIFTY 50 STOCK SCANNER")
    logger.info("="*70)
    logger.info("")
    
    db = TimescaleClient()
    await db.connect()
    
    # Initialize strategies
    strategies = [
        EmaCrossoverStrategy(),
        SwingTrendStrategy(),
        ScalpingMeanReversionStrategy()
    ]
    
    logger.info(f"Scanning {len(NIFTY50_SYMBOLS)} Nifty 50 stocks...")
    logger.info(f"Using {len(strategies)} strategies")
    logger.info("")
    
    # Scan all stocks concurrently
    tasks = [scan_stock(db, symbol, strategies) for symbol in NIFTY50_SYMBOLS]
    results = await asyncio.gather(*tasks)
    
    # Flatten opportunities
    all_opportunities = [opp for stock_opps in results for opp in stock_opps]
    
    if not all_opportunities:
        logger.info("No trading opportunities found")
        await db.disconnect()
        return
    
    # Sort by signal strength (strongest first)
    all_opportunities.sort(key=lambda x: x['signal_strength'], reverse=True)
    
    # Display top 10 opportunities
    logger.info("="*70)
    logger.info(f"TOP 10 TRADING OPPORTUNITIES (out of {len(all_opportunities)})")
    logger.info("="*70)
    logger.info("")
    
    for i, opp in enumerate(all_opportunities[:10], 1):
        logger.info(f"{i}. {opp['symbol']}")
        logger.info(f"   Strategy: {opp['strategy']}")
        logger.info(f"   Signal: {opp['side']}")
        logger.info(f"   Entry: ₹{opp['entry_price']:.2f}")
        logger.info(f"   Current: ₹{opp['current_price']:.2f}")
        logger.info(f"   Strength: {opp['signal_strength']*100:.2f}%")
        logger.info("")
    
    # Return best opportunity for paper trading
    best = all_opportunities[0]
    logger.info("="*70)
    logger.info(f"🎯 BEST OPPORTUNITY: {best['symbol']} using {best['strategy']}")
    logger.info("="*70)
    
    await db.disconnect()
    
    return best


if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x scripts/run_stock_scanner.py

echo "✅ Stock scanner created!"
echo ""
echo "Test it:"
echo "  cd docker && docker compose run --rm data-service python scripts/run_stock_scanner.py"
