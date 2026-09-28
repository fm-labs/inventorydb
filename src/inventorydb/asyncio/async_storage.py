from typing import Protocol, runtime_checkable

from inventorydb.interface import Item


@runtime_checkable
class AsyncInventoryStorage(Protocol):
    """Async counterpart of ``InventoryStorage``, with the same contract."""

    async def aitems(self, item_type: str) -> list[Item]: ...

    async def aread(self, item_type: str, id: str) -> Item | None: ...

    async def awrite(self, item_type: str, item: Item) -> bool: ...

    async def adelete(self, item_type: str, id: str) -> bool: ...
