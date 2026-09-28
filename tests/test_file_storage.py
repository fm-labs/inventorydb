"""Tests for FileBasedInventoryStorage and DirectoryBasedInventoryStorage."""

import json
import os
import stat
import subprocess
import sys
import threading

import pytest

from inventorydb.interface import Item
from inventorydb.storage.file_storage import (
    DirectoryBasedInventoryStorage,
    FileBasedInventoryStorage,
)
from inventorydb.util.file_util import locked

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def base_dir(tmp_path) -> str:
    return str(tmp_path)


@pytest.fixture()
def file_storage(base_dir) -> FileBasedInventoryStorage:
    return FileBasedInventoryStorage(base_dir)


@pytest.fixture()
def dir_storage(base_dir) -> DirectoryBasedInventoryStorage:
    return DirectoryBasedInventoryStorage(base_dir)


def seed_file(base_dir: str, item_type: str, items: list[Item]) -> None:
    """Pre-create a type's JSON file with the given items."""
    path = os.path.join(base_dir, f"{item_type}.json")
    with open(path, "w") as f:
        json.dump(items, f)


# ===========================================================================
# FileBasedInventoryStorage
# ===========================================================================


class TestFileBasedInventoryStorageInit:
    def test_init_raises_on_missing_dir(self):
        with pytest.raises(ValueError, match="does not exist"):
            FileBasedInventoryStorage("/nonexistent/path/xyz")

    def test_init_succeeds_with_existing_dir(self, base_dir):
        storage = FileBasedInventoryStorage(base_dir)
        assert storage.inventory_dir == base_dir


class TestFileBasedInventoryStorageSelect:
    def test_select_returns_all_items(self, file_storage, base_dir):
        items = [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}]
        seed_file(base_dir, "todo", items)
        assert file_storage.select("todo") == items

    def test_select_returns_empty_list_when_file_missing(self, file_storage):
        assert file_storage.select("nonexistent_type") == []

    def test_select_returns_empty_list_for_empty_file(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [])
        assert file_storage.select("todo") == []


class TestFileBasedInventoryStorageWrite:
    def test_write_creates_new_item(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [])
        item = {"id": "1", "title": "Buy milk"}
        file_storage.write("todo", item)
        assert file_storage.select("todo") == [item]

    def test_write_creates_file_for_new_type(self, file_storage, base_dir):
        item = {"id": "1", "title": "Buy milk"}
        file_storage.write("todo", item)
        assert os.path.exists(os.path.join(base_dir, "todo.json"))
        assert file_storage.read("todo", "1") == item

    def test_write_returns_true(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [])
        assert file_storage.write("todo", {"id": "1"}) is True

    def test_write_updates_existing_item(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [{"id": "1", "title": "Old"}])
        file_storage.write("todo", {"id": "1", "title": "New"})
        result = file_storage.select("todo")
        assert len(result) == 1
        assert result[0]["title"] == "New"

    def test_write_update_does_not_duplicate(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [{"id": "1", "title": "x"}])
        file_storage.write("todo", {"id": "1", "title": "y"})
        assert len(file_storage.select("todo")) == 1

    def test_multiple_items_persist(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [])
        for i in range(3):
            file_storage.write("todo", {"id": str(i), "value": i})
        assert len(file_storage.select("todo")) == 3


class TestFileBasedInventoryStorageRead:
    def test_read_returns_item_by_id(self, file_storage, base_dir):
        item = {"id": "42", "title": "Hello"}
        seed_file(base_dir, "todo", [item])
        assert file_storage.read("todo", "42") == item

    def test_read_returns_none_when_not_found(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [{"id": "1"}])
        assert file_storage.read("todo", "999") is None

    def test_read_returns_none_when_file_missing(self, file_storage):
        assert file_storage.read("ghost_type", "1") is None

    def test_read_returns_correct_item_among_many(self, file_storage, base_dir):
        items = [{"id": str(i), "val": i} for i in range(5)]
        seed_file(base_dir, "todo", items)
        assert file_storage.read("todo", "3") == {"id": "3", "val": 3}


class TestFileBasedInventoryStorageDelete:
    def test_delete_removes_item(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [{"id": "1"}, {"id": "2"}])
        file_storage.delete("todo", "1")
        remaining = file_storage.select("todo")
        assert len(remaining) == 1
        assert remaining[0]["id"] == "2"

    def test_delete_returns_true(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [{"id": "1"}])
        assert file_storage.delete("todo", "1") is True

    def test_delete_returns_false_if_id_missing(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [{"id": "1"}])
        result = file_storage.delete("todo", "nonexistent")
        assert result is False
        # Original item is untouched
        assert len(file_storage.select("todo")) == 1

    def test_delete_returns_false_when_file_missing(self, file_storage):
        assert file_storage.delete("ghost_type", "1") is False


# ===========================================================================
# DirectoryBasedInventoryStorage
# ===========================================================================


class TestDirectoryBasedInventoryStorageInit:
    def test_init_raises_on_missing_dir(self):
        with pytest.raises(ValueError, match="does not exist"):
            DirectoryBasedInventoryStorage("/nonexistent/path/xyz")

    def test_init_succeeds_with_existing_dir(self, base_dir):
        storage = DirectoryBasedInventoryStorage(base_dir)
        assert storage.inventory_dir == base_dir


class TestDirectoryBasedInventoryStorageSelect:
    def test_select_returns_empty_list_when_type_dir_missing(self, dir_storage):
        assert dir_storage.select("ghost") == []

    def test_select_returns_written_items(self, dir_storage):
        items = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        for item in items:
            dir_storage.write("todo", item)
        result = dir_storage.select("todo")
        assert sorted(result, key=lambda x: x["id"]) == sorted(items, key=lambda x: x["id"])

    def test_select_returns_empty_list_for_empty_type_dir(self, dir_storage, base_dir):
        os.makedirs(os.path.join(base_dir, "empty_type"))
        assert dir_storage.select("empty_type") == []

    def test_multiple_types_are_isolated(self, dir_storage):
        dir_storage.write("todos", {"id": "1", "kind": "todo"})
        dir_storage.write("notes", {"id": "1", "kind": "note"})
        todos = dir_storage.select("todos")
        notes = dir_storage.select("notes")
        assert todos == [{"id": "1", "kind": "todo"}]
        assert notes == [{"id": "1", "kind": "note"}]


class TestDirectoryBasedInventoryStorageWrite:
    def test_write_returns_true(self, dir_storage):
        assert dir_storage.write("todo", {"id": "1"}) is True

    def test_write_creates_type_directory(self, dir_storage, base_dir):
        dir_storage.write("todo", {"id": "1"})
        assert os.path.isdir(os.path.join(base_dir, "todo"))

    def test_write_creates_individual_json_file(self, dir_storage, base_dir):
        dir_storage.write("todo", {"id": "abc"})
        assert os.path.isfile(os.path.join(base_dir, "todo", "abc.json"))

    def test_write_raises_on_missing_id(self, dir_storage):
        with pytest.raises(ValueError, match="'id'"):
            dir_storage.write("todo", {"title": "No ID here"})

    def test_write_raises_on_empty_id(self, dir_storage):
        with pytest.raises(ValueError, match="'id'"):
            dir_storage.write("todo", {"id": ""})

    def test_update_via_write_overwrites_fields(self, dir_storage):
        dir_storage.write("todo", {"id": "1", "title": "Original"})
        dir_storage.write("todo", {"id": "1", "title": "Updated"})
        assert dir_storage.read("todo", "1") == {"id": "1", "title": "Updated"}

    def test_update_via_write_does_not_duplicate(self, dir_storage):
        dir_storage.write("todo", {"id": "1"})
        dir_storage.write("todo", {"id": "1"})
        assert len(dir_storage.select("todo")) == 1


class TestDirectoryBasedInventoryStorageRead:
    def test_read_returns_item_by_id(self, dir_storage):
        item = {"id": "7", "title": "Test"}
        dir_storage.write("todo", item)
        assert dir_storage.read("todo", "7") == item

    def test_read_returns_none_when_not_found(self, dir_storage):
        dir_storage.write("todo", {"id": "1"})
        assert dir_storage.read("todo", "999") is None

    def test_read_returns_none_when_type_missing(self, dir_storage):
        assert dir_storage.read("ghost_type", "1") is None


class TestDirectoryBasedInventoryStorageDelete:
    def test_delete_removes_item_and_returns_true(self, dir_storage, base_dir):
        dir_storage.write("todo", {"id": "1"})
        result = dir_storage.delete("todo", "1")
        assert result is True
        assert not os.path.exists(os.path.join(base_dir, "todo", "1.json"))

    def test_delete_returns_false_when_item_missing(self, dir_storage):
        assert dir_storage.delete("todo", "nonexistent") is False

    def test_delete_only_removes_target_item(self, dir_storage):
        dir_storage.write("todo", {"id": "1"})
        dir_storage.write("todo", {"id": "2"})
        dir_storage.delete("todo", "1")
        remaining = dir_storage.select("todo")
        assert remaining == [{"id": "2"}]


# ===========================================================================
# Path validation (both file-based adapters)
# ===========================================================================


UNSAFE_NAMES = ["", ".", "..", "../escape", "a/b", "..\\escape", "nul\x00byte"]


class TestFileStoragePathValidation:
    @pytest.mark.parametrize("item_type", UNSAFE_NAMES)
    def test_file_storage_rejects_unsafe_item_type(self, file_storage, item_type):
        with pytest.raises(ValueError, match="Invalid item type"):
            file_storage.write(item_type, {"id": "1"})

    @pytest.mark.parametrize("item_type", UNSAFE_NAMES)
    def test_dir_storage_rejects_unsafe_item_type(self, dir_storage, item_type):
        with pytest.raises(ValueError, match="Invalid item type"):
            dir_storage.write(item_type, {"id": "1"})

    @pytest.mark.parametrize("item_id", [n for n in UNSAFE_NAMES if n])
    def test_dir_storage_rejects_unsafe_item_id(self, dir_storage, item_id):
        with pytest.raises(ValueError, match="Invalid item id"):
            dir_storage.write("todo", {"id": item_id})
        with pytest.raises(ValueError, match="Invalid item id"):
            dir_storage.read("todo", item_id)
        with pytest.raises(ValueError, match="Invalid item id"):
            dir_storage.delete("todo", item_id)

    def test_dir_storage_traversal_writes_nothing_outside_base_dir(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        storage = DirectoryBasedInventoryStorage(str(base))
        with pytest.raises(ValueError):
            storage.write("todo", {"id": "../../escaped"})
        assert list(tmp_path.rglob("escaped*")) == []


# ===========================================================================
# Concurrency and crash safety
# ===========================================================================


WRITER_PROCESS = """
import sys
from inventorydb.storage.file_storage import FileBasedInventoryStorage
storage = FileBasedInventoryStorage(sys.argv[1])
for i in range(int(sys.argv[3])):
    storage.write("todo", {"id": f"{sys.argv[2]}-{i}"})
"""


class TestFileBasedInventoryStorageConcurrency:
    def test_concurrent_processes_do_not_lose_writes(self, file_storage, base_dir):
        workers, per_worker = 4, 25
        procs = [
            subprocess.Popen([sys.executable, "-c", WRITER_PROCESS, base_dir, str(w), str(per_worker)])
            for w in range(workers)
        ]
        for p in procs:
            assert p.wait(timeout=60) == 0
        assert len(file_storage.select("todo")) == workers * per_worker

    def test_concurrent_threads_do_not_lose_writes(self, file_storage):
        def worker(w: int) -> None:
            for i in range(25):
                file_storage.write("todo", {"id": f"{w}-{i}"})

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        assert len(file_storage.select("todo")) == 100

    def test_write_waits_for_lock(self, file_storage, base_dir):
        done = threading.Event()

        def write() -> None:
            file_storage.write("todo", {"id": "1"})
            done.set()

        writer = threading.Thread(target=write)
        with locked(os.path.join(base_dir, ".todo.json.lock")):
            writer.start()
            assert not done.wait(timeout=0.3), "write completed while the lock was held"
        writer.join(timeout=10)
        assert done.is_set()
        assert file_storage.read("todo", "1") == {"id": "1"}

    def test_shared_readers_do_not_block_each_other(self, file_storage, base_dir):
        if sys.platform == "win32":
            pytest.skip("Windows locks are always exclusive")
        file_storage.write("todo", {"id": "1"})
        with locked(os.path.join(base_dir, ".todo.json.lock"), shared=True):
            result = []
            reader = threading.Thread(target=lambda: result.append(file_storage.select("todo")))
            reader.start()
            reader.join(timeout=5)
            assert result == [[{"id": "1"}]]


class TestFileBasedInventoryStorageFiles:
    def test_failed_write_keeps_original_file(self, file_storage, base_dir):
        file_storage.write("todo", {"id": "1"})
        with pytest.raises(TypeError):
            file_storage.write("todo", {"id": "2", "bad": object()})  # not JSON-serializable
        assert file_storage.select("todo") == [{"id": "1"}]

    def test_no_temp_files_left_behind(self, file_storage, base_dir):
        file_storage.write("todo", {"id": "1"})
        with pytest.raises(TypeError):
            file_storage.write("todo", {"id": "2", "bad": object()})
        assert sorted(os.listdir(base_dir)) == [".todo.json.lock", "todo.json"]

    def test_read_and_delete_of_missing_type_create_no_files(self, file_storage, base_dir):
        assert file_storage.select("ghost") == []
        assert file_storage.read("ghost", "1") is None
        assert file_storage.delete("ghost", "1") is False
        assert os.listdir(base_dir) == []

    def test_lock_file_is_not_an_item_type(self, file_storage, base_dir):
        file_storage.write("todo", {"id": "1"})
        assert file_storage.select(".todo") == []

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
    def test_write_keeps_file_permissions(self, file_storage, base_dir):
        file_storage.write("todo", {"id": "1"})
        path = os.path.join(base_dir, "todo.json")
        os.chmod(path, 0o600)
        file_storage.write("todo", {"id": "2"})
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


class TestDirectoryBasedInventoryStorageFiles:
    def test_failed_write_leaves_no_partial_item(self, dir_storage, base_dir):
        dir_storage.write("todo", {"id": "1"})
        with pytest.raises(TypeError):
            dir_storage.write("todo", {"id": "2", "bad": object()})
        assert dir_storage.select("todo") == [{"id": "1"}]
        assert dir_storage.read("todo", "2") is None

    def test_failed_overwrite_keeps_previous_version(self, dir_storage, base_dir):
        dir_storage.write("todo", {"id": "1", "v": 1})
        with pytest.raises(TypeError):
            dir_storage.write("todo", {"id": "1", "bad": object()})
        assert dir_storage.read("todo", "1") == {"id": "1", "v": 1}
        assert os.listdir(os.path.join(base_dir, "todo")) == ["1.json"]
