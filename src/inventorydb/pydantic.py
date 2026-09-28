import pydantic

from inventorydb.inventory import Inventory


class PydanticInventory(Inventory[pydantic.BaseModel]):
    def __init__(self, item_type, storage, model_class):
        self.model_class = model_class
        self.item_type = item_type
        super().__init__(item_type, storage)

    def save(self, model: pydantic.BaseModel) -> pydantic.BaseModel:
        item_dict = model.model_dump(mode="json")
        created_item = super().save(item_dict)
        return self.model_class.model_validate(created_item)

    def get(self, id: str) -> pydantic.BaseModel | None:
        item_dict = super().get(id)
        if not item_dict:
            return None
        return self.model_class.model_validate(item_dict)

    def patch(self, id: str, data: dict) -> pydantic.BaseModel:
        updated_item_dict = super().patch(id, data)
        return self.model_class.model_validate(updated_item_dict)

    def delete(self, id: str) -> bool:
        return super().delete(id)
