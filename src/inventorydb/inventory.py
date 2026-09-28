from typing import List

from inventorydb.errors import InventoryError, ItemNotFoundError
from inventorydb.interface import InventoryStorage


class Inventory[T]:

    def __init__(self, item_type, storage: InventoryStorage):
        self.storage = storage
        self.item_type = item_type

    def filter(self) -> List[T]:
        return self.storage.select(self.item_type)

    def get(self, id: str) -> T | None:
        return self.storage.read(self.item_type, id)

    def save(self, item: T) -> T:
        _id = item.get("id")
        if not _id:
            raise ValueError("Item id is required.")
        if not self.storage.write(self.item_type, item):
            raise InventoryError(f"Failed to save item '{_id}'.")
        return self.storage.read(self.item_type, _id)

    def patch(self, id: str, data: dict) -> T:
        if "id" in data and data["id"] != id:
            raise ValueError("Patch data must not change the item id.")
        item = self.storage.read(self.item_type, id)
        if item is None:
            raise ItemNotFoundError(self.item_type, id)
        item.update(data)
        if not self.storage.write(self.item_type, item):
            raise InventoryError(f"Failed to patch item '{id}'.")
        return self.storage.read(self.item_type, id)

    def delete(self, id: str) -> bool:
        return self.storage.delete(self.item_type, id)
