#!/usr/bin/env python3
"""
Real-Time Trading Engine - WebSocket streaming with live order placement
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
import threading  # WebSocket background thread


class RealtimeTradingEngine:
    def __init__(self, mode='paper'):
        self.mode = mode
        self.db = TimescaleClient()
        self.fyers = get_fyers_client()
        self.active_positions = {}
        self.trade_log = []  # track all trades for this session

        # Trading parameters
        self.position_size = 5000          # Rupees per position
        self.min_move_pct = 0.5           # Not yet enforced in execute_trade
        self.min_net_profit = 25          # Not yet enforced in execute_trade
        self.brokerage = 48
        self.live_buy_only = True         # You can enforce this in execute_trade if needed

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
            logger.info(f"📨 Received tick: {tick_data}")

            # Fyers sends data as dict or list of dicts
            if isinstance(tick_data, list):
                for tick in tick_data:
                    self._process_single_tick(tick)
            elif isinstance(tick_data, dict):
                self._process_single_tick(tick_data)
        except Exception as e:
            logger.error(f"❌ Error processing tick: {str(e)}")

    def _process_single_tick(self, tick):
        """Process a single tick"""
        try:
            # Extract symbol - try different field names
            symbol = (
                tick.get('symbol')
                or tick.get('fyToken')
                or tick.get('s')
                or tick.get('id')
            )

            # Subscription ack messages have no market symbol; skip them
            if tick.get('type') == 'sub' and tick.get('s') == 'ok':
                logger.debug("Skipping subscription confirmation message")
                return

            # Extract price - try different field names
            ltp = (
                tick.get('ltp')
                or tick.get('last_traded_price')
                or tick.get('last_price')
                or tick.get('lp')
                or (tick.get('v', {}).get('lp') if isinstance(tick.get('v'), dict) else None)
            )

            # Extract volume
            volume = (
                tick.get('vol_traded_today')
                or tick.get('volume')
                or (tick.get('v', {}).get('volume') if isinstance(tick.get('v'), dict) else 0)
            )

            if not symbol or symbol not in self.symbols:
                logger.debug(f"Skipping unknown symbol: {symbol}")
                return

            if not ltp:
                logger.debug(f"No price for {symbol}")
                return

            timestamp = datetime.now(timezone.utc)
            self.last_tick_time[symbol] = timestamp

            # Round timestamp to minute
            candle_time = timestamp.replace(second=0, microsecond=0)

            # Check if we need to start a new candle
            if (
                self.current_candles[symbol] is None
                or self.current_candles[symbol]['timestamp'] != candle_time
            ):
                # Save previous candle if exists
                if self.current_candles[symbol] is not None and self.loop:
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
                logger.debug(f"🕐 Started new candle for {symbol} at {candle_time}")
            else:
                # Update current candle
                candle = self.current_candles[symbol]
                candle['high'] = max(candle['high'], float(ltp))
                candle['low'] = min(candle['low'], float(ltp))
                candle['close'] = float(ltp)
                candle['volume'] = int(volume) if volume else candle['volume']

        except Exception as e:
            logger.error(f"❌ Error processing single tick: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    async def on_candle_close(self, symbol, candle):
        """Called when a 1-minute candle is completed"""
        try:
            logger.info(
                f"🕐 {symbol} Candle closed: {candle['timestamp'].strftime('%H:%M')} | "
                f"O:{candle['open']:.2f} H:{candle['high']:.2f} "
                f"L:{candle['low']:.2f} C:{candle['close']:.2f}"
            )

            # Save to database
            await self.db.pool.execute(
                """
                INSERT INTO ohlcv_1m (symbol, timestamp, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (symbol, timestamp) DO UPDATE
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
                candle['volume']
            )

            # Add to buffer
            self.candle_buffer[symbol].append(candle)
            if len(self.candle_buffer[symbol]) > 200:
                self.candle_buffer[symbol].pop(0)

            # Update all strategies with new candle
            for strategy_name, strategy in self.strategies[symbol].items():
                signal = await strategy.on_candle(candle)
                if signal:
                    logger.info(f"📊 {strategy_name} signal: {signal}")

            # Check for consensus signals
            await self.check_consensus(symbol, candle)

        except Exception as e:
            logger.error(f"❌ Error on candle close: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def check_consensus(self, symbol, candle):
        """Check if 2+ strategies agree on a signal"""
        try:
            buy_votes = 0
            sell_votes = 0

            for strategy_name, strategy in self.strategies[symbol].items():
                if hasattr(strategy, 'current_signal'):
                    signal = strategy.current_signal
                    if signal and signal.get('action') == 'BUY':
                        buy_votes += 1
                    elif signal and signal.get('action') == 'SELL':
                        sell_votes += 1

            # Require 2+ strategies to agree
            if buy_votes >= 2 and symbol not in self.active_positions:
                await self.execute_trade(symbol, 'BUY', candle['close'])
            elif sell_votes >= 2 and symbol in self.active_positions:
                await self.execute_trade(symbol, 'SELL', candle['close'])

        except Exception as e:
            logger.error(f"❌ Error checking consensus: {str(e)}")

    async def execute_trade(self, symbol, action, price):
        """Execute paper or live trade via Fyers, with clear logging."""
        try:
            qty = max(1, int(self.position_size / price))

            # Optional guard: only BUY in live mode if you want
            if self.mode == "live" and self.live_buy_only and action == "SELL":
                logger.info(f"ℹ️ Live SELL ignored due to live_buy_only=True | {symbol}")
                return

            if action == "BUY":
                if self.mode == "paper":
                    logger.success(f"📈 PAPER BUY: {symbol} x{qty} @ ₹{price:.2f}")
                    self.active_positions[symbol] = {
                        "qty": qty,
                        "entry_price": price,
                        "entry_time": datetime.now(timezone.utc),
                    }
                    # log trade
                    self.trade_log.append({
                        "time": datetime.now(timezone.utc),
                        "symbol": symbol,
                        "side": "BUY",
                        "qty": qty,
                        "price": price,
                        "mode": self.mode,
                        "pnl": 0.0,
                    })
                else:
                    order = {
                        "symbol": symbol,
                        "qty": qty,
                        "type": 1,          # 1 = MARKET, 2 = LIMIT
                        "side": 1,          # 1 = BUY, -1 = SELL
                        "productType": "INTRADAY",
                        "limitPrice": 0,
                        "stopPrice": 0,
                        "validity": "DAY",
                        "disclosedQty": 0,
                        "offlineOrder": False,
                    }
                    logger.info(f"ORDER-LIVE-REQ | BUY  | {symbol} | qty={qty} | data={order}")
                    resp = self.fyers.place_order(data=order)
                    logger.info(f"ORDER-LIVE-RESP | BUY  | {symbol} | resp={resp}")

                    self.active_positions[symbol] = {
                        "qty": qty,
                        "entry_price": price,
                        "entry_time": datetime.now(timezone.utc),
                        "order": resp,
                    }
                    # log trade (entry, PnL 0 here)
                    self.trade_log.append({
                        "time": datetime.now(timezone.utc),
                        "symbol": symbol,
                        "side": "BUY",
                        "qty": qty,
                        "price": price,
                        "mode": self.mode,
                        "pnl": 0.0,
                    })

            elif action == "SELL" and symbol in self.active_positions:
                position = self.active_positions[symbol]
                qty = position["qty"]
                pnl = (price - position["entry_price"]) * qty

                if self.mode == "paper":
                    logger.success(
                        f"📉 PAPER SELL: {symbol} x{qty} @ ₹{price:.2f} | PnL: ₹{pnl:.2f}"
                    )
                    del self.active_positions[symbol]
                    # log trade with realized PnL
                    self.trade_log.append({
                        "time": datetime.now(timezone.utc),
                        "symbol": symbol,
                        "side": "SELL",
                        "qty": qty,
                        "price": price,
                        "mode": self.mode,
                        "pnl": pnl,
                    })
                else:
                    order = {
                        "symbol": symbol,
                        "qty": qty,
                        "type": 1,          # MARKET sell
                        "side": -1,         # SELL
                        "productType": "INTRADAY",
                        "limitPrice": 0,
                        "stopPrice": 0,
                        "validity": "DAY",
                        "disclosedQty": 0,
                        "offlineOrder": False,
                    }
                    logger.info(f"ORDER-LIVE-REQ | SELL | {symbol} | qty={qty} | data={order}")
                    resp = self.fyers.place_order(data=order)
                    logger.info(
                        f"ORDER-LIVE-RESP | SELL | {symbol} | resp={resp} | PnL=₹{pnl:.2f}"
                    )
                    del self.active_positions[symbol]
                    # log trade with realized PnL (what the engine thinks)
                    self.trade_log.append({
                        "time": datetime.now(timezone.utc),
                        "symbol": symbol,
                        "side": "SELL",
                        "qty": qty,
                        "price": price,
                        "mode": self.mode,
                        "pnl": pnl,
                    })

        except Exception as e:
            logger.error(f"ORDER-LIVE-ERR | {action} | {symbol} | error={e}")
            import traceback
            logger.error(traceback.format_exc())

    def print_session_summary(self):
        """Print end-of-session summary based on trade_log."""
        logger.info("==== SESSION SUMMARY ====")
        if not self.trade_log:
            logger.info("No trades executed this session.")
            return

        total_pnl = sum(t["pnl"] for t in self.trade_log)
        logger.info(f"Total trades: {len(self.trade_log)}")
        logger.info(f"Total PnL (engine-side): ₹{total_pnl:.2f}")

        per_symbol = {}
        for t in self.trade_log:
            sym = t["symbol"]
            per_symbol.setdefault(sym, {"pnl": 0.0, "trades": 0})
            per_symbol[sym]["pnl"] += t["pnl"]
            per_symbol[sym]["trades"] += 1

        for sym, stats in per_symbol.items():
            logger.info(
                f"{sym}: trades={stats['trades']}, PnL=₹{stats['pnl']:.2f}"
            )

    def start_websocket(self):
        """Start Fyers WebSocket connection - corrected v3 usage"""
        try:
            logger.info("🔌 Connecting to Fyers WebSocket...")

            # 1. Get Access Token
            access_token = os.getenv('FYERS_ACCESS_TOKEN')
            if not access_token:
                raise ValueError("FYERS_ACCESS_TOKEN not found in environment")

            # 2. Ensure AppID:AccessToken format if needed
            if ':' not in access_token and os.getenv('FYERS_APP_ID'):
                app_id = os.getenv('FYERS_APP_ID')
                access_token = f"{app_id}:{access_token}"
                logger.info(f"🔑 Formatted access token with AppID: {app_id}")

            # 3. Define callbacks
            def on_message(message):
                """Callback for incoming messages"""
                # Filter out system messages like cn/ful/cp
                if isinstance(message, dict) and message.get('type') in ['cn', 'ful', 'cp']:
                    logger.debug(f"ℹ️ System Message: {message}")
                    return
                self.on_tick(message)

            def on_error(message):
                logger.error(f"❌ WebSocket error: {message}")

            def on_close(message):
                logger.warning(f"🔌 WebSocket closed: {message}")

            def on_open():
                """Callback when WebSocket connects"""
                logger.success("✅ WebSocket connected!")
                try:
                    data_type = "SymbolUpdate"
                    logger.info(f"📡 Subscribing to {len(self.symbols)} symbols...")
                    self.ws.subscribe(symbols=self.symbols, data_type=data_type)
                    logger.success(
                        f"✅ Subscription request sent for {len(self.symbols)} symbols"
                    )
                    # Do NOT call keep_running(); connect() handles loop
                except Exception as e:
                    logger.error(f"❌ Subscription failed: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())

            # 4. Create WebSocket instance
            self.ws = data_ws.FyersDataSocket(
                access_token=access_token,
                log_path="",
                litemode=False,
                write_to_file=False,
                reconnect=True,
                on_connect=on_open,
                on_close=on_close,
                on_error=on_error,
                on_message=on_message
            )

            # 5. Start in background thread (connect is blocking)
            ws_thread = threading.Thread(target=self.ws.connect, daemon=True)
            ws_thread.start()

            logger.info("🔌 WebSocket thread started")

        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    async def run(self):
        """Main run loop"""
        try:
            # Connect to database
            await self.db.connect()

            # Print banner
            print("=" * 70)
            print("🚀 REAL-TIME TRADING ENGINE STARTED")
            print("=" * 70)
            print(f"Mode: {self.mode.upper()}")
            print(f"Data Source: Fyers WebSocket (Real-time streaming)")
            print(f"Position Size: ₹{self.position_size:,}")
            print(f"Min Move: {self.min_move_pct}%")
            print(f"Min Net Profit: ₹{self.min_net_profit}")
            print(f"Symbols: {len(self.symbols)}")
            print("=" * 70)

            # Load historical data
            await self.load_historical_data()

            # Start WebSocket
            logger.info("🚀 Starting real-time data streaming...")
            self.loop = asyncio.get_event_loop()
            self.running = True
            self.start_websocket()

            # Main status loop
            while self.running:
                await asyncio.sleep(30)
                data_count = sum(1 for t in self.last_tick_time.values() if t)
                logger.info(
                    f"📊 Status: {data_count}/{len(self.symbols)} symbols receiving data | "
                    f"Positions: {len(self.active_positions)}"
                )

        except KeyboardInterrupt:
            logger.info("⚠️  Shutting down gracefully...")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Fatal error: {str(e)}")
            raise
        finally:
            # print session summary before disconnecting
            self.print_session_summary()
            await self.db.disconnect()


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else 'paper'

    if mode not in ['paper', 'live']:
        print("Usage: python realtime_trading_engine.py [paper|live]")
        sys.exit(1)

    engine = RealtimeTradingEngine(mode=mode)
    asyncio.run(engine.run())
