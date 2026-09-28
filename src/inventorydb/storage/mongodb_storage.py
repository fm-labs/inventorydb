from typing import Optional, List

from inventorydb.interface import InventoryStorage


class MongoDBInventoryStorage(InventoryStorage):
    """MongoDB-based storage implementation for inventory items."""

    def __init__(self, mongo_client):
        self.mongo_client = mongo_client

    def get_mongo_collection(self, item_type: str):
        db = self.mongo_client['inventory']
        return db[item_type]

    def select(self, item_type: str, query: Optional[dict] = None) -> List[dict]:
        """Return all items of a type. ``query`` is a MongoDB-only extension to filter results."""
        collection = self.get_mongo_collection(item_type)
        return list(collection.find(query or {}, {'_id': False}))

    def write(self, item_type: str, item: dict) -> bool:
        collection = self.get_mongo_collection(item_type)
        collection.replace_one({'id': item['id']}, item, upsert=True)
        return True

    def read(self, item_type: str, id: str) -> Optional[dict]:
        collection = self.get_mongo_collection(item_type)
        return collection.find_one({'id': id}, {'_id': False})

    def delete(self, item_type: str, id: str) -> bool:
        collection = self.get_mongo_collection(item_type)
        result = collection.delete_one({'id': id})
        return result.deleted_count > 0
