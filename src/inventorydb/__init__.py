"""Damn simple object store for Python dicts and Pydantic models across multiple backends."""

import importlib
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from inventorydb.asyncio.async_file_storage import AsyncDirectoryBasedInventoryStorage, AsyncFileBasedInventoryStorage
from inventorydb.asyncio.async_inventory import AsyncInventory
from inventorydb.asyncio.async_mongodb_storage import AsyncMongoDBInventoryStorage
from inventorydb.asyncio.async_redis_storage import AsyncRedisInventoryStorage
from inventorydb.asyncio.async_sqlite_storage import AsyncSQLiteInventoryStorage
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
    # Lets type checkers see the real classes; at runtime they are loaded lazily by __getattr__.
    from inventorydb.pydantic import AsyncPydanticInventory, PydanticInventory

try:
    __version__ = version("inventorydb")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"

__all__ = [
    "AsyncDirectoryBasedInventoryStorage",
    "AsyncFileBasedInventoryStorage",
    "AsyncInventory",
    "AsyncInventoryStorage",
    "AsyncMongoDBInventoryStorage",
    "AsyncPydanticInventory",
    "AsyncRedisInventoryStorage",
    "AsyncSQLiteInventoryStorage",
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
    if name in ("PydanticInventory", "AsyncPydanticInventory"):
        return getattr(importlib.import_module("inventorydb.pydantic"), name)
    raise AttributeError(f"module 'inventorydb' has no attribute {name!r}")
