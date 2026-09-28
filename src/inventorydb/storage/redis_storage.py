from typing import List, Optional

from inventorydb.interface import InventoryStorage


class RedisInventoryStorage(InventoryStorage):

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def select(self, item_type: str) -> List[dict]:
        keys = self.redis_client.keys(f"{item_type}:*")
        items = []
        for key in keys:
            item = self.redis_client.hgetall(key)
            items.append({k.decode('utf-8'): v.decode('utf-8') for k, v in item.items()})
        return items

    def write(self, item_type: str, item: dict) -> bool:
        key = f"{item_type}:{item['id']}"
        # Delete first so fields missing from the new item don't survive (replace, not merge).
        pipe = self.redis_client.pipeline(transaction=True)
        pipe.delete(key)
        pipe.hset(key, mapping=item)
        pipe.execute()
        return True

    def read(self, item_type: str, id: str) -> Optional[dict]:
        key = f"{item_type}:{id}"
        item = self.redis_client.hgetall(key)
        return {k.decode('utf-8'): v.decode('utf-8') for k, v in item.items()} if item else None

    def delete(self, item_type: str, id: str) -> bool:
        key = f"{item_type}:{id}"
        result = self.redis_client.delete(key)
        return result > 0
