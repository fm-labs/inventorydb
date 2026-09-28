import asyncio

from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.interface import Item
from inventorydb.storage.sqlite_storage import SQLiteInventoryStorage


class AsyncSQLiteInventoryStorage(AsyncInventoryStorage):
    """Async counterpart of ``SQLiteInventoryStorage``, using the same data layout.

    Uses the standard library ``sqlite3`` module, so it needs no extra dependencies.
    Each call runs in a worker thread (``asyncio.to_thread``) with its own connection,
    so the event loop is never blocked by database I/O.
    """

    def __init__(self, db_path: str):
        # Creates the table if needed; this one-off setup runs synchronously.
        self.sync_storage = SQLiteInventoryStorage(db_path)

    @property
    def db_path(self) -> str:
        return self.sync_storage.db_path

    async def akeys(self, item_type: str) -> list[str]:
        return await asyncio.to_thread(self.sync_storage.keys, item_type)

    async def aitems(self, item_type: str) -> list[Item]:
        return await asyncio.to_thread(self.sync_storage.items, item_type)

    async def aread(self, item_type: str, id: str) -> Item | None:
        return await asyncio.to_thread(self.sync_storage.read, item_type, id)

    async def awrite(self, item_type: str, item: Item) -> bool:
        return await asyncio.to_thread(self.sync_storage.write, item_type, item)

    async def adelete(self, item_type: str, id: str) -> bool:
        return await asyncio.to_thread(self.sync_storage.delete, item_type, id)
