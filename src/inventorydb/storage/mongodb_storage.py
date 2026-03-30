from typing import Optional, List

from inventorydb.interface import InventoryStorage


class MongoDBInventoryStorage(InventoryStorage):
    """MongoDB-based storage implementation for inventory items."""

    def __init__(self, mongo_client):
        self.mongo_client = mongo_client
        
    def get_mongo_collection(self, inventory_type: str):
        db = self.mongo_client['inventory']
        return db[inventory_type]

    def select(self, inventory_type: str, query: Optional[dict] = None) -> List[dict]:
        if query is None:
            query = {}
        collection = self.get_mongo_collection(inventory_type)
        records = list(collection.find(query))
        filtered_records = []
        for record in records:
            record.pop('_id', None)
            filtered_records.append(record)
        return filtered_records

    def write(self, inventory_type: str, item: dict) -> bool:
        collection = self.get_mongo_collection(inventory_type)
        collection.update_one({'id': item['id']}, {'$set': item}, upsert=True)
        return True

    def read(self, inventory_type: str, id: str) -> dict:
        db = self.mongo_client['inventory']
        collection = db[inventory_type]
        item = collection.find_one({'id': id})
        print("Fetched item from MongoDB:", item)
        if item:
            item.pop('_id', None)
        return item if item else None

    def delete(self, inventory_type: str, id: str) -> bool:
        collection = self.get_mongo_collection(inventory_type)
        result = collection.delete_one({'id': id})
        return result.deleted_count > 0
