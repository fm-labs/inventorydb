"""Damn simple object store for Python dicts and Pydantic models across multiple backends."""

import importlib
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from objbase.asyncio.async_file_storage import AsyncDirectoryBasedInventoryStorage, AsyncFileBasedInventoryStorage
from objbase.asyncio.async_inventory import AsyncInventory
from objbase.asyncio.async_mongodb_storage import AsyncMongoDBInventoryStorage
from objbase.asyncio.async_redis_storage import AsyncRedisInventoryStorage
from objbase.asyncio.async_sqlite_storage import AsyncSQLiteInventoryStorage
from objbase.asyncio.async_storage import AsyncInventoryStorage
from objbase.errors import InventoryError, ItemNotFoundError
from objbase.interface import InventoryStorage, Item
from objbase.inventory import Inventory
from objbase.storage.file_storage import DirectoryBasedInventoryStorage, FileBasedInventoryStorage
from objbase.storage.inmemory_storage import InMemoryInventoryStorage
from objbase.storage.mongodb_storage import MongoDBInventoryStorage
from objbase.storage.redis_storage import RedisInventoryStorage
from objbase.storage.sqlite_storage import SQLiteInventoryStorage

if TYPE_CHECKING:
    # Lets type checkers see the real classes; at runtime they are loaded lazily by __getattr__.
    from objbase.pydantic import AsyncPydanticInventory, PydanticInventory

try:
    __version__ = version("objbase")
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
    # Imported lazily so `import objbase` works without pydantic installed.
    if name in ("PydanticInventory", "AsyncPydanticInventory"):
        return getattr(importlib.import_module("objbase.pydantic"), name)
    raise AttributeError(f"module 'objbase' has no attribute {name!r}")
