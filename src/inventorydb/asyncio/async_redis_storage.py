from typing import List

from inventorydb.asyncio.async_storage import AsyncInventoryStorage


class AsyncRedisInventoryStorage(AsyncInventoryStorage):

    def __init__(self, redis_client: "redis.asyncio.Redis"):
        self.redis_client = redis_client

    async def aselect(self, inventory_type: str) -> List[dict]:
        keys = await self.redis_client.keys(f"{inventory_type}:*")
        items = []
        for key in keys:
            item = await self.redis_client.hgetall(key)
            if item:
                items.append(item)
        return items

    async def awrite(self, inventory_type: str, item: dict) -> bool:
        key = f"{inventory_type}:{item['id']}"
        await self.redis_client.hset(key, mapping=item)
        return True

    async def aread(self, inventory_type: str, id: str) -> dict:
        key = f"{inventory_type}:{id}"
        item = await self.redis_client.hgetall(key)
        return item if item else {}

    async def adelete(self, inventory_type: str, id: str) -> bool:
        key = f"{inventory_type}:{id}"
        result = await self.redis_client.delete(key)
        return result > 0
