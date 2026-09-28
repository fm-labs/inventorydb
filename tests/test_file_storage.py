"""Tests for FileBasedInventoryStorage and DirectoryBasedInventoryStorage."""

import json
import os

import pytest

from inventorydb.storage.file_storage import (
    DirectoryBasedInventoryStorage,
    FileBasedInventoryStorage,
)


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


def seed_file(base_dir: str, item_type: str, items: list) -> None:
    """Pre-create the JSON file that FileBasedInventoryStorage expects to exist."""
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

    def test_select_raises_when_file_missing(self, file_storage):
        """FileBasedInventoryStorage has no guard for a missing type file."""
        with pytest.raises(FileNotFoundError):
            file_storage.select("nonexistent_type")

    def test_select_returns_empty_list_for_empty_file(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [])
        assert file_storage.select("todo") == []


class TestFileBasedInventoryStorageWrite:
    def test_write_creates_new_item(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [])
        item = {"id": "1", "title": "Buy milk"}
        file_storage.write("todo", item)
        assert file_storage.select("todo") == [item]

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

    def test_read_returns_empty_dict_when_not_found(self, file_storage, base_dir):
        seed_file(base_dir, "todo", [{"id": "1"}])
        assert file_storage.read("todo", "999") == {}

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

    def test_delete_returns_true_even_if_id_missing(self, file_storage, base_dir):
        """Quirk: FileBasedInventoryStorage.delete always rewrites and returns True."""
        seed_file(base_dir, "todo", [{"id": "1"}])
        result = file_storage.delete("todo", "nonexistent")
        assert result is True
        # Original item is untouched
        assert len(file_storage.select("todo")) == 1


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

    def test_read_returns_empty_dict_when_not_found(self, dir_storage):
        dir_storage.write("todo", {"id": "1"})
        assert dir_storage.read("todo", "999") == {}

    def test_read_returns_empty_dict_when_type_missing(self, dir_storage):
        assert dir_storage.read("ghost_type", "1") == {}


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
