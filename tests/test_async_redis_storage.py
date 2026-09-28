"""Tests for AsyncRedisInventoryStorage using a real Redis via testcontainers."""

import redis.asyncio
import pytest
from testcontainers.community.redis import RedisContainer

from inventorydb.asyncio.async_redis_storage import AsyncRedisInventoryStorage


async def close_async_redis(client) -> None:
    """Close an async client; ``aclose`` only exists in redis-py >= 5.0.1."""
    await (client.aclose() if hasattr(client, "aclose") else client.close())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def redis_container():
    """Start a single Redis container for the entire test session."""
    with RedisContainer() as container:
        yield container


@pytest.fixture()
async def redis_client(redis_container):
    """Return an async Redis client and flush the DB before each test."""
    client = redis.asyncio.Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        decode_responses=True,
    )
    await client.flushdb()
    yield client
    await close_async_redis(client)


@pytest.fixture()
async def storage(redis_client) -> AsyncRedisInventoryStorage:
    return AsyncRedisInventoryStorage(redis_client)


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


class TestAsyncRedisInventoryStorageWrite:
    async def test_write_returns_true(self, storage):
        assert await storage.awrite("todo", {"id": "1", "title": "Buy milk"}) is True

    async def test_write_stores_item_in_type_hash(self, storage, redis_client):
        await storage.awrite("todo", {"id": "1", "title": "Buy milk"})
        assert await redis_client.hexists("inventory:todo", "1")

    async def test_write_stores_all_fields(self, storage):
        item = {"id": "1", "title": "Buy milk", "done": "false"}
        await storage.awrite("todo", item)
        assert await storage.aread("todo", "1") == item

    async def test_write_updates_existing_item(self, storage):
        await storage.awrite("todo", {"id": "1", "title": "Old"})
        await storage.awrite("todo", {"id": "1", "title": "New"})
        assert (await storage.aread("todo", "1"))["title"] == "New"

    async def test_write_update_does_not_duplicate(self, storage):
        await storage.awrite("todo", {"id": "1", "title": "x"})
        await storage.awrite("todo", {"id": "1", "title": "y"})
        assert len(await storage.aselect("todo")) == 1

    async def test_write_multiple_items(self, storage):
        for i in range(3):
            await storage.awrite("todo", {"id": str(i), "val": str(i)})
        assert len(await storage.aselect("todo")) == 3


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


class TestAsyncRedisInventoryStorageRead:
    async def test_read_returns_item_by_id(self, storage):
        item = {"id": "42", "title": "Hello"}
        await storage.awrite("todo", item)
        assert await storage.aread("todo", "42") == item

    async def test_read_returns_none_for_unknown_id(self, storage):
        assert await storage.aread("todo", "nonexistent") is None

    async def test_read_returns_none_for_unknown_type(self, storage):
        assert await storage.aread("ghost_type", "1") is None

    async def test_read_returns_correct_item_among_many(self, storage):
        for i in range(5):
            await storage.awrite("todo", {"id": str(i), "val": str(i)})
        assert await storage.aread("todo", "3") == {"id": "3", "val": "3"}

    async def test_read_does_not_cross_types(self, storage):
        await storage.awrite("todos", {"id": "1", "kind": "todo"})
        assert await storage.aread("notes", "1") is None


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------


class TestAsyncRedisInventoryStorageSelect:
    async def test_select_returns_empty_list_for_unknown_type(self, storage):
        assert await storage.aselect("todo") == []

    async def test_select_returns_all_items(self, storage):
        items = [{"id": "1", "title": "a"}, {"id": "2", "title": "b"}]
        for item in items:
            await storage.awrite("todo", item)
        result = sorted(await storage.aselect("todo"), key=lambda x: x["id"])
        assert result == sorted(items, key=lambda x: x["id"])

    async def test_select_isolates_types(self, storage):
        await storage.awrite("todos", {"id": "1", "kind": "todo"})
        await storage.awrite("notes", {"id": "1", "kind": "note"})
        assert await storage.aselect("todos") == [{"id": "1", "kind": "todo"}]
        assert await storage.aselect("notes") == [{"id": "1", "kind": "note"}]

    async def test_select_reflects_updates(self, storage):
        await storage.awrite("todo", {"id": "1", "title": "Old"})
        await storage.awrite("todo", {"id": "1", "title": "New"})
        result = await storage.aselect("todo")
        assert len(result) == 1
        assert result[0]["title"] == "New"

    async def test_select_returns_empty_list_after_all_deleted(self, storage):
        await storage.awrite("todo", {"id": "1"})
        await storage.adelete("todo", "1")
        assert await storage.aselect("todo") == []


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestAsyncRedisInventoryStorageDelete:
    async def test_delete_returns_true_when_item_exists(self, storage):
        await storage.awrite("todo", {"id": "1"})
        assert await storage.adelete("todo", "1") is True

    async def test_delete_returns_false_for_unknown_id(self, storage):
        assert await storage.adelete("todo", "nonexistent") is False

    async def test_delete_returns_false_for_unknown_type(self, storage):
        assert await storage.adelete("ghost_type", "1") is False

    async def test_delete_removes_item_from_redis(self, storage, redis_client):
        await storage.awrite("todo", {"id": "1"})
        await storage.adelete("todo", "1")
        assert not await redis_client.hexists("inventory:todo", "1")

    async def test_delete_item_no_longer_readable(self, storage):
        await storage.awrite("todo", {"id": "1"})
        await storage.adelete("todo", "1")
        assert await storage.aread("todo", "1") is None

    async def test_delete_item_excluded_from_select(self, storage):
        await storage.awrite("todo", {"id": "1"})
        await storage.awrite("todo", {"id": "2"})
        await storage.adelete("todo", "1")
        result = await storage.aselect("todo")
        assert result == [{"id": "2"}]

    async def test_delete_only_removes_target_type(self, storage):
        await storage.awrite("todos", {"id": "1"})
        await storage.awrite("notes", {"id": "1"})
        await storage.adelete("todos", "1")
        assert await storage.aselect("todos") == []
        assert await storage.aselect("notes") == [{"id": "1"}]


class TestAsyncRedisInventoryStorageLayout:
    async def test_write_preserves_value_types(self, storage):
        item = {"id": "1", "done": False, "count": 3, "tags": ["a"], "meta": {"k": None}}
        await storage.awrite("todo", item)
        assert await storage.aread("todo", "1") == item
        assert await storage.aselect("todo") == [item]

    async def test_works_with_bytes_client(self, redis_container):
        client = redis.asyncio.Redis(
            host=redis_container.get_container_host_ip(),
            port=int(redis_container.get_exposed_port(6379)),
        )
        try:
            await client.flushdb()
            storage = AsyncRedisInventoryStorage(client)
            await storage.awrite("todo", {"id": "1", "done": True})
            assert await storage.aread("todo", "1") == {"id": "1", "done": True}
            assert await storage.aselect("todo") == [{"id": "1", "done": True}]
        finally:
            await close_async_redis(client)

    async def test_shares_data_with_sync_storage(self, redis_container, storage):
        from inventorydb.storage.redis_storage import RedisInventoryStorage

        RedisInventoryStorage(redis_container.get_client()).write("todo", {"id": "1", "n": 1})
        assert await storage.aread("todo", "1") == {"id": "1", "n": 1}

    async def test_types_sharing_a_prefix_do_not_collide(self, storage):
        await storage.awrite("todo", {"id": "1"})
        await storage.awrite("todo:archive", {"id": "2"})
        assert await storage.aselect("todo") == [{"id": "1"}]
