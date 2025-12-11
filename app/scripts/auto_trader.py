#!/usr/bin/env python3
"""
Automated Trading Bot - Places REAL orders when conditions are met
⚠️ WARNING: This trades with REAL MONEY. Test thoroughly in paper mode first!
"""

import asyncio
from datetime import datetime, timedelta, timezone
from core.timescale_client import TimescaleClient
from core.fyers_client import get_fyers_client
from analytics.strategies.intraday.ema_crossover import EmaCrossoverStrategy
from analytics.strategies.intraday.swing_trend import SwingTrendStrategy
from analytics.strategies.intraday.scalping_mean_reversion import ScalpingMeanReversionStrategy
from loguru import logger

class AutoTrader:
    def __init__(self, mode='paper'):
        """
        mode: 'paper' for simulation, 'live' for real trading
        """
        self.mode = mode
        self.db = TimescaleClient()
        self.fyers = get_fyers_client() if mode == 'live' else None
        self.active_positions = {}
        
        # Trading parameters
        self.position_size = 5000       # ₹5,000 per trade (safer for live)
        self.min_move_pct = 0.5         # 0.5% minimum move (more opportunities)
        self.min_net_profit = 25        # ₹25 after brokerage (realistic for smaller positions)
        self.brokerage = 48             # ₹48 per round trip
        self.live_buy_only = True       # 🔴 LIVE MODE: BUY positions only!
        
    async def scan_opportunities(self):
        """Scan for high-probability setups"""
        symbols = [
            'NSE:RELIANCE-EQ', 'NSE:TCS-EQ', 'NSE:INFY-EQ',
            'NSE:HDFCBANK-EQ', 'NSE:ICICIBANK-EQ'
        ]
        
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=5)
        
        opportunities = []
        
        for symbol in symbols:
            candles = await self.db.fetch_candles(symbol, '1m', start, end)
            if not candles or len(candles) < 100:
                continue
            
            strategies = [
                EmaCrossoverStrategy(symbol),
                SwingTrendStrategy(symbol),
                ScalpingMeanReversionStrategy(symbol)
            ]
            
            signals = []
            for strategy in strategies:
                for candle in candles:
                    await strategy.on_candle(candle)
                
                if strategy.position:
                    signals.append({
                        'strategy': strategy.__class__.__name__,
                        'side': strategy.position.get('side'),
                        'entry': strategy.position.get('entry_price'),
                        'current': candles[-1]['close']
                    })
            
            # Count by direction
            buy_signals = [s for s in signals if s['side'] == 'BUY']
            sell_signals = [s for s in signals if s['side'] == 'SELL']
            
            # 🔴 LIVE MODE: Filter for BUY only if live_buy_only is True
            if self.mode == 'live' and self.live_buy_only:
                dominant_signals = buy_signals if len(buy_signals) >= 2 else []
            else:
                # Paper mode: Allow both BUY and SELL
                dominant_signals = buy_signals if len(buy_signals) >= 2 else (sell_signals if len(sell_signals) >= 2 else [])
            
            if len(dominant_signals) >= 2:
                avg_entry = sum(s['entry'] for s in dominant_signals) / len(dominant_signals)
                current_price = candles[-1]['close']
                side = dominant_signals[0]['side']
                
                if side == 'BUY':
                    move_pct = ((current_price - avg_entry) / avg_entry) * 100
                else:  # SELL
                    move_pct = ((avg_entry - current_price) / avg_entry) * 100
                
                qty = int(self.position_size / current_price)
                gross_pnl = abs(current_price - avg_entry) * qty
                net_pnl = gross_pnl - self.brokerage
                
                # More lenient for live BUY-only mode
                min_move_threshold = 0.3 if (self.mode == 'live' and side == 'BUY') else self.min_move_pct
                
                if abs(move_pct) >= min_move_threshold and net_pnl > self.min_net_profit:
                    opportunities.append({
                        'symbol': symbol,
                        'side': side,
                        'entry': avg_entry,
                        'current': current_price,
                        'qty': qty,
                        'net_pnl': net_pnl,
                        'move_pct': move_pct,
                        'strategies': [s['strategy'] for s in dominant_signals]
                    })
        
        return opportunities
    
    async def place_order(self, opportunity):
        """Place order - paper or live"""
        symbol = opportunity['symbol']
        side = opportunity['side']
        qty = opportunity['qty']
        price = opportunity['current']
        net_pnl = opportunity['net_pnl']
        strategies = opportunity['strategies']
        
        logger.info(f"")
        logger.success(f"{'[PAPER TRADE]' if self.mode == 'paper' else '[🔴 LIVE ORDER 🔴]'}")
        logger.info(f"  Symbol: {symbol}")
        logger.info(f"  Action: {side} {qty} shares")
        logger.info(f"  Price: ₹{price:.2f}")
        logger.info(f"  Position Value: ₹{qty * price:,.0f}")
        logger.info(f"  Expected Net P&L: ₹{net_pnl:.2f}")
        logger.info(f"  Strategies: {', '.join([s.replace('Strategy', '') for s in strategies])}")
        
        if self.mode == 'live':
            # REAL ORDER PLACEMENT via Fyers API
            try:
                # Convert symbol format: NSE:TCS-EQ -> NSE:TCS-EQ
                order_data = {
                    "symbol": symbol,
                    "qty": qty,
                    "type": 2,  # Market order
                    "side": 1,  # Always BUY (1) in live mode
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
                    return response
                else:
                    logger.error(f"❌ Order failed: {response.get('message')}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Order error: {str(e)}")
                return None
        else:
            # PAPER TRADING
            logger.info(f"✅ Paper trade recorded (no real order)")
            return {'status': 'paper_trade', 'timestamp': datetime.now().isoformat()}
    
    async def run(self, interval=300):
        """Main loop - scan every interval seconds"""
        await self.db.connect()
        
        print("="*70)
        print(f"🤖 AUTO-TRADER STARTED")
        print("="*70)
        print(f"Mode: {self.mode.upper()}")
        if self.mode == 'live':
            print("🔴 WARNING: REAL MONEY TRADING ACTIVE 🔴")
            if self.live_buy_only:
                print("📈 LIVE MODE: BUY POSITIONS ONLY (No short selling)")
        print(f"Scan Interval: {interval} seconds ({interval/60:.1f} minutes)")
        print(f"Position Size: ₹{self.position_size:,}")
        print(f"Min Move: {self.min_move_pct}%")
        print(f"Min Net Profit: ₹{self.min_net_profit}")
        print(f"Brokerage: ₹{self.brokerage} per trade")
        print("="*70)
        print()
        
        try:
            scan_count = 0
            while True:
                scan_count += 1
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                logger.info(f"[Scan #{scan_count}] {timestamp} - Analyzing markets...")
                
                opportunities = await self.scan_opportunities()
                
                if opportunities:
                    logger.success(f"✅ Found {len(opportunities)} high-probability opportunities!")
                    print()
                    
                    for i, opp in enumerate(opportunities, 1):
                        # Check if not already in position
                        if opp['symbol'] not in self.active_positions:
                            print(f"Opportunity #{i}:")
                            await self.place_order(opp)
                            self.active_positions[opp['symbol']] = opp
                            print()
                        else:
                            logger.info(f"⏭️  Skipping {opp['symbol']} - already in position")
                else:
                    mode_msg = "2+ strategies agree on BUY" if (self.mode == 'live' and self.live_buy_only) else "2+ strategies agree on SAME DIRECTION"
                    logger.info("⏸️  No opportunities meet criteria")
                    logger.info(f"   Requirements: {mode_msg}, >{self.min_move_pct}% move, >₹{self.min_net_profit} net profit")
                
                logger.info(f"⏰ Next scan in {interval} seconds...")
                print()
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("")
            logger.warning("🛑 Auto-Trader stopped by user (Ctrl+C)")
            print()
            print("="*70)
            print("📊 SESSION SUMMARY")
            print("="*70)
            print(f"Total Scans: {scan_count}")
            print(f"Positions Taken: {len(self.active_positions)}")
            if self.active_positions:
                print("Symbols Traded:")
                for symbol, opp in self.active_positions.items():
                    print(f"  - {symbol}: {opp['side']} {opp['qty']} shares @ ₹{opp['current']:.2f}")
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
        print("⚠️  DANGER: LIVE TRADING MODE")
        print("="*70)
        print("This will place REAL orders with REAL money!")
        print("Losses are REAL and can exceed your capital.")
        print()
        print("🔴 LIVE MODE CONFIGURATION:")
        print("  - Only BUY positions will be placed (no short selling)")
        print("  - Position size: ₹5,000 per trade")
        print("  - Required margin: ~₹1,000 per trade")
        print()
        print("Have you:")
        print("  ✅ Tested in paper mode for at least 1 week?")
        print("  ✅ Verified strategies are profitable?")
        print("  ✅ Have at least ₹5,000 margin in your account?")
        print("  ✅ Understand you can only BUY (no short selling)?")
        print()
        confirm = input("Type 'I ACCEPT THE RISK' to proceed: ")
        if confirm != 'I ACCEPT THE RISK':
            print("Cancelled - Good decision! Test in paper mode first.")
            sys.exit(0)
        print()
    
    trader = AutoTrader(mode=mode)
    asyncio.run(trader.run(interval=300))
