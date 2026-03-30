from typing import List

from inventorydb.interface import InventoryStorage


class RedisInventoryStorage(InventoryStorage):

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def select(self, inventory_type: str) -> List[dict]:
        keys = self.redis_client.keys(f"{inventory_type}:*")
        items = []
        for key in keys:
            item = self.redis_client.hgetall(key)
            items.append({k.decode('utf-8'): v.decode('utf-8') for k, v in item.items()})
        return items

    def write(self, inventory_type: str, item: dict) -> bool:
        key = f"{inventory_type}:{item['id']}"
        self.redis_client.hset(key, mapping=item)
        return True

    def read(self, inventory_type: str, id: str) -> dict:
        key = f"{inventory_type}:{id}"
        item = self.redis_client.hgetall(key)
        return {k.decode('utf-8'): v.decode('utf-8') for k, v in item.items()} if item else {}

    def delete(self, inventory_type: str, id: str) -> bool:
        key = f"{inventory_type}:{id}"
        result = self.redis_client.delete(key)
        return result > 0