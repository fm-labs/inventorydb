from typing import List, Optional

from inventorydb.asyncio.async_storage import AsyncInventoryStorage


class AsyncRedisInventoryStorage(AsyncInventoryStorage):

    def __init__(self, redis_client: "redis.asyncio.Redis"):
        self.redis_client = redis_client

    async def aselect(self, item_type: str) -> List[dict]:
        keys = await self.redis_client.keys(f"{item_type}:*")
        items = []
        for key in keys:
            item = await self.redis_client.hgetall(key)
            if item:
                items.append(item)
        return items

    async def awrite(self, item_type: str, item: dict) -> bool:
        key = f"{item_type}:{item['id']}"
        # Delete first so fields missing from the new item don't survive (replace, not merge).
        async with self.redis_client.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            pipe.hset(key, mapping=item)
            await pipe.execute()
        return True

    async def aread(self, item_type: str, id: str) -> Optional[dict]:
        key = f"{item_type}:{id}"
        item = await self.redis_client.hgetall(key)
        return item if item else None

    async def adelete(self, item_type: str, id: str) -> bool:
        key = f"{item_type}:{id}"
        result = await self.redis_client.delete(key)
        return result > 0
