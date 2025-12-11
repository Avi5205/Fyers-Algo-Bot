#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta, timezone
import sys
sys.path.append('/app')

from core.timescale_client import TimescaleClient
from analytics.backtest.engine import BacktestEngine
from analytics.strategies.intraday.ema_crossover import EmaCrossoverStrategy

async def main():
    db = TimescaleClient()
    await db.connect()
    
    engine = BacktestEngine(db)
    
    # Run backtest on Fyers RELIANCE data (last 5 days of 1m candles)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=5)
    
    result = await engine.run(
        strategy_cls=EmaCrossoverStrategy,
        strategy_kwargs={
            'symbol': 'NSE:RELIANCE-EQ',
            'fast_period': 9,
            'slow_period': 21
        },
        symbol='NSE:RELIANCE-EQ',  # FYERS format!
        timeframe='1m',
        start=start,
        end=end,
    )
    
    print(f"\n{'='*60}")
    print(f"BACKTEST RESULTS - EmaCrossoverStrategy")
    print(f"{'='*60}")
    print(f"Symbol: NSE:RELIANCE-EQ")
    print(f"Period: {start.date()} to {end.date()}")
    print(f"Total Trades: {result.get('total_trades', 0)}")
    print(f"PnL: ₹{result.get('pnl', 0):.2f}")
    print(f"Win Rate: {result.get('win_rate', 0):.1f}%")
    print(f"{'='*60}\n")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
