    async def fetch_candles(self, symbol: str, timeframe: str, start, end):
        """Fetch OHLCV candles from ohlcv_1m table"""
        if self.pool is None:
            raise RuntimeError("TimescaleClient not connected")

        query = """
        SELECT time, symbol, open, high, low, close, volume
        FROM ohlcv_1m
        WHERE symbol = $1 AND time >= $2 AND time <= $3
        ORDER BY time ASC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, start, end)
            # Convert to dict format expected by engine
            return [dict(r) for r in rows]

    async def get_ohlcv(self, symbol: str, timeframe: str, start, end):
        """Alias for fetch_candles - compatibility with Dhan engine"""
        return await self.fetch_candles(symbol, timeframe, start, end)
