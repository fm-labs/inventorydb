"""Tests for the AsyncInventory API."""

import pytest

from inventorydb.asyncio.async_inventory import AsyncInventory
from inventorydb.errors import InventoryError, ItemNotFoundError
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage
from inventorydb.storage.sqlite_storage import SQLiteInventoryStorage


@pytest.fixture()
def storage() -> InMemoryInventoryStorage:
    return InMemoryInventoryStorage()


@pytest.fixture()
def todos(storage) -> AsyncInventory:
    return AsyncInventory(item_type="todo", storage=storage)


class FailingStorage(InMemoryInventoryStorage):
    async def awrite(self, item_type, item):
        return False


class TestAsyncInventoryInit:
    def test_rejects_sync_only_storage(self, tmp_path):
        with pytest.raises(TypeError, match="not an AsyncInventoryStorage"):
            AsyncInventory("todo", SQLiteInventoryStorage(str(tmp_path / "x.db")))  # type: ignore[arg-type]


class TestAsyncInventorySave:
    async def test_save_returns_stored_item(self, todos):
        assert await todos.save({"id": "1", "title": "Buy milk"}) == {"id": "1", "title": "Buy milk"}

    async def test_save_stores_under_item_type(self, todos, storage):
        await todos.save({"id": "1"})
        assert storage.read("todo", "1") == {"id": "1"}

    @pytest.mark.parametrize("item", [{}, {"id": ""}, {"id": None}])
    async def test_save_without_id_raises(self, todos, item):
        with pytest.raises(ValueError, match="id is required"):
            await todos.save(item)

    async def test_save_raises_when_storage_write_fails(self):
        with pytest.raises(InventoryError, match="Failed to save"):
            await AsyncInventory("todo", FailingStorage()).save({"id": "1"})


class TestAsyncInventoryGetFilter:
    async def test_get_returns_item(self, todos):
        await todos.save({"id": "1", "title": "a"})
        assert await todos.get("1") == {"id": "1", "title": "a"}

    async def test_get_missing_returns_none(self, todos):
        assert await todos.get("nope") is None

    async def test_filter_returns_all_items(self, todos):
        await todos.save({"id": "1"})
        await todos.save({"id": "2"})
        assert sorted(i["id"] for i in await todos.filter()) == ["1", "2"]

    async def test_filter_empty(self, todos):
        assert await todos.filter() == []


class TestAsyncInventoryPatch:
    async def test_patch_merges_fields(self, todos):
        await todos.save({"id": "1", "title": "a", "done": False})
        assert await todos.patch("1", {"done": True}) == {"id": "1", "title": "a", "done": True}

    async def test_patch_persists(self, todos):
        await todos.save({"id": "1", "done": False})
        await todos.patch("1", {"done": True})
        assert await todos.get("1") == {"id": "1", "done": True}

    async def test_patch_cannot_change_id(self, todos):
        await todos.save({"id": "1"})
        with pytest.raises(ValueError, match="must not change the item id"):
            await todos.patch("1", {"id": "2"})
        assert await todos.get("2") is None

    async def test_patch_missing_item_raises(self, todos):
        with pytest.raises(ItemNotFoundError) as exc_info:
            await todos.patch("nope", {"done": True})
        assert exc_info.value.item_type == "todo"
        assert exc_info.value.id == "nope"

    async def test_patch_raises_when_storage_write_fails(self):
        storage = FailingStorage()
        storage.write("todo", {"id": "1"})
        with pytest.raises(InventoryError, match="Failed to patch"):
            await AsyncInventory("todo", storage).patch("1", {"done": True})


class TestAsyncInventoryDelete:
    async def test_delete_existing(self, todos):
        await todos.save({"id": "1"})
        assert await todos.delete("1") is True
        assert await todos.get("1") is None

    async def test_delete_missing(self, todos):
        assert await todos.delete("nope") is False
