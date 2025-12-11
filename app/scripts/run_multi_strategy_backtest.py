#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta, timezone
import sys
sys.path.append('/app')

from core.timescale_client import TimescaleClient
from analytics.backtest.engine import BacktestEngine
from analytics.strategies.intraday.ema_crossover import EmaCrossoverStrategy
from analytics.strategies.intraday.swing_trend import SwingTrendStrategy
from analytics.strategies.intraday.scalping_mean_reversion import ScalpingMeanReversionStrategy


async def run_strategy(db, strategy_cls, strategy_name, symbol, params):
    """Run single strategy backtest"""
    engine = BacktestEngine(db)
    
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=5)
    
    print(f"\n{'='*70}")
    print(f"Running {strategy_name} on {symbol}")
    print(f"{'='*70}")
    
    result = await engine.run(
        strategy_cls=strategy_cls,
        strategy_kwargs={'symbol': symbol, **params},
        symbol=symbol,
        timeframe='1m',
        start=start,
        end=end,
    )
    
    return {
        'strategy': strategy_name,
        'symbol': symbol,
        'result': result
    }


async def main():
    db = TimescaleClient()
    await db.connect()
    
    # Define symbols to test
    symbols = [
        'NSE:RELIANCE-EQ',
        'NSE:TCS-EQ',
        'NSE:INFY-EQ',
        'NSE:HDFCBANK-EQ',
        'NSE:ICICIBANK-EQ',
    ]
    
    # Define strategies with parameters
    strategies = [
        {
            'cls': EmaCrossoverStrategy,
            'name': 'EMA Crossover',
            'params': {'fast_period': 9, 'slow_period': 21}
        },
        {
            'cls': SwingTrendStrategy,
            'name': 'Swing Trend (RSI+MA)',
            'params': {'rsi_period': 14, 'ma_period': 50}
        },
        {
            'cls': ScalpingMeanReversionStrategy,
            'name': 'Scalping Mean Reversion (BB)',
            'params': {'bb_period': 20, 'bb_std': 2.0}
        },
    ]
    
    # Run all combinations
    all_results = []
    
    for symbol in symbols:
        for strategy in strategies:
            result = await run_strategy(
                db,
                strategy['cls'],
                strategy['name'],
                symbol,
                strategy['params']
            )
            all_results.append(result)
            
            # Print summary
            res = result['result']
            print(f"\nStrategy: {result['strategy']}")
            print(f"Symbol: {result['symbol']}")
            print(f"Total Trades: {res.get('total_trades', 0)}")
            print(f"PnL: ₹{res.get('pnl', 0):.2f}")
            print(f"Win Rate: {res.get('win_rate', 0):.1f}%")
            print("-" * 70)
    
    # Summary report
    print(f"\n\n{'='*70}")
    print("OVERALL SUMMARY - ALL STRATEGIES & SYMBOLS")
    print(f"{'='*70}\n")
    
    print(f"{'Strategy':<30} {'Symbol':<20} {'Trades':<10} {'PnL':>12} {'WinRate':>10}")
    print("-" * 70)
    
    for result in all_results:
        res = result['result']
        print(f"{result['strategy']:<30} {result['symbol']:<20} "
              f"{res.get('total_trades', 0):<10} "
              f"₹{res.get('pnl', 0):>10.2f} "
              f"{res.get('win_rate', 0):>9.1f}%")
    
    # Best performers
    sorted_results = sorted(all_results, key=lambda x: x['result'].get('pnl', 0), reverse=True)
    
    print(f"\n{'='*70}")
    print("TOP 3 BEST PERFORMERS")
    print(f"{'='*70}\n")
    
    for i, result in enumerate(sorted_results[:3], 1):
        res = result['result']
        print(f"{i}. {result['strategy']} on {result['symbol']}")
        print(f"   PnL: ₹{res.get('pnl', 0):.2f} | Trades: {res.get('total_trades', 0)} | Win Rate: {res.get('win_rate', 0):.1f}%\n")
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
