from typing import List

from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.interface import InventoryStorage


class InMemoryInventoryStorage(InventoryStorage, AsyncInventoryStorage):
    """In-memory storage implementation for inventory items."""

    def __init__(self):
        self.data = {}

    def select(self, inventory_type: str) -> List[dict]:
        return list(self.data.get(inventory_type, {}).values())

    def read(self, inventory_type: str, id: str) -> dict:
        return self.data.get(inventory_type, {}).get(id)

    def write(self, inventory_type: str, item: dict) -> bool:
        if inventory_type not in self.data:
            self.data[inventory_type] = {}
        self.data[inventory_type][item['id']] = item
        return True

    def delete(self, inventory_type: str, id: str) -> bool:
        if inventory_type in self.data and id in self.data[inventory_type]:
            del self.data[inventory_type][id]
            return True
        return False

    async def aselect(self, inventory_type: str) -> List[dict]:
        return self.select(inventory_type)

    async def aread(self, inventory_type: str, id: str) -> dict:
        return self.read(inventory_type, id)

    async def awrite(self, inventory_type: str, item: dict) -> bool:
        return self.write(inventory_type, item)

    async def adelete(self, inventory_type: str, id: str) -> bool:
        return self.delete(inventory_type, id)