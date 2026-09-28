from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class AsyncInventoryStorage(Protocol):
    """Async counterpart of ``InventoryStorage``, with the same contract."""

    async def aselect(self, item_type: str) -> List[dict]: ...

    async def aread(self, item_type: str, id: str) -> Optional[dict]: ...

    async def awrite(self, item_type: str, item: dict) -> bool: ...

    async def adelete(self, item_type: str, id: str) -> bool: ...
