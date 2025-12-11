import os
from typing import List, Dict, Optional
from datetime import datetime
import asyncpg
import asyncio
from loguru import logger

class TimescaleClient:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", 5432))
        self.database = os.getenv("DB_NAME", "trading_db")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "trading123")

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info(f"Connected to TimescaleDB at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from TimescaleDB")

    async def insert_tick(self, tick_data: Dict):
        query = """
        INSERT INTO ticks (time, symbol, exchange, ltp, volume, bid, ask, bid_qty, ask_qty, oi)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                tick_data['time'],
                tick_data['symbol'],
                tick_data['exchange'],
                tick_data.get('ltp'),
                tick_data.get('volume'),
                tick_data.get('bid'),
                tick_data.get('ask'),
                tick_data.get('bid_qty'),
                tick_data.get('ask_qty'),
                tick_data.get('oi', 0)
            )

    async def insert_ohlcv(self, ohlcv_data: Dict):
        query = """
        INSERT INTO ohlcv_1m (time, symbol, exchange, open, high, low, close, volume)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (time, symbol) DO UPDATE
        SET open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                ohlcv_data['time'],
                ohlcv_data['symbol'],
                ohlcv_data['exchange'],
                ohlcv_data['open'],
                ohlcv_data['high'],
                ohlcv_data['low'],
                ohlcv_data['close'],
                ohlcv_data['volume']
            )

    async def get_ohlcv(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        table_map = {
            '1m': 'ohlcv_1m',
            '5m': 'ohlcv_5m',
            '15m': 'ohlcv_15m',
            '1h': 'ohlcv_1h',
            '1d': 'ohlcv_1d'
        }
        
        table = table_map.get(timeframe, 'ohlcv_1m')
        
        query = f"""
        SELECT time, symbol, exchange, open, high, low, close, volume
        FROM {table}
        WHERE symbol = $1 AND time >= $2 AND time <= $3
        ORDER BY time ASC
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, start_time, end_time)
            return [dict(row) for row in rows]

    async def insert_trade(self, trade_data: Dict):
        query = """
        INSERT INTO trades (time, symbol, exchange, order_id, transaction_type, quantity, price, status, strategy_name)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                trade_data['time'],
                trade_data['symbol'],
                trade_data['exchange'],
                trade_data.get('order_id'),
                trade_data['transaction_type'],
                trade_data['quantity'],
                trade_data['price'],
                trade_data['status'],
                trade_data.get('strategy_name')
            )

    async def get_latest_price(self, symbol: str) -> Optional[float]:
        query = """
        SELECT ltp FROM ticks
        WHERE symbol = $1
        ORDER BY time DESC
        LIMIT 1
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, symbol)
            return row['ltp'] if row else None
