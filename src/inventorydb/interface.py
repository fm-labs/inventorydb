from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class InventoryStorage(Protocol):
    """Storage contract shared by all adapters.

    - ``select`` returns all items of a type, or ``[]`` if there are none.
    - ``read`` returns the item, or ``None`` if it does not exist.
    - ``write`` inserts the item or replaces an existing item with the same id entirely.
    - ``delete`` returns ``True`` if an item was removed, ``False`` if it did not exist.
    - Returned items are independent copies; mutating them does not change stored data.
    """

    def select(self, item_type: str) -> List[dict]: ...

    def read(self, item_type: str, id: str) -> Optional[dict]: ...

    def write(self, item_type: str, item: dict) -> bool: ...

    def delete(self, item_type: str, id: str) -> bool: ...
