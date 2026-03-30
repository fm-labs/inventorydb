import json
import os
from typing import List

from inventorydb.interface import InventoryStorage


class FileBasedInventoryStorage(InventoryStorage):
    """Simple file-based storage that saves all items of a given inventory type in a single JSON file."""

    def __init__(self, base_dir: str):
        self.inventory_dir = base_dir
        if not os.path.exists(self.inventory_dir):
            raise ValueError(f"Base directory {self.inventory_dir} does not exist.")

    def select(self, inventory_type: str) -> List[dict]:
        return self._read_file(inventory_type)

    def write(self, inventory_type: str, item: dict) -> bool:
        items = self.select(inventory_type)
        for i, existing_item in enumerate(items):
            if existing_item["id"] == item["id"]:
                items[i] = item
                break
        else:
            items.append(item)
        self._write_file(inventory_type, items)
        return True

    def read(self, inventory_type: str, id: str) -> dict:
        items = self.select(inventory_type)
        for item in items:
            if item["id"] == id:
                return item
        return {}

    def delete(self, inventory_type: str, id: str) -> bool:
        items = self.select(inventory_type)
        items = [item for item in items if item["id"] != id]
        self._write_file(inventory_type, items)
        return True

    def _read_file(self, file_name: str) -> dict | list:
        file_path = f"{self.inventory_dir}/{file_name}.json"
        with open(file_path, 'r') as f:
            return json.load(f)

    def _write_file(self, file_name: str, data: dict | list) -> None:
        file_path = f"{self.inventory_dir}/{file_name}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)


class DirectoryBasedInventoryStorage(InventoryStorage):
    """Alternative file-based storage that uses a directory per inventory type and individual files per item."""

    def __init__(self, base_dir: str):
        self.inventory_dir = base_dir
        if not os.path.exists(self.inventory_dir):
            raise ValueError(f"Base directory {self.inventory_dir} does not exist.")

    def select(self, inventory_type: str) -> List[dict]:
        type_dir = f"{self.inventory_dir}/{inventory_type}"
        if not os.path.exists(type_dir):
            return []
        items = []
        for filename in os.listdir(type_dir):
            if filename.endswith(".json"):
                with open(f"{type_dir}/{filename}", 'r') as f:
                    items.append(json.load(f))
        return items

    def write(self, inventory_type: str, item: dict) -> bool:
        type_dir = f"{self.inventory_dir}/{inventory_type}"
        os.makedirs(type_dir, exist_ok=True)
        item_id = item.get("id")
        if not item_id:
            raise ValueError("Item must have an 'id' field.")
        with open(f"{type_dir}/{item_id}.json", 'w') as f:
            json.dump(item, f, indent=4)
        return True

    def read(self, inventory_type: str, id: str) -> dict:
        type_dir = f"{self.inventory_dir}/{inventory_type}"
        item_path = f"{type_dir}/{id}.json"
        if not os.path.exists(item_path):
            return {}
        with open(item_path, 'r') as f:
            return json.load(f)

    def delete(self, inventory_type: str, id: str) -> bool:
        type_dir = f"{self.inventory_dir}/{inventory_type}"
        item_path = f"{type_dir}/{id}.json"
        if os.path.exists(item_path):
            os.remove(item_path)
            return True
        return False
