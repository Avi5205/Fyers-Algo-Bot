"""
Backtesting engine for strategy evaluation
"""
from datetime import datetime, timedelta, timezone
from typing import Type, Dict, Any
from loguru import logger

from analytics.strategies.base_strategy import BaseStrategy


class BacktestEngine:
    """
    Event-driven backtesting engine
    """
    
    def __init__(self, db):
        self.db = db
        self.trades = []
        
    async def run(
        self,
        strategy_cls: Type[BaseStrategy],
        strategy_kwargs: Dict[str, Any],
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """
        Run backtest for a given strategy
        """
        # Initialize strategy
        strategy = strategy_cls(**strategy_kwargs)
        
        logger.info(
            f"Backtest {strategy.__class__.__name__} on {symbol} {timeframe} "
            f"from {start} to {end}"
        )
        
        # Fetch historical candles
        candles = await self.db.fetch_candles(symbol, timeframe, start, end)
        
        if not candles:
            logger.warning(f"No candles found for {symbol} in date range")
            return {
                'total_trades': 0,
                'pnl': 0.0,
                'win_rate': 0.0,
                'wins': 0,
                'losses': 0
            }
        
        # Process each candle (event-driven)
        for candle in candles:
            await strategy.on_candle(candle)
        
        # Get strategy stats
        stats = strategy.get_stats()
        
        logger.info(
            f"Backtest completed: {stats['total_trades']} trades, "
            f"PnL={stats['total_pnl']:.2f}, Wins={stats['winning_trades']}, "
            f"Losses={stats['losing_trades']}"
        )
        
        return {
            'total_trades': stats['total_trades'],
            'pnl': stats['total_pnl'],
            'win_rate': stats['win_rate'],
            'wins': stats['winning_trades'],
            'losses': stats['losing_trades'],
            'avg_win': stats.get('avg_win', 0),
            'avg_loss': stats.get('avg_loss', 0),
        }
