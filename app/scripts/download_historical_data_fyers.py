import asyncio
import os
from datetime import datetime, timedelta, timezone

from loguru import logger
from dotenv import load_dotenv

from core.fyers_client import get_fyers_client
from core.timescale_client import TimescaleClient

load_dotenv()


class FyersHistoricalDownloader:
    def __init__(self):
        self.fyers = get_fyers_client()
        self.db = TimescaleClient()

    async def download_symbol(
        self,
        symbol: str,
        exchange: str = "NSE",
        days: int = 30,
    ):
        """
        Fetch 1-minute candles via fyers.history and store into ohlcv_1m.
        symbol: FYERS symbol, e.g. 'NSE:RELIANCE-EQ'
        """
        end_date = datetime.now(tz=timezone.utc)
        start_date = end_date - timedelta(days=days)

        range_from = start_date.strftime("%Y-%m-%d")
        range_to = end_date.strftime("%Y-%m-%d")

        logger.info(f"Downloading {symbol} from {range_from} to {range_to}")

        data = {
            "symbol": symbol,
            "resolution": "1",      # 1-minute
            "date_format": "1",     # yyyy-mm-dd
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1",
        }

        try:
            resp = self.fyers.history(data=data)
        except Exception as e:
            logger.error(f"Fyers history call failed for {symbol}: {e}")
            return

        if not isinstance(resp, dict) or "candles" not in resp:
            logger.error(f"Unexpected Fyers history response for {symbol}: {resp}")
            return

        candles = resp.get("candles", [])
        if not candles:
            logger.warning(f"No candles received for {symbol}")
            return

        logger.info(f"Received {len(candles)} candles for {symbol}")

        for c in candles:
            # Fyers format: [timestamp, open, high, low, close, volume]
            # timestamp is epoch seconds.
            try:
                ts, o, h, l, cl, v = c
            except ValueError:
                logger.error(f"Malformed candle for {symbol}: {c}")
                continue

            dt = datetime.fromtimestamp(ts, tz=timezone.utc)

            ohlcv = {
                "time": dt,
                "symbol": symbol,
                "exchange": exchange,
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(cl),
                "volume": int(v),
            }
            await self.db.insert_ohlcv_1m(ohlcv)

        logger.info(f"Inserted {len(candles)} candles for {symbol} into ohlcv_1m")

    async def download_all(self):
        await self.db.connect()

        symbols = [
            "NSE:RELIANCE-EQ",
            "NSE:TCS-EQ",
            "NSE:INFY-EQ",
            "NSE:HDFCBANK-EQ",
            "NSE:ICICIBANK-EQ",
        ]

        for sym in symbols:
            await self.download_symbol(sym, exchange="NSE", days=30)
            await asyncio.sleep(1)

        await self.db.disconnect()
        logger.info("Fyers historical data download completed")


async def main():
    downloader = FyersHistoricalDownloader()
    await downloader.download_all()


if __name__ == "__main__":
    asyncio.run(main())
