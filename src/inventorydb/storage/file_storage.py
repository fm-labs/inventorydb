import json
import os

from inventorydb.interface import InventoryStorage, Item


def _safe_name(name: str, kind: str) -> str:
    """Validate that an item type or id can be used as a single path component."""
    if not isinstance(name, str) or name in ("", ".", "..") or "/" in name or "\\" in name or "\x00" in name:
        raise ValueError(f"Invalid {kind} for file storage: {name!r}")
    return name


class FileBasedInventoryStorage(InventoryStorage):
    """Simple file-based storage that saves all items of a given inventory type in a single JSON file."""

    def __init__(self, base_dir: str):
        self.inventory_dir = base_dir
        if not os.path.exists(self.inventory_dir):
            raise ValueError(f"Base directory {self.inventory_dir} does not exist.")

    def select(self, item_type: str) -> list[Item]:
        return self._read_file(item_type)

    def write(self, item_type: str, item: Item) -> bool:
        items = self.select(item_type)
        for i, existing_item in enumerate(items):
            if existing_item["id"] == item["id"]:
                items[i] = item
                break
        else:
            items.append(item)
        self._write_file(item_type, items)
        return True

    def read(self, item_type: str, id: str) -> Item | None:
        items = self.select(item_type)
        for item in items:
            if item["id"] == id:
                return item
        return None

    def delete(self, item_type: str, id: str) -> bool:
        items = self.select(item_type)
        remaining = [item for item in items if item["id"] != id]
        if len(remaining) == len(items):
            return False
        self._write_file(item_type, remaining)
        return True

    def _file_path(self, item_type: str) -> str:
        return os.path.join(self.inventory_dir, f"{_safe_name(item_type, 'item type')}.json")

    def _read_file(self, item_type: str) -> list[Item]:
        file_path = self._file_path(item_type)
        if not os.path.exists(file_path):
            return []
        with open(file_path) as f:
            items: list[Item] = json.load(f)
        return items

    def _write_file(self, item_type: str, data: list[Item]) -> None:
        with open(self._file_path(item_type), "w") as f:
            json.dump(data, f, indent=4)


class DirectoryBasedInventoryStorage(InventoryStorage):
    """Alternative file-based storage that uses a directory per inventory type and individual files per item."""

    def __init__(self, base_dir: str):
        self.inventory_dir = base_dir
        if not os.path.exists(self.inventory_dir):
            raise ValueError(f"Base directory {self.inventory_dir} does not exist.")

    def _type_dir(self, item_type: str) -> str:
        return os.path.join(self.inventory_dir, _safe_name(item_type, "item type"))

    def _item_path(self, item_type: str, id: str) -> str:
        return os.path.join(self._type_dir(item_type), f"{_safe_name(id, 'item id')}.json")

    def select(self, item_type: str) -> list[Item]:
        type_dir = self._type_dir(item_type)
        if not os.path.exists(type_dir):
            return []
        items = []
        for filename in os.listdir(type_dir):
            if filename.endswith(".json"):
                with open(os.path.join(type_dir, filename)) as f:
                    items.append(json.load(f))
        return items

    def write(self, item_type: str, item: Item) -> bool:
        item_id = item.get("id")
        if not item_id:
            raise ValueError("Item must have an 'id' field.")
        item_path = self._item_path(item_type, item_id)
        os.makedirs(self._type_dir(item_type), exist_ok=True)
        with open(item_path, "w") as f:
            json.dump(item, f, indent=4)
        return True

    def read(self, item_type: str, id: str) -> Item | None:
        item_path = self._item_path(item_type, id)
        if not os.path.exists(item_path):
            return None
        with open(item_path) as f:
            item: Item = json.load(f)
        return item

    def delete(self, item_type: str, id: str) -> bool:
        item_path = self._item_path(item_type, id)
        if os.path.exists(item_path):
            os.remove(item_path)
            return True
        return False
