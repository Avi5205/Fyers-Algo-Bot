"""
Paper trading engine - simulates live trading without real money
"""
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger
from analytics.risk.manager import RiskManager


class PaperTradingEngine:
    """
    Paper trading engine that executes strategies in real-time simulation
    """
    
    def __init__(self, strategy, risk_manager: RiskManager = None):
        self.strategy = strategy
        self.risk_manager = risk_manager or RiskManager()
        self.is_running = False
        
    async def start(self, db, symbol, live_feed=False):
        """
        Start paper trading
        live_feed: if True, use WebSocket live data; else use recent DB candles
        """
        self.is_running = True
        
        logger.info(f"[PaperTrading] Started for {symbol} using {self.strategy.name}")
        logger.info(f"[PaperTrading] Initial capital: ₹{self.risk_manager.current_capital:.2f}")
        
        if live_feed:
            logger.warning("[PaperTrading] Live feed mode not yet implemented, using DB polling")
        
        # Poll database for new candles (simulated live)
        while self.is_running:
            try:
                # Get latest candle
                end = datetime.now(timezone.utc)
                start = end - timedelta(minutes=2)
                
                candles = await db.fetch_candles(symbol, '1m', start, end)
                
                if candles:
                    latest = candles[-1]
                    
                    # Check risk management (stop-loss, take-profit)
                    if self.risk_manager.check_stop_loss(symbol, latest['close']):
                        logger.warning(f"[PaperTrading] STOP LOSS HIT for {symbol}")
                        self.risk_manager.close_position(symbol, latest['close'])
                        await self.strategy.on_candle(latest)
                    
                    elif self.risk_manager.check_take_profit(symbol, latest['close']):
                        logger.info(f"[PaperTrading] TAKE PROFIT HIT for {symbol}")
                        self.risk_manager.close_position(symbol, latest['close'])
                        await self.strategy.on_candle(latest)
                    
                    else:
                        # Execute strategy logic
                        await self.strategy.on_candle(latest)
                
                # Wait for next candle (1 minute)
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"[PaperTrading] Error: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop paper trading"""
        self.is_running = False
        logger.info("[PaperTrading] Stopped")
        
        # Print statistics
        stats = self.risk_manager.get_stats()
        
        logger.info(f"\n{'='*70}")
        logger.info("PAPER TRADING SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Total Trades: {stats.get('total_trades', 0)}")
        logger.info(f"Winning Trades: {stats.get('winning_trades', 0)}")
        logger.info(f"Losing Trades: {stats.get('losing_trades', 0)}")
        logger.info(f"Win Rate: {stats.get('win_rate', 0.0):.1f}%")
        logger.info(f"Total PnL: ₹{stats.get('total_pnl', 0.0):.2f}")
        
        # Safely get final_capital with fallback
        final_capital = stats.get('final_capital', self.risk_manager.current_capital)
        logger.info(f"Final Capital: ₹{final_capital:.2f}")
        
        # Calculate return
        initial_capital = self.risk_manager.initial_capital
        return_pct = ((final_capital - initial_capital) / initial_capital * 100)
        logger.info(f"Return: {return_pct:.2f}%")
        logger.info(f"{'='*70}\n")
