import json

from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.interface import Item
from inventorydb.storage.redis_storage import DEFAULT_KEY_PREFIX, RedisHashClient, redis_type_key


class AsyncRedisInventoryStorage(AsyncInventoryStorage):
    """Async counterpart of ``RedisInventoryStorage``, using the same data layout.

    Takes an async client such as ``redis.asyncio.Redis``.
    """

    def __init__(self, redis_client: RedisHashClient, key_prefix: str = DEFAULT_KEY_PREFIX):
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    def _key(self, item_type: str) -> str:
        return redis_type_key(self.key_prefix, item_type)

    async def aselect(self, item_type: str) -> list[Item]:
        return [json.loads(value) for value in await self.redis_client.hvals(self._key(item_type))]

    async def awrite(self, item_type: str, item: Item) -> bool:
        await self.redis_client.hset(self._key(item_type), item["id"], json.dumps(item))
        return True

    async def aread(self, item_type: str, id: str) -> Item | None:
        value = await self.redis_client.hget(self._key(item_type), id)
        return json.loads(value) if value is not None else None

    async def adelete(self, item_type: str, id: str) -> bool:
        return bool(await self.redis_client.hdel(self._key(item_type), id))
