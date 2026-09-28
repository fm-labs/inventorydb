import json
import os

from inventorydb.interface import InventoryStorage, Item
from inventorydb.util.file_util import atomic_write_json, atomic_write_text, locked


def _safe_name(name: str, kind: str) -> str:
    """Validate that an item type or id can be used as a single path component."""
    # Newlines are rejected because the directory storage index stores one id per line.
    if not isinstance(name, str) or name in ("", ".", "..") or any(c in name for c in "/\\\x00\n\r"):
        raise ValueError(f"Invalid {kind} for file storage: {name!r}")
    return name


class FileBasedInventoryStorage(InventoryStorage):
    """Simple file-based storage that saves all items of a given inventory type in a single JSON file.

    Safe for concurrent use by multiple threads and processes on the same machine:
    writes hold an exclusive lock on ``.{item_type}.json.lock`` for the whole
    read-modify-write cycle, and files are replaced atomically. Locks are advisory
    and may not work on network file systems.
    """

    def __init__(self, base_dir: str):
        self.inventory_dir = base_dir
        if not os.path.exists(self.inventory_dir):
            raise ValueError(f"Base directory {self.inventory_dir} does not exist.")

    def keys(self, item_type: str) -> list[str]:
        return [item["id"] for item in self.items(item_type)]

    def items(self, item_type: str) -> list[Item]:
        file_path = self._file_path(item_type)
        if not os.path.exists(file_path):
            return []
        with locked(self._lock_path(item_type), shared=True):
            return self._load(file_path)

    def write(self, item_type: str, item: Item) -> bool:
        file_path = self._file_path(item_type)
        with locked(self._lock_path(item_type)):
            items = self._load(file_path)
            for i, existing_item in enumerate(items):
                if existing_item["id"] == item["id"]:
                    items[i] = item
                    break
            else:
                items.append(item)
            atomic_write_json(file_path, items)
        return True

    def read(self, item_type: str, id: str) -> Item | None:
        items = self.items(item_type)
        for item in items:
            if item["id"] == id:
                return item
        return None

    def delete(self, item_type: str, id: str) -> bool:
        file_path = self._file_path(item_type)
        if not os.path.exists(file_path):
            return False
        with locked(self._lock_path(item_type)):
            items = self._load(file_path)
            remaining = [item for item in items if item["id"] != id]
            if len(remaining) == len(items):
                return False
            atomic_write_json(file_path, remaining)
        return True

    def _file_path(self, item_type: str) -> str:
        return os.path.join(self.inventory_dir, f"{_safe_name(item_type, 'item type')}.json")

    def _lock_path(self, item_type: str) -> str:
        return os.path.join(self.inventory_dir, f".{_safe_name(item_type, 'item type')}.json.lock")

    @staticmethod
    def _load(file_path: str) -> list[Item]:
        """Load a type file; the caller must hold its lock. A missing file means no items."""
        try:
            with open(file_path) as f:
                items: list[Item] = json.load(f)
        except FileNotFoundError:
            return []
        return items


class DirectoryBasedInventoryStorage(InventoryStorage):
    """Alternative file-based storage that uses a directory per inventory type and individual files per item.

    Each type directory also holds an index file (``.index``) listing the ids of
    all items of that type, one per line, so ``keys()`` doesn't have to scan the
    directory. Writes and deletes hold an exclusive lock on ``.index.lock`` while
    they change the item file and the index, keeping both in step across threads
    and processes. Locks are advisory and may not work on network file systems.
    """

    INDEX_FILE = ".index"

    def __init__(self, base_dir: str):
        self.inventory_dir = base_dir
        if not os.path.exists(self.inventory_dir):
            raise ValueError(f"Base directory {self.inventory_dir} does not exist.")

    def _type_dir(self, item_type: str) -> str:
        return os.path.join(self.inventory_dir, _safe_name(item_type, "item type"))

    def _item_path(self, item_type: str, id: str) -> str:
        return os.path.join(self._type_dir(item_type), f"{_safe_name(id, 'item id')}.json")

    def _index_path(self, item_type: str) -> str:
        return os.path.join(self._type_dir(item_type), self.INDEX_FILE)

    def _lock_path(self, item_type: str) -> str:
        return os.path.join(self._type_dir(item_type), f"{self.INDEX_FILE}.lock")

    def keys(self, item_type: str) -> list[str]:
        type_dir = self._type_dir(item_type)
        if not os.path.exists(type_dir):
            return []
        with locked(self._lock_path(item_type), shared=True):
            ids = self._read_index(item_type)
        # A type directory without an index predates indexing; the next write or
        # delete creates the index, until then the directory is scanned.
        return ids if ids is not None else self._scan(type_dir)

    def items(self, item_type: str) -> list[Item]:
        type_dir = self._type_dir(item_type)
        if not os.path.exists(type_dir):
            return []
        items = []
        for filename in os.listdir(type_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(type_dir, filename)) as f:
                        items.append(json.load(f))
                except FileNotFoundError:
                    continue  # deleted by another process since listdir()
        return items

    def write(self, item_type: str, item: Item) -> bool:
        item_id = item.get("id")
        if not item_id:
            raise ValueError("Item must have an 'id' field.")
        item_path = self._item_path(item_type, item_id)
        os.makedirs(self._type_dir(item_type), exist_ok=True)
        with locked(self._lock_path(item_type)):
            atomic_write_json(item_path, item)
            if item_id not in self._load_index(item_type):
                with open(self._index_path(item_type), "a") as f:
                    f.write(f"{item_id}\n")
                    f.flush()
                    os.fsync(f.fileno())
        return True

    def read(self, item_type: str, id: str) -> Item | None:
        item_path = self._item_path(item_type, id)
        try:
            with open(item_path) as f:
                item: Item = json.load(f)
        except FileNotFoundError:
            return None
        return item

    def delete(self, item_type: str, id: str) -> bool:
        item_path = self._item_path(item_type, id)
        if not os.path.exists(self._type_dir(item_type)):
            return False
        with locked(self._lock_path(item_type)):
            try:
                os.remove(item_path)
            except FileNotFoundError:
                return False
            ids = self._load_index(item_type)
            if id in ids:
                self._write_index(item_type, [i for i in ids if i != id])
        return True

    def rebuild_index(self, item_type: str) -> None:
        """Recreate the index of ``item_type`` from the item files in its directory.

        Only needed if the index got out of step with the item files, e.g. after a
        crash between writing an item and updating the index, or after item files
        were added or removed by hand.
        """
        type_dir = self._type_dir(item_type)
        if not os.path.exists(type_dir):
            return
        with locked(self._lock_path(item_type)):
            self._write_index(item_type, self._scan(type_dir))

    @staticmethod
    def _scan(type_dir: str) -> list[str]:
        """Ids of all item files in ``type_dir``, from the directory listing (item files are named ``{id}.json``)."""
        return [filename.removesuffix(".json") for filename in os.listdir(type_dir) if filename.endswith(".json")]

    def _read_index(self, item_type: str) -> list[str] | None:
        """Ids in the index of ``item_type``, or ``None`` if there is no index. The caller must hold the lock."""
        try:
            with open(self._index_path(item_type)) as f:
                return [line for line in f.read().splitlines() if line]
        except FileNotFoundError:
            return None

    def _load_index(self, item_type: str) -> list[str]:
        """Like ``_read_index``, but creates a missing index first. The caller must hold the exclusive lock."""
        ids = self._read_index(item_type)
        if ids is None:
            ids = self._scan(self._type_dir(item_type))
            self._write_index(item_type, ids)
        return ids

    def _write_index(self, item_type: str, ids: list[str]) -> None:
        atomic_write_text(self._index_path(item_type), "".join(f"{id}\n" for id in ids))
