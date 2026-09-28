import json
from typing import List, Optional

from inventorydb.interface import InventoryStorage

DEFAULT_KEY_PREFIX = "inventory:"


def redis_type_key(key_prefix: str, item_type: str) -> str:
    """Name of the Redis hash that holds all items of ``item_type``, keyed by id."""
    return f"{key_prefix}{item_type}"


class RedisInventoryStorage(InventoryStorage):
    """Redis-backed storage.

    Each item type is one Redis hash (``{key_prefix}{item_type}``) mapping item
    ids to JSON-encoded items. Works with clients created with or without
    ``decode_responses=True``.
    """

    def __init__(self, redis_client, key_prefix: str = DEFAULT_KEY_PREFIX):
        self.redis_client = redis_client
        self.key_prefix = key_prefix

    def _key(self, item_type: str) -> str:
        return redis_type_key(self.key_prefix, item_type)

    def select(self, item_type: str) -> List[dict]:
        return [json.loads(value) for value in self.redis_client.hvals(self._key(item_type))]

    def write(self, item_type: str, item: dict) -> bool:
        self.redis_client.hset(self._key(item_type), item["id"], json.dumps(item))
        return True

    def read(self, item_type: str, id: str) -> Optional[dict]:
        value = self.redis_client.hget(self._key(item_type), id)
        return json.loads(value) if value is not None else None

    def delete(self, item_type: str, id: str) -> bool:
        return self.redis_client.hdel(self._key(item_type), id) > 0
