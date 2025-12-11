#!/usr/bin/env python3
import asyncpg
import os
from loguru import logger

async def init_db():
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="trading_db",
        host="timescaledb",
        port=5432,
    )
    
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS ohlcv_1m (
        time TIMESTAMPTZ NOT NULL,
        symbol TEXT NOT NULL,
        exchange TEXT NOT NULL,
        open DOUBLE PRECISION,
        high DOUBLE PRECISION,
        low DOUBLE PRECISION,
        close DOUBLE PRECISION,
        volume BIGINT,
        PRIMARY KEY (time, symbol)
    );
    """)
    
    await conn.close()
    logger.info("Created ohlcv_1m table")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
