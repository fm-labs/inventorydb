import pydantic

from inventorydb.interface import InventoryStorage, Item
from inventorydb.inventory import Inventory


class PydanticInventory[M: pydantic.BaseModel]:
    """Inventory that validates items against a Pydantic model.

    Wraps an ``Inventory``: items are stored as plain dicts and returned as
    ``model_class`` instances. The model type is inferred from ``model_class``,
    so ``PydanticInventory("todo", storage, Todo).get("1")`` is typed ``Todo | None``.
    """

    def __init__(self, item_type: str, storage: InventoryStorage, model_class: type[M]):
        self.model_class = model_class
        self.inventory = Inventory(item_type, storage)

    @property
    def item_type(self) -> str:
        return self.inventory.item_type

    @property
    def storage(self) -> InventoryStorage:
        return self.inventory.storage

    def filter(self) -> list[M]:
        return [self.model_class.model_validate(item) for item in self.inventory.filter()]

    def save(self, model: M) -> M:
        created_item = self.inventory.save(model.model_dump(mode="json"))
        return self.model_class.model_validate(created_item)

    def get(self, id: str) -> M | None:
        item = self.inventory.get(id)
        if item is None:
            return None
        return self.model_class.model_validate(item)

    def patch(self, id: str, data: Item | M) -> M:
        if isinstance(data, pydantic.BaseModel):
            data = data.model_dump(mode="json")
        return self.model_class.model_validate(self.inventory.patch(id, data))

    def delete(self, id: str) -> bool:
        return self.inventory.delete(id)
