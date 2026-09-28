from typing import List

from inventorydb.interface import InventoryStorage


# def get_inventory_schema(item_type: str) -> dict:
#     """
#     Get the JSON schema for a specific inventory item type.
#     """
#     schema = lookup_inventory_schema(item_type)
#     if not schema or len(schema) == 0:
#         raise RuntimeError(f"Schema for item type '{item_type}' not found.")
#     return schema
# 
# 
# def get_inventory_metadata(item_type: str) -> dict:
#     """
#     Get metadata for a specific inventory item type.
#     """
#     metadata = lookup_inventory_metadata(item_type)
#     if not metadata or len(metadata) == 0:
#         raise RuntimeError(f"Metadata for item type '{item_type}' not found.")
#     return metadata


class Inventory[T]:

    def __init__(self, item_type, storage: InventoryStorage):
        self.storage = storage
        self.item_type = item_type
    
    def filter(self) -> List[T]:
        return self.storage.select(self.item_type)


    def get(self, id: str) -> T | None:
        return self.storage.read(self.item_type, id)


    def save(self, item: T) -> T:
        _id = item["id"] if "id" in item else None
        if not _id:
            raise RuntimeError("Item id is required.")
    
        #_id = gen_inventory_key(item_type, _id)
        #item["id"] = _id
        if not self.storage.write(self.item_type, item):
            return {"error": "Failed to save item"}
        return self.storage.read(self.item_type, _id)


    def patch(self, id: str, data: dict) -> T:
        item = self.storage.read(self.item_type, id)
        if not item:
            return {"error": "Item not found"}
        # fix: remove item_type from data if exists, since it's not stored in item properties
        if "item_type" in item:
            del item["item_type"]
        item.patch(data)
        print("Patched item:", item)
        if not self.storage.write(self.item_type, item):
            return {"error": "Failed to patch item"}
        return item
    
    
    def delete(self, id: str) -> bool:
        return self.storage.delete(self.item_type, id)
