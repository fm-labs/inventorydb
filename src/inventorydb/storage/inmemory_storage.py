from typing import List

from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.interface import InventoryStorage


class InMemoryInventoryStorage(InventoryStorage, AsyncInventoryStorage):
    """In-memory storage implementation for inventory items."""

    def __init__(self):
        self.data = {}

    def select(self, item_type: str) -> List[dict]:
        return list(self.data.get(item_type, {}).values())

    def read(self, item_type: str, id: str) -> dict:
        return self.data.get(item_type, {}).get(id)

    def write(self, item_type: str, item: dict) -> bool:
        if item_type not in self.data:
            self.data[item_type] = {}
        self.data[item_type][item['id']] = item
        return True

    def delete(self, item_type: str, id: str) -> bool:
        if item_type in self.data and id in self.data[item_type]:
            del self.data[item_type][id]
            return True
        return False

    async def aselect(self, item_type: str) -> List[dict]:
        return self.select(item_type)

    async def aread(self, item_type: str, id: str) -> dict:
        return self.read(item_type, id)

    async def awrite(self, item_type: str, item: dict) -> bool:
        return self.write(item_type, item)

    async def adelete(self, item_type: str, id: str) -> bool:
        return self.delete(item_type, id)