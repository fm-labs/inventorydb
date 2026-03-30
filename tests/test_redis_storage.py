"""Tests for RedisInventoryStorage using a real Redis via testcontainers."""

import pytest
from testcontainers.redis import RedisContainer

from inventorydb.storage.redis_storage import RedisInventoryStorage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def redis_container():
    """Start a single Redis container for the entire test session."""
    with RedisContainer() as container:
        yield container


@pytest.fixture()
def redis_client(redis_container):
    """Return a bytes-mode Redis client and flush the DB before each test."""
    client = redis_container.get_client()
    client.flushdb()
    return client


@pytest.fixture()
def storage(redis_client) -> RedisInventoryStorage:
    return RedisInventoryStorage(redis_client)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def str_item(item: dict) -> dict:
    """Convert all dict values to strings (Redis stores everything as strings)."""
    return {k: str(v) for k, v in item.items()}


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


class TestRedisInventoryStorageWrite:
    def test_write_returns_true(self, storage):
        assert storage.write("todo", {"id": "1", "title": "Buy milk"}) is True

    def test_write_creates_hash_in_redis(self, storage, redis_client):
        storage.write("todo", {"id": "1", "title": "Buy milk"})
        assert redis_client.exists("todo:1")

    def test_write_stores_all_fields(self, storage):
        item = {"id": "1", "title": "Buy milk", "done": "false"}
        storage.write("todo", item)
        assert storage.read("todo", "1") == item

    def test_write_updates_existing_item(self, storage):
        storage.write("todo", {"id": "1", "title": "Old"})
        storage.write("todo", {"id": "1", "title": "New"})
        assert storage.read("todo", "1")["title"] == "New"

    def test_write_update_does_not_duplicate(self, storage):
        storage.write("todo", {"id": "1", "title": "x"})
        storage.write("todo", {"id": "1", "title": "y"})
        assert len(storage.select("todo")) == 1

    def test_write_multiple_items(self, storage):
        for i in range(3):
            storage.write("todo", {"id": str(i), "val": str(i)})
        assert len(storage.select("todo")) == 3


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


class TestRedisInventoryStorageRead:
    def test_read_returns_item_by_id(self, storage):
        item = {"id": "42", "title": "Hello"}
        storage.write("todo", item)
        assert storage.read("todo", "42") == item

    def test_read_returns_empty_dict_for_unknown_id(self, storage):
        assert storage.read("todo", "nonexistent") == {}

    def test_read_returns_empty_dict_for_unknown_type(self, storage):
        assert storage.read("ghost_type", "1") == {}

    def test_read_returns_correct_item_among_many(self, storage):
        for i in range(5):
            storage.write("todo", {"id": str(i), "val": str(i)})
        assert storage.read("todo", "3") == {"id": "3", "val": "3"}

    def test_read_does_not_cross_types(self, storage):
        storage.write("todos", {"id": "1", "kind": "todo"})
        assert storage.read("notes", "1") == {}


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------


class TestRedisInventoryStorageSelect:
    def test_select_returns_empty_list_for_unknown_type(self, storage):
        assert storage.select("todo") == []

    def test_select_returns_all_items(self, storage):
        items = [{"id": "1", "title": "a"}, {"id": "2", "title": "b"}]
        for item in items:
            storage.write("todo", item)
        result = sorted(storage.select("todo"), key=lambda x: x["id"])
        assert result == sorted(items, key=lambda x: x["id"])

    def test_select_isolates_types(self, storage):
        storage.write("todos", {"id": "1", "kind": "todo"})
        storage.write("notes", {"id": "1", "kind": "note"})
        assert storage.select("todos") == [{"id": "1", "kind": "todo"}]
        assert storage.select("notes") == [{"id": "1", "kind": "note"}]

    def test_select_reflects_updates(self, storage):
        storage.write("todo", {"id": "1", "title": "Old"})
        storage.write("todo", {"id": "1", "title": "New"})
        result = storage.select("todo")
        assert len(result) == 1
        assert result[0]["title"] == "New"

    def test_select_returns_empty_list_after_all_deleted(self, storage):
        storage.write("todo", {"id": "1"})
        storage.delete("todo", "1")
        assert storage.select("todo") == []


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestRedisInventoryStorageDelete:
    def test_delete_returns_true_when_item_exists(self, storage):
        storage.write("todo", {"id": "1"})
        assert storage.delete("todo", "1") is True

    def test_delete_returns_false_for_unknown_id(self, storage):
        assert storage.delete("todo", "nonexistent") is False

    def test_delete_returns_false_for_unknown_type(self, storage):
        assert storage.delete("ghost_type", "1") is False

    def test_delete_removes_item_from_redis(self, storage, redis_client):
        storage.write("todo", {"id": "1"})
        storage.delete("todo", "1")
        assert not redis_client.exists("todo:1")

    def test_delete_item_no_longer_readable(self, storage):
        storage.write("todo", {"id": "1"})
        storage.delete("todo", "1")
        assert storage.read("todo", "1") == {}

    def test_delete_item_excluded_from_select(self, storage):
        storage.write("todo", {"id": "1"})
        storage.write("todo", {"id": "2"})
        storage.delete("todo", "1")
        result = storage.select("todo")
        assert result == [{"id": "2"}]

    def test_delete_only_removes_target_type(self, storage):
        storage.write("todos", {"id": "1"})
        storage.write("notes", {"id": "1"})
        storage.delete("todos", "1")
        assert storage.select("todos") == []
        assert storage.select("notes") == [{"id": "1"}]
