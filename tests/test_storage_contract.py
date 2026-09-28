"""Shared contract tests run against every storage adapter.

Each adapter must behave identically for the operations below (see the
``InventoryStorage`` docstring). Adapter-specific behaviour belongs in the
per-adapter test modules.

Redis and MongoDB run in testcontainers and are skipped when Docker is not
available. The MongoDB image can be overridden with INVENTORYDB_TEST_MONGO_IMAGE.
"""

import os
import shutil
import subprocess

import pytest

from inventorydb.interface import InventoryStorage
from inventorydb.asyncio.async_storage import AsyncInventoryStorage
from inventorydb.storage.file_storage import (
    DirectoryBasedInventoryStorage,
    FileBasedInventoryStorage,
)
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage
from inventorydb.storage.sqlite_storage import SQLiteInventoryStorage

# See tests/test_mongodb_storage.py for why mongo:latest is not used.
MONGO_IMAGE = os.getenv("INVENTORYDB_TEST_MONGO_IMAGE", "mongo:7.0")


async def close_async_redis(client) -> None:
    """Close an async client; ``aclose`` only exists in redis-py >= 5.0.1."""
    await (client.aclose() if hasattr(client, "aclose") else client.close())


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


requires_docker = pytest.mark.skipif(not _docker_available(), reason="Docker is not available")


# ---------------------------------------------------------------------------
# Container fixtures (started lazily, only when a container backend is selected)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def redis_container():
    from testcontainers.community.redis import RedisContainer

    with RedisContainer() as container:
        yield container


@pytest.fixture(scope="module")
def mongo_container():
    from testcontainers.community.mongodb import MongoDbContainer

    with MongoDbContainer(MONGO_IMAGE) as container:
        yield container


# ---------------------------------------------------------------------------
# Sync adapters
# ---------------------------------------------------------------------------


def _inmemory(request, tmp_path):
    return InMemoryInventoryStorage()


def _file(request, tmp_path):
    return FileBasedInventoryStorage(str(tmp_path))


def _directory(request, tmp_path):
    return DirectoryBasedInventoryStorage(str(tmp_path))


def _sqlite(request, tmp_path):
    return SQLiteInventoryStorage(str(tmp_path / "inventory.db"))


def _redis(request, tmp_path):
    from inventorydb.storage.redis_storage import RedisInventoryStorage

    client = request.getfixturevalue("redis_container").get_client()
    client.flushdb()
    return RedisInventoryStorage(client)


def _mongodb(request, tmp_path):
    from inventorydb.storage.mongodb_storage import MongoDBInventoryStorage

    client = request.getfixturevalue("mongo_container").get_connection_client()
    client.drop_database("inventory")
    return MongoDBInventoryStorage(client)


SYNC_ADAPTERS = [
    pytest.param(_inmemory, id="inmemory"),
    pytest.param(_file, id="file"),
    pytest.param(_directory, id="directory"),
    pytest.param(_sqlite, id="sqlite"),
    pytest.param(_redis, id="redis", marks=requires_docker),
    pytest.param(_mongodb, id="mongodb", marks=requires_docker),
]


@pytest.fixture(params=SYNC_ADAPTERS)
def storage(request, tmp_path) -> InventoryStorage:
    return request.param(request, tmp_path)


class TestStorageContract:
    def test_implements_protocol(self, storage):
        assert isinstance(storage, InventoryStorage)

    # select

    def test_select_unknown_type_returns_empty_list(self, storage):
        assert storage.select("ghost") == []

    def test_select_returns_all_items_of_type(self, storage):
        storage.write("todo", {"id": "1", "title": "a"})
        storage.write("todo", {"id": "2", "title": "b"})
        items = sorted(storage.select("todo"), key=lambda i: i["id"])
        assert items == [{"id": "1", "title": "a"}, {"id": "2", "title": "b"}]

    def test_select_isolates_types(self, storage):
        storage.write("todo", {"id": "1", "title": "a"})
        storage.write("note", {"id": "1", "title": "b"})
        assert storage.select("todo") == [{"id": "1", "title": "a"}]

    def test_select_after_all_deleted_returns_empty_list(self, storage):
        storage.write("todo", {"id": "1"})
        storage.delete("todo", "1")
        assert storage.select("todo") == []

    # read

    def test_read_unknown_id_returns_none(self, storage):
        storage.write("todo", {"id": "1"})
        assert storage.read("todo", "999") is None

    def test_read_unknown_type_returns_none(self, storage):
        assert storage.read("ghost", "1") is None

    def test_read_returns_written_item(self, storage):
        item = {"id": "1", "title": "Buy milk"}
        storage.write("todo", item)
        assert storage.read("todo", "1") == item

    # write

    def test_write_returns_true(self, storage):
        assert storage.write("todo", {"id": "1"}) is True

    def test_write_replaces_whole_item(self, storage):
        storage.write("todo", {"id": "1", "title": "a", "note": "remove me"})
        storage.write("todo", {"id": "1", "title": "b"})
        assert storage.read("todo", "1") == {"id": "1", "title": "b"}
        assert len(storage.select("todo")) == 1

    def test_write_does_not_mutate_input(self, storage):
        item = {"id": "1", "title": "a"}
        storage.write("todo", item)
        assert item == {"id": "1", "title": "a"}

    def test_write_preserves_value_types(self, storage):
        item = {"id": "1", "done": False, "count": 3, "ratio": 0.5, "tags": ["a"], "meta": {"k": "v"}}
        storage.write("todo", item)
        assert storage.read("todo", "1") == item

    # delete

    def test_delete_existing_returns_true(self, storage):
        storage.write("todo", {"id": "1"})
        assert storage.delete("todo", "1") is True
        assert storage.read("todo", "1") is None

    def test_delete_unknown_id_returns_false(self, storage):
        storage.write("todo", {"id": "1"})
        assert storage.delete("todo", "999") is False
        assert storage.read("todo", "1") == {"id": "1"}

    def test_delete_unknown_type_returns_false(self, storage):
        assert storage.delete("ghost", "1") is False

    def test_delete_only_removes_target(self, storage):
        storage.write("todo", {"id": "1"})
        storage.write("todo", {"id": "2"})
        storage.write("note", {"id": "1"})
        storage.delete("todo", "1")
        assert storage.select("todo") == [{"id": "2"}]
        assert storage.read("note", "1") == {"id": "1"}

    # isolation

    def test_mutating_input_after_write_does_not_change_stored_item(self, storage):
        item = {"id": "1", "title": "a"}
        storage.write("todo", item)
        item["title"] = "changed"
        assert storage.read("todo", "1") == {"id": "1", "title": "a"}

    def test_mutating_read_result_does_not_change_stored_item(self, storage):
        storage.write("todo", {"id": "1", "title": "a"})
        storage.read("todo", "1")["title"] = "changed"
        storage.select("todo")[0]["title"] = "changed"
        assert storage.read("todo", "1") == {"id": "1", "title": "a"}


# ---------------------------------------------------------------------------
# Async adapters
# ---------------------------------------------------------------------------


async def _async_inmemory(request):
    return InMemoryInventoryStorage()


async def _async_redis(request):
    import redis.asyncio

    from inventorydb.asyncio.async_redis_storage import AsyncRedisInventoryStorage

    container = request.getfixturevalue("redis_container")
    client = redis.asyncio.Redis(
        host=container.get_container_host_ip(),
        port=int(container.get_exposed_port(6379)),
        decode_responses=True,
    )
    await client.flushdb()
    return AsyncRedisInventoryStorage(client)


ASYNC_ADAPTERS = [
    pytest.param(_async_inmemory, id="inmemory"),
    pytest.param(_async_redis, id="redis", marks=requires_docker),
]


@pytest.fixture(params=ASYNC_ADAPTERS)
async def async_storage(request) -> AsyncInventoryStorage:
    storage = await request.param(request)
    yield storage
    client = getattr(storage, "redis_client", None)
    if client is not None:
        await close_async_redis(client)


class TestAsyncStorageContract:
    def test_implements_protocol(self, async_storage):
        assert isinstance(async_storage, AsyncInventoryStorage)

    async def test_select_unknown_type_returns_empty_list(self, async_storage):
        assert await async_storage.aselect("ghost") == []

    async def test_read_unknown_returns_none(self, async_storage):
        assert await async_storage.aread("ghost", "1") is None

    async def test_read_returns_written_item(self, async_storage):
        item = {"id": "1", "title": "Buy milk"}
        assert await async_storage.awrite("todo", item) is True
        assert await async_storage.aread("todo", "1") == item

    async def test_write_preserves_value_types(self, async_storage):
        item = {"id": "1", "done": False, "count": 3, "ratio": 0.5, "tags": ["a"], "meta": {"k": "v"}}
        await async_storage.awrite("todo", item)
        assert await async_storage.aread("todo", "1") == item

    async def test_write_replaces_whole_item(self, async_storage):
        await async_storage.awrite("todo", {"id": "1", "title": "a", "note": "remove me"})
        await async_storage.awrite("todo", {"id": "1", "title": "b"})
        assert await async_storage.aread("todo", "1") == {"id": "1", "title": "b"}

    async def test_delete_returns_whether_item_existed(self, async_storage):
        await async_storage.awrite("todo", {"id": "1"})
        assert await async_storage.adelete("todo", "1") is True
        assert await async_storage.adelete("todo", "1") is False
        assert await async_storage.aread("todo", "1") is None
