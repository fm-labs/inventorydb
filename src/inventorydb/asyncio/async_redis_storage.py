import json
from typing import List, Optional

from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.storage.redis_storage import DEFAULT_KEY_PREFIX, redis_type_key


class AsyncRedisInventoryStorage(AsyncInventoryStorage):
    """Async counterpart of ``RedisInventoryStorage``, using the same data layout."""

    def __init__(self, redis_client: "redis.asyncio.Redis", key_prefix: str = DEFAULT_KEY_PREFIX):
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    def _key(self, item_type: str) -> str:
        return redis_type_key(self.key_prefix, item_type)

    async def aselect(self, item_type: str) -> List[dict]:
        return [json.loads(value) for value in await self.redis_client.hvals(self._key(item_type))]

    async def awrite(self, item_type: str, item: dict) -> bool:
        await self.redis_client.hset(self._key(item_type), item["id"], json.dumps(item))
        return True

    async def aread(self, item_type: str, id: str) -> Optional[dict]:
        value = await self.redis_client.hget(self._key(item_type), id)
        return json.loads(value) if value is not None else None

    async def adelete(self, item_type: str, id: str) -> bool:
        return await self.redis_client.hdel(self._key(item_type), id) > 0
