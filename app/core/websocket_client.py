import asyncio
import json
from typing import List, Callable
from datetime import datetime
from loguru import logger

class DhanWebSocketClient:
    """
    Placeholder WebSocket client for Week 1
    Real implementation will use dhanhq.marketfeed in Week 2
    """
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.connection = None
        self.subscribed_symbols = []
        self.callbacks = []
        self.running = False

    async def connect(self):
        logger.info("WebSocket client initialized (placeholder mode)")
        self.running = True

    async def subscribe(self, symbols: List[dict], callback: Callable):
        self.callbacks.append(callback)
        self.subscribed_symbols.extend(symbols)
        
        logger.info(f"Subscribed to {len(symbols)} symbols (placeholder mode)")
        
        # Simulate tick data for testing
        await self._simulate_ticks()

    async def _simulate_ticks(self):
        """Generate fake tick data for testing"""
        import random
        
        while self.running:
            for symbol_info in self.subscribed_symbols:
                tick_data = {
                    'time': datetime.now(),
                    'symbol': symbol_info['symbol'],
                    'exchange': symbol_info['exchange'],
                    'ltp': round(random.uniform(1000, 3000), 2),
                    'volume': random.randint(1000, 100000),
                    'bid': round(random.uniform(1000, 3000), 2),
                    'ask': round(random.uniform(1000, 3000), 2),
                    'bid_qty': random.randint(100, 10000),
                    'ask_qty': random.randint(100, 10000),
                    'oi': 0
                }
                
                for callback in self.callbacks:
                    await callback(tick_data)
            
            await asyncio.sleep(5)  # Generate tick every 5 seconds

    async def disconnect(self):
        self.running = False
        logger.info("WebSocket disconnected")
