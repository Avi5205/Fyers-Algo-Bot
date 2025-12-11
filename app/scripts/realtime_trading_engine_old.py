#!/usr/bin/env python3
"""
Real-Time Trading Engine - WebSocket streaming with live order placement
Streams live ticks, builds candles, analyzes strategies, and trades in real-time
"""

import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import json
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from core.timescale_client import TimescaleClient
from core.fyers_client import get_fyers_client
from analytics.strategies.intraday.ema_crossover import EmaCrossoverStrategy
from analytics.strategies.intraday.swing_trend import SwingTrendStrategy
from analytics.strategies.intraday.scalping_mean_reversion import ScalpingMeanReversionStrategy
from loguru import logger
import os

class RealtimeTradingEngine:
    def __init__(self, mode='paper'):
        self.mode = mode
        self.db = TimescaleClient()
        self.fyers = get_fyers_client()
        self.active_positions = {}
        
        # Trading parameters
        self.position_size = 5000
        self.min_move_pct = 0.5
        self.min_net_profit = 25
        self.brokerage = 48
        self.live_buy_only = True
        
        # Symbols to trade
        self.symbols = [
            'NSE:RELIANCE-EQ',
            'NSE:TCS-EQ',
            'NSE:INFY-EQ',
            'NSE:HDFCBANK-EQ',
            'NSE:ICICIBANK-EQ'
        ]
        
        # Real-time candle building
        self.current_candles = {}
        self.candle_buffer = defaultdict(list)
        self.strategies = {}
        self.last_tick_time = {}
        
        # WebSocket
        self.ws = None
        self.running = False
        self.loop = None
        
        # Initialize strategies for each symbol
        for symbol in self.symbols:
            self.strategies[symbol] = {
                'ema_crossover': EmaCrossoverStrategy(symbol),
                'swing_trend': SwingTrendStrategy(symbol),
                'scalping_mr': ScalpingMeanReversionStrategy(symbol)
            }
            self.current_candles[symbol] = None
            self.last_tick_time[symbol] = None
    
    async def load_historical_data(self):
        """Load recent historical data to initialize strategies"""
        logger.info("📚 Loading historical data to initialize strategies...")
        
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=2)
        
        for symbol in self.symbols:
            candles = await self.db.fetch_candles(symbol, '1m', start, end)
            
            if candles and len(candles) > 0:
                logger.info(f"✅ {symbol}: Loaded {len(candles)} historical candles")
                
                # Initialize strategies with historical data
                for strategy_name, strategy in self.strategies[symbol].items():
                    for candle in candles:
                        await strategy.on_candle(candle)
                
                # Store in buffer
                self.candle_buffer[symbol] = candles[-200:]
            else:
                logger.warning(f"⚠️  {symbol}: No historical data available")
    
    def on_tick(self, tick_data):
        """Handle incoming tick data from WebSocket"""
        try:
            # Fyers WebSocket sends data in different formats
            if isinstance(tick_data, dict):
                symbol = tick_data.get('symbol', tick_data.get('fyToken'))
                ltp = tick_data.get('ltp', tick_data.get('last_traded_price', tick_data.get('last_price')))
                volume = tick_data.get('vol_traded_today', tick_data.get('volume', 0))
            else:
                return
            
            if not symbol or symbol not in self.symbols:
                return
            
            if not ltp:
                return
            
            timestamp = datetime.now(timezone.utc)
            self.last_tick_time[symbol] = timestamp
            
            # Round timestamp to minute
            candle_time = timestamp.replace(second=0, microsecond=0)
            
            # Check if we need to start a new candle
            if self.current_candles[symbol] is None or self.current_candles[symbol]['timestamp'] != candle_time:
                # Save previous candle if exists
                if self.current_candles[symbol] is not None:
                    # Schedule candle close in event loop
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self.on_candle_close(symbol, self.current_candles[symbol]),
                            self.loop
                        )
                
                # Start new candle
                self.current_candles[symbol] = {
                    'symbol': symbol,
                    'timestamp': candle_time,
                    'open': float(ltp),
                    'high': float(ltp),
                    'low': float(ltp),
                    'close': float(ltp),
                    'volume': int(volume) if volume else 0,
                    'timeframe': '1m'
                }
            else:
                # Update current candle
                candle = self.current_candles[symbol]
                candle['high'] = max(candle['high'], float(ltp))
                candle['low'] = min(candle['low'], float(ltp))
                candle['close'] = float(ltp)
                candle['volume'] = int(volume) if volume else candle['volume']
            
        except Exception as e:
            logger.error(f"❌ Error processing tick: {str(e)}")
    
    async def on_candle_close(self, symbol, candle):
        """Called when a 1-minute candle is completed"""
        try:
            logger.debug(f"🕐 {symbol} Candle closed: {candle['timestamp'].strftime('%H:%M')} | "
                        f"O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f}")
            
            # Store in database - use pool.execute directly
            await self.db.pool.execute(
                """
                INSERT INTO candles (symbol, timestamp, open, high, low, close, volume, timeframe)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (symbol, timestamp, timeframe) DO UPDATE
                SET open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
                """,
                candle['symbol'],
                candle['timestamp'],
                candle['open'],
                candle['high'],
                candle['low'],
                candle['close'],
                candle['volume'],
                '1m'
            )
            
            # Add to buffer
            self.candle_buffer[symbol].append(candle)
            if len(self.candle_buffer[symbol]) > 200:
                self.candle_buffer[symbol].pop(0)
            
            # Update all strategies for this symbol
            for strategy_name, strategy in self.strategies[symbol].items():
                await strategy.on_candle(candle)
            
            # Check for trading opportunities
            await self.check_opportunities(symbol)
            
        except Exception as e:
            logger.error(f"❌ Error on candle close: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def check_opportunities(self, symbol):
        """Check if strategies agree and conditions are met for trading"""
        try:
            if symbol in self.active_positions:
                return
            
            # Get current positions from all strategies
            signals = []
            for strategy_name, strategy in self.strategies[symbol].items():
                if strategy.position:
                    signals.append({
                        'strategy': strategy.__class__.__name__,
                        'side': strategy.position.get('side'),
                        'entry': strategy.position.get('entry_price'),
                        'current': self.current_candles[symbol]['close'] if self.current_candles[symbol] else None
                    })
            
            if not signals or len(signals) < 2:
                return
            
            # Count by direction
            buy_signals = [s for s in signals if s['side'] == 'BUY']
            sell_signals = [s for s in signals if s['side'] == 'SELL']
            
            # Live mode: BUY only
            if self.mode == 'live' and self.live_buy_only:
                dominant_signals = buy_signals if len(buy_signals) >= 2 else []
            else:
                dominant_signals = buy_signals if len(buy_signals) >= 2 else (sell_signals if len(sell_signals) >= 2 else [])
            
            if len(dominant_signals) >= 2:
                avg_entry = sum(s['entry'] for s in dominant_signals) / len(dominant_signals)
                current_price = dominant_signals[0]['current']
                
                if not current_price:
                    return
                
                side = dominant_signals[0]['side']
                
                if side == 'BUY':
                    move_pct = ((current_price - avg_entry) / avg_entry) * 100
                else:
                    move_pct = ((avg_entry - current_price) / avg_entry) * 100
                
                qty = int(self.position_size / current_price)
                gross_pnl = abs(current_price - avg_entry) * qty
                net_pnl = gross_pnl - self.brokerage
                
                min_move_threshold = 0.3 if (self.mode == 'live' and side == 'BUY') else self.min_move_pct
                
                if abs(move_pct) >= min_move_threshold and net_pnl > self.min_net_profit:
                    opportunity = {
                        'symbol': symbol,
                        'side': side,
                        'entry': avg_entry,
                        'current': current_price,
                        'qty': qty,
                        'net_pnl': net_pnl,
                        'move_pct': move_pct,
                        'strategies': [s['strategy'] for s in dominant_signals],
                        'timestamp': datetime.now(timezone.utc)
                    }
                    
                    logger.success(f"🎯 {symbol}: OPPORTUNITY DETECTED!")
                    await self.place_order(opportunity)
            
        except Exception as e:
            logger.error(f"❌ Error checking opportunities: {str(e)}")
    
    async def place_order(self, opportunity):
        """Place order - paper or live"""
        symbol = opportunity['symbol']
        side = opportunity['side']
        qty = opportunity['qty']
        price = opportunity['current']
        net_pnl = opportunity['net_pnl']
        strategies = opportunity['strategies']
        
        logger.info("")
        logger.success(f"{'[PAPER TRADE]' if self.mode == 'paper' else '[🔴 LIVE ORDER 🔴]'}")
        logger.info(f"  Symbol: {symbol}")
        logger.info(f"  Action: {side} {qty} shares")
        logger.info(f"  Price: ₹{price:.2f}")
        logger.info(f"  Position Value: ₹{qty * price:,.0f}")
        logger.info(f"  Expected Net P&L: ₹{net_pnl:.2f}")
        logger.info(f"  Move: {opportunity['move_pct']:.2f}%")
        logger.info(f"  Strategies: {', '.join([s.replace('Strategy', '') for s in strategies])}")
        logger.info(f"  Timestamp: {opportunity['timestamp'].strftime('%H:%M:%S')}")
        
        if self.mode == 'live':
            try:
                order_data = {
                    "symbol": symbol,
                    "qty": qty,
                    "type": 2,
                    "side": 1,
                    "productType": "INTRADAY",
                    "validity": "DAY",
                    "offlineOrder": False,
                    "stopPrice": 0,
                    "limitPrice": 0
                }
                
                logger.warning("🔴 Placing LIVE BUY order with REAL money...")
                response = self.fyers.place_order(order_data)
                
                if response.get('s') == 'ok':
                    logger.success(f"✅ Order placed successfully!")
                    logger.info(f"   Order ID: {response.get('id')}")
                    self.active_positions[symbol] = opportunity
                    return response
                else:
                    logger.error(f"❌ Order failed: {response.get('message')}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Order error: {str(e)}")
                return None
        else:
            logger.info(f"✅ Paper trade recorded (no real order)")
            self.active_positions[symbol] = opportunity
            return {'status': 'paper_trade', 'timestamp': datetime.now().isoformat()}
    
    def start_websocket(self):
        """Start WebSocket connection to Fyers"""
        try:
            # Get access token from environment
            access_token = os.getenv('FYERS_ACCESS_TOKEN')
            if not access_token:
                raise ValueError("FYERS_ACCESS_TOKEN not found in environment")
            
            # Create WebSocket instance with correct callback signatures
            self.ws = data_ws.FyersDataSocket(
                access_token=access_token,
                log_path="",
                litemode=False,
                write_to_file=False,
                reconnect=True,
                on_connect=self._on_connect,
                on_close=self._on_close,
                on_error=self._on_error,
                on_message=self._on_message
            )
            
            logger.info("🔌 Connecting to Fyers WebSocket...")
            self.ws.connect()
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {str(e)}")
            raise
    
    def _on_connect(self):
        """WebSocket connected - NO msg parameter"""
        logger.success("✅ WebSocket connected!")
        
        # Subscribe to symbols
        data_type = "SymbolUpdate"
        self.ws.subscribe(symbols=self.symbols, data_type=data_type)
        self.ws.keep_running()
        
        logger.success(f"📡 Subscribed to {len(self.symbols)} symbols")
    
    def _on_close(self, msg):
        """WebSocket closed"""
        logger.warning(f"⚠️  WebSocket closed: {msg}")
    
    def _on_error(self, msg):
        """WebSocket error"""
        logger.error(f"❌ WebSocket error: {msg}")
    
    def _on_message(self, msg):
        """WebSocket message received"""
        try:
            # Process tick data
            self.on_tick(msg)
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
    
    async def run(self):
        """Main loop - start WebSocket and run indefinitely"""
        await self.db.connect()
        
        # Store event loop for WebSocket callbacks
        self.loop = asyncio.get_event_loop()
        
        print("="*70)
        print(f"🚀 REAL-TIME TRADING ENGINE STARTED")
        print("="*70)
        print(f"Mode: {self.mode.upper()}")
        if self.mode == 'live':
            print("🔴 WARNING: REAL MONEY TRADING ACTIVE 🔴")
            if self.live_buy_only:
                print("📈 LIVE MODE: BUY POSITIONS ONLY (No short selling)")
        print(f"Data Source: Fyers WebSocket (Real-time streaming)")
        print(f"Position Size: ₹{self.position_size:,}")
        print(f"Min Move: {self.min_move_pct}%")
        print(f"Min Net Profit: ₹{self.min_net_profit}")
        print(f"Symbols: {len(self.symbols)}")
        print("="*70)
        print()
        
        try:
            # Load historical data
            await self.load_historical_data()
            
            logger.info("🚀 Starting real-time data streaming...")
            
            # Start WebSocket in separate thread
            import threading
            ws_thread = threading.Thread(target=self.start_websocket, daemon=True)
            ws_thread.start()
            
            self.running = True
            
            # Status update every 30 seconds
            last_status = datetime.now(timezone.utc)
            
            # Keep main loop running
            while self.running:
                await asyncio.sleep(1)
                
                # Print status every 30 seconds
                now = datetime.now(timezone.utc)
                if (now - last_status).total_seconds() > 30:
                    active_symbols = [s for s, t in self.last_tick_time.items() if t and (now - t).total_seconds() < 60]
                    logger.info(f"📊 Status: {len(active_symbols)}/{len(self.symbols)} symbols receiving data | Positions: {len(self.active_positions)}")
                    last_status = now
                
        except KeyboardInterrupt:
            logger.info("")
            logger.warning("🛑 Real-Time Trading Engine stopped by user (Ctrl+C)")
            self.running = False
            
            if self.ws:
                self.ws.close()
            
            print()
            print("="*70)
            print("📊 SESSION SUMMARY")
            print("="*70)
            print(f"Positions Taken: {len(self.active_positions)}")
            if self.active_positions:
                print("Symbols Traded:")
                for symbol, opp in self.active_positions.items():
                    print(f"  - {symbol}: {opp['side']} {opp['qty']} shares @ ₹{opp['current']:.2f} at {opp['timestamp'].strftime('%H:%M:%S')}")
            else:
                print("No positions taken this session")
            print("="*70)
        finally:
            await self.db.disconnect()

if __name__ == "__main__":
    import sys
    
    mode = 'paper' if len(sys.argv) < 2 else sys.argv[1]
    
    if mode == 'live':
        print()
        print("="*70)
        print("⚠️  DANGER: LIVE TRADING MODE WITH REAL-TIME DATA")
        print("="*70)
        print("This will:")
        print("  • Stream live market data via WebSocket")
        print("  • Place REAL orders with REAL money INSTANTLY")
        print("  • React to market changes in <1 second")
        print()
        print("Have you:")
        print("  ✅ Tested in paper mode extensively?")
        print("  ✅ Have sufficient margin in your account?")
        print("  ✅ Understand orders execute IMMEDIATELY?")
        print("  ✅ Know how to stop the system quickly?")
        print()
        confirm = input("Type 'I ACCEPT THE RISK' to proceed: ")
        if confirm != 'I ACCEPT THE RISK':
            print("Cancelled - Good decision! Test in paper mode first.")
            sys.exit(0)
        print()
    
    engine = RealtimeTradingEngine(mode=mode)
    asyncio.run(engine.run())
