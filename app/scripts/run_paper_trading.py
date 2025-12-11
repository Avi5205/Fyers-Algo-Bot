#!/usr/bin/env python3
"""
Run paper trading simulation
"""
import asyncio
import signal
import sys
sys.path.append('/app')

from core.timescale_client import TimescaleClient
from analytics.paper_trading.engine import PaperTradingEngine
from analytics.strategies.intraday.swing_trend import SwingTrendStrategy
from analytics.risk.manager import RiskManager
from loguru import logger


# Global engine for signal handling
paper_engine = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    logger.info("\n[SIGINT] Stopping paper trading...")
    if paper_engine:
        paper_engine.stop()
    sys.exit(0)


async def main():
    global paper_engine
    
    # Initialize
    db = TimescaleClient()
    await db.connect()
    
    # Create strategy
    strategy = SwingTrendStrategy(
        symbol='NSE:RELIANCE-EQ',
        rsi_period=14,
        ma_period=50
    )
    
    # Create risk manager
    risk_mgr = RiskManager(
        initial_capital=100000.0,
        max_risk_per_trade=0.02,
        stop_loss_pct=0.02,
        take_profit_pct=0.04
    )
    
    # Create paper trading engine
    paper_engine = PaperTradingEngine(strategy, risk_mgr)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("="*70)
    logger.info("PAPER TRADING MODE - Press Ctrl+C to stop")
    logger.info("="*70)
    
    # Start paper trading (non-blocking simulation)
    await paper_engine.start(db, 'NSE:RELIANCE-EQ', live_feed=False)
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
