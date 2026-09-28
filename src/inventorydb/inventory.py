from typing import List

from inventorydb.errors import InventoryError, ItemNotFoundError
from inventorydb.interface import InventoryStorage


def require_item_id(item: dict) -> str:
    """Return the item's id, raising ``ValueError`` if it is missing or empty."""
    _id = item.get("id")
    if not _id:
        raise ValueError("Item id is required.")
    return _id


def check_patch_data(id: str, data: dict) -> None:
    """Raise ``ValueError`` if patch data would change the item id."""
    if "id" in data and data["id"] != id:
        raise ValueError("Patch data must not change the item id.")


class Inventory[T]:

    def __init__(self, item_type, storage: InventoryStorage):
        self.storage = storage
        self.item_type = item_type

    def filter(self) -> List[T]:
        return self.storage.select(self.item_type)

    def get(self, id: str) -> T | None:
        return self.storage.read(self.item_type, id)

    def save(self, item: T) -> T:
        _id = require_item_id(item)
        if not self.storage.write(self.item_type, item):
            raise InventoryError(f"Failed to save item '{_id}'.")
        return self.storage.read(self.item_type, _id)

    def patch(self, id: str, data: dict) -> T:
        check_patch_data(id, data)
        item = self.storage.read(self.item_type, id)
        if item is None:
            raise ItemNotFoundError(self.item_type, id)
        item.update(data)
        if not self.storage.write(self.item_type, item):
            raise InventoryError(f"Failed to patch item '{id}'.")
        return self.storage.read(self.item_type, id)

    def delete(self, id: str) -> bool:
        return self.storage.delete(self.item_type, id)
