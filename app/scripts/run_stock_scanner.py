"""
Multi-Stock Scanner - Finds best trading opportunities
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from loguru import logger

sys.path.insert(0, '/app')

from core.timescale_client import TimescaleClient
from analytics.strategies.intraday.ema_crossover import EmaCrossoverStrategy
from analytics.strategies.intraday.swing_trend import SwingTrendStrategy
from analytics.strategies.intraday.scalping_mean_reversion import ScalpingMeanReversionStrategy


async def scan_stock(db, symbol):
    """Scan a single stock with all strategies"""
    opportunities = []
    
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=2)
    
    try:
        candles = await db.fetch_candles(symbol, '1m', start, end)
        if not candles or len(candles) < 50:
            return opportunities
        
        latest_price = candles[-1]['close']
        
        strategies = [
            ('EMA Crossover', EmaCrossoverStrategy(symbol)),
            ('Swing Trend', SwingTrendStrategy(symbol)),
            ('Scalping Mean Reversion', ScalpingMeanReversionStrategy(symbol))
        ]
        
        for strategy_name, strategy in strategies:
            for candle in candles[-50:]:
                await strategy.on_candle(candle)
            
            if strategy.position and strategy.position.get('quantity', 0) != 0:
                entry_price = strategy.position.get('entry_price', latest_price)
                side = 'BUY' if strategy.position.get('quantity', 0) > 0 else 'SELL'
                signal_strength = abs(latest_price - entry_price) / latest_price
                
                opportunities.append({
                    'symbol': symbol,
                    'strategy': strategy_name,
                    'side': side,
                    'entry_price': entry_price,
                    'current_price': latest_price,
                    'signal_strength': signal_strength,
                    'pnl': (latest_price - entry_price) if side == 'BUY' else (entry_price - latest_price)
                })
    
    except Exception as e:
        logger.debug(f"Error scanning {symbol}: {e}")
    
    return opportunities


async def main():
    logger.info("="*70)
    logger.info("NIFTY 50 STOCK SCANNER")
    logger.info("="*70)
    logger.info("")
    
    db = TimescaleClient()
    await db.connect()
    
    symbols = ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:INFY-EQ", 
               "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ"]
    
    logger.info(f"📊 Scanning {len(symbols)} stocks...")
    logger.info(f"🎯 Using 3 strategies per stock (15 combinations)")
    logger.info("")
    
    tasks = [scan_stock(db, symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    
    all_opportunities = [opp for stock_opps in results for opp in stock_opps]
    
    if not all_opportunities:
        logger.warning("⚠️  No open positions found")
        logger.info("")
        logger.info("Strategies generated signals but closed them immediately")
        logger.info("(Scalping strategy exits within same candle)")
        logger.info("")
        logger.info("💡 Try running paper trading to catch live signals!")
        await db.disconnect()
        return None
    
    all_opportunities.sort(key=lambda x: x['signal_strength'], reverse=True)
    
    logger.info("="*70)
    logger.info(f"🏆 OPEN POSITIONS ({len(all_opportunities)} found)")
    logger.info("="*70)
    logger.info("")
    
    for i, opp in enumerate(all_opportunities[:10], 1):
        pnl_icon = "📈" if opp['pnl'] > 0 else "📉"
        logger.info(f"{i}. {opp['symbol']}")
        logger.info(f"   Strategy: {opp['strategy']}")
        logger.info(f"   Signal: {opp['side']}")
        logger.info(f"   Entry: ₹{opp['entry_price']:.2f}")
        logger.info(f"   Current: ₹{opp['current_price']:.2f}")
        logger.info(f"   {pnl_icon} P&L: ₹{opp['pnl']:.2f}")
        logger.info(f"   Strength: {opp['signal_strength']*100:.2f}%")
        logger.info("")
    
    best = all_opportunities[0]
    logger.success(f"🎯 BEST: {best['symbol']} - {best['strategy']}")
    logger.success(f"   {best['side']} @ ₹{best['entry_price']:.2f}")
    
    await db.disconnect()
    return best


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️  Stopped")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
