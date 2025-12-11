import os
import json
from typing import Optional, Callable
import redis.asyncio as aioredis
from loguru import logger
from datetime import datetime, date

def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"Type {type(o)} not serializable")

class RedisClient:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))

    async def connect(self):
        try:
            self.client = await aioredis.from_url(
                f"redis://{self.host}:{self.port}",
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")

    async def publish(self, channel: str, message: dict):
        if self.client:
            payload = json.dumps(message, default=_json_default)
            await self.client.publish(channel, payload)

    async def subscribe(self, channel: str, callback: Callable):
        if not self.client:
            raise Exception("Redis client not connected")
        
        self.pubsub = self.client.pubsub()
        await self.pubsub.subscribe(channel)
        
        logger.info(f"Subscribed to channel: {channel}")
        
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

    async def set(self, key: str, value: dict, ex: int = None):
        if self.client:
            payload = json.dumps(value, default=_json_default)
            await self.client.set(key, payload, ex=ex)

    async def get(self, key: str) -> Optional[dict]:
        if self.client:
            value = await self.client.get(key)
            return json.loads(value) if value else None
        return None

    async def delete(self, key: str):
        if self.client:
            await self.client.delete(key)
