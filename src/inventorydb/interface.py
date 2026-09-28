from typing import Any, Protocol, runtime_checkable

Item = dict[str, Any]
"""A stored item: a JSON-serializable dict with an ``"id"`` key."""


@runtime_checkable
class InventoryStorage(Protocol):
    """Storage contract shared by all adapters.

    - ``items`` returns all items of a type, or ``[]`` if there are none.
    - ``read`` returns the item, or ``None`` if it does not exist.
    - ``write`` inserts the item or replaces an existing item with the same id entirely.
    - ``delete`` returns ``True`` if an item was removed, ``False`` if it did not exist.
    - Returned items are independent copies; mutating them does not change stored data.
    """

    def items(self, item_type: str) -> list[Item]: ...

    def read(self, item_type: str, id: str) -> Item | None: ...

    def write(self, item_type: str, item: Item) -> bool: ...

    def delete(self, item_type: str, id: str) -> bool: ...
