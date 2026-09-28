from typing import List

from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.errors import InventoryError, ItemNotFoundError
from inventorydb.inventory import check_patch_data, require_item_id


class AsyncInventory[T]:
    """Async counterpart of ``Inventory``, backed by an ``AsyncInventoryStorage``.

    Same methods and behaviour as ``Inventory``, but every method is a coroutine.
    """

    def __init__(self, item_type, storage: AsyncInventoryStorage):
        if not isinstance(storage, AsyncInventoryStorage):
            raise TypeError(
                f"{type(storage).__name__} is not an AsyncInventoryStorage; "
                "use Inventory for sync storage adapters."
            )
        self.storage = storage
        self.item_type = item_type

    async def filter(self) -> List[T]:
        return await self.storage.aselect(self.item_type)

    async def get(self, id: str) -> T | None:
        return await self.storage.aread(self.item_type, id)

    async def save(self, item: T) -> T:
        _id = require_item_id(item)
        if not await self.storage.awrite(self.item_type, item):
            raise InventoryError(f"Failed to save item '{_id}'.")
        return await self.storage.aread(self.item_type, _id)

    async def patch(self, id: str, data: dict) -> T:
        check_patch_data(id, data)
        item = await self.storage.aread(self.item_type, id)
        if item is None:
            raise ItemNotFoundError(self.item_type, id)
        item.update(data)
        if not await self.storage.awrite(self.item_type, item):
            raise InventoryError(f"Failed to patch item '{id}'.")
        return await self.storage.aread(self.item_type, id)

    async def delete(self, id: str) -> bool:
        return await self.storage.adelete(self.item_type, id)
