"""Damn simple object store for Python dicts and Pydantic models across multiple backends."""

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from inventorydb.asyncio.async_inventory import AsyncInventory
from inventorydb.asyncio.async_redis_storage import AsyncRedisInventoryStorage
from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.errors import InventoryError, ItemNotFoundError
from inventorydb.interface import InventoryStorage, Item
from inventorydb.inventory import Inventory
from inventorydb.storage.file_storage import DirectoryBasedInventoryStorage, FileBasedInventoryStorage
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage
from inventorydb.storage.mongodb_storage import MongoDBInventoryStorage
from inventorydb.storage.redis_storage import RedisInventoryStorage
from inventorydb.storage.sqlite_storage import SQLiteInventoryStorage

if TYPE_CHECKING:
    # Lets type checkers see the real class; at runtime it is loaded lazily by __getattr__.
    from inventorydb.pydantic import PydanticInventory

try:
    __version__ = version("inventorydb")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"

__all__ = [
    "AsyncInventory",
    "AsyncInventoryStorage",
    "AsyncRedisInventoryStorage",
    "DirectoryBasedInventoryStorage",
    "FileBasedInventoryStorage",
    "InMemoryInventoryStorage",
    "Inventory",
    "InventoryError",
    "InventoryStorage",
    "Item",
    "ItemNotFoundError",
    "MongoDBInventoryStorage",
    "PydanticInventory",
    "RedisInventoryStorage",
    "SQLiteInventoryStorage",
]


def __getattr__(name: str) -> Any:
    # Imported lazily so `import inventorydb` works without pydantic installed.
    if name == "PydanticInventory":
        from inventorydb.pydantic import PydanticInventory

        return PydanticInventory
    raise AttributeError(f"module 'inventorydb' has no attribute {name!r}")
