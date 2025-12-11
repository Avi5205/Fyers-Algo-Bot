import os
from contextlib import asynccontextmanager
import asyncpg
from loguru import logger


class TimescaleClient:
    def __init__(self):
        self.pool = None
        self._dsn = {
            "user": os.getenv("PGUSER", "postgres"),
            "password": os.getenv("PGPASSWORD", "postgres"),
            "database": os.getenv("PGDATABASE", "trading_db"),
            "host": os.getenv("PGHOST", "timescaledb"),
            "port": int(os.getenv("PGPORT", "5432")),
        }

    async def connect(self):
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(**self._dsn, min_size=2, max_size=10)
                logger.info(f"Connected to TimescaleDB at {self._dsn['host']}:{self._dsn['port']}")
            except Exception as e:
                logger.error(f"Failed to connect to TimescaleDB: {e}")
                raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from TimescaleDB")
            self.pool = None

    async def fetch_candles(self, symbol: str, timeframe: str, start, end):
        """Fetch OHLCV candles from ohlcv_1m table - returns dict format"""
        if self.pool is None:
            raise RuntimeError("TimescaleClient not connected")

        query = """
        SELECT time, symbol, exchange, open, high, low, close, volume
        FROM ohlcv_1m
        WHERE symbol = $1 AND time >= $2 AND time <= $3
        ORDER BY time ASC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, start, end)
            return [dict(r) for r in rows]

    async def get_ohlcv(self, symbol: str, timeframe: str, start, end):
        """Alias for fetch_candles - compatibility with Dhan engine"""
        return await self.fetch_candles(symbol, timeframe, start, end)

    async def insert_ohlcv_1m(self, ohlcv: dict):
        """Insert with ON CONFLICT DO NOTHING (idempotent)"""
        if self.pool is None:
            raise RuntimeError("TimescaleClient not connected")

        q = """
        INSERT INTO ohlcv_1m(time, symbol, exchange, open, high, low, close, volume)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (time, symbol) DO NOTHING
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                q,
                ohlcv["time"],
                ohlcv["symbol"],
                ohlcv["exchange"],
                ohlcv["open"],
                ohlcv["high"],
                ohlcv["low"],
                ohlcv["close"],
                ohlcv["volume"],
            )
