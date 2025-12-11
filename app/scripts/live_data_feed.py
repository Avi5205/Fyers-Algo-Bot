#!/usr/bin/env python3
"""
Fyers WebSocket live data feed
Subscribes to real-time tick data and stores in TimescaleDB
"""
import asyncio
import os
from datetime import datetime, timezone
from fyers_apiv3.FyersWebsocket import data_ws
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Import your DB client
import sys
sys.path.append('/app')
from core.timescale_client import TimescaleClient


class FyersLiveFeed:
    def __init__(self, symbols):
        self.symbols = symbols
        self.db = None
        self.fyers_ws = None
        self.access_token = os.getenv("FYERS_ACCESS_TOKEN")
        
        if not self.access_token:
            raise RuntimeError("FYERS_ACCESS_TOKEN not set in .env")
    
    async def init_db(self):
        """Initialize database connection"""
        self.db = TimescaleClient()
        await self.db.connect()
        logger.info("Connected to TimescaleDB for live feed")
    
    def on_message(self, message):
        """Handle incoming WebSocket messages"""
        try:
            # Fyers sends tick data in this format
            # message = {'symbol': 'NSE:RELIANCE-EQ', 'ltp': 1234.5, 'timestamp': ...}
            logger.debug(f"Received tick: {message}")
            
            # Store tick (you can aggregate to 1m candles later)
            # For now, log it
            if isinstance(message, dict) and 'ltp' in message:
                symbol = message.get('symbol', 'UNKNOWN')
                price = message.get('ltp', 0)
                logger.info(f"[{symbol}] LTP: ₹{price:.2f}")
                
                # TODO: Aggregate ticks into 1m candles and insert into ohlcv_1m
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def on_error(self, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
    
    def on_close(self):
        """Handle WebSocket close"""
        logger.warning("WebSocket connection closed")
    
    def run(self):
        """Start WebSocket connection"""
        logger.info(f"Starting Fyers WebSocket for symbols: {self.symbols}")
        
        # Initialize Fyers WebSocket
        self.fyers_ws = data_ws.FyersDataSocket(
            access_token=self.access_token,
            log_path="logs",
            litemode=False,  # Set True for lite mode (less data)
            write_to_file=False,
            reconnect=True,
            on_connect=lambda: logger.info("WebSocket connected!"),
            on_close=self.on_close,
            on_error=self.on_error,
            on_message=self.on_message
        )
        
        # Subscribe to symbols (Fyers format: NSE:RELIANCE-EQ)
        self.fyers_ws.subscribe(symbols=self.symbols, data_type="SymbolUpdate")
        
        # Keep connection alive
        self.fyers_ws.keep_running()


async def main():
    # Symbols to subscribe (Fyers format)
    symbols = [
        "NSE:RELIANCE-EQ",
        "NSE:TCS-EQ",
        "NSE:INFY-EQ",
        "NSE:HDFCBANK-EQ",
        "NSE:ICICIBANK-EQ",
    ]
    
    feed = FyersLiveFeed(symbols)
    await feed.init_db()
    
    # Run WebSocket (blocking)
    feed.run()


if __name__ == "__main__":
    asyncio.run(main())
