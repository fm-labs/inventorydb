from typing import List

import pydantic

from inventorydb.inventory import Inventory


class PydanticInventory(Inventory[pydantic.BaseModel]):
    def __init__(self, item_type, storage, model_class):
        self.model_class = model_class
        super().__init__(item_type, storage)

    def filter(self) -> List[pydantic.BaseModel]:
        return [self.model_class.model_validate(item) for item in super().filter()]

    def save(self, model: pydantic.BaseModel) -> pydantic.BaseModel:
        item_dict = model.model_dump(mode="json")
        created_item = super().save(item_dict)
        return self.model_class.model_validate(created_item)

    def get(self, id: str) -> pydantic.BaseModel | None:
        item_dict = super().get(id)
        if item_dict is None:
            return None
        return self.model_class.model_validate(item_dict)

    def patch(self, id: str, data: dict | pydantic.BaseModel) -> pydantic.BaseModel:
        if isinstance(data, pydantic.BaseModel):
            data = data.model_dump(mode="json")
        updated_item_dict = super().patch(id, data)
        return self.model_class.model_validate(updated_item_dict)
