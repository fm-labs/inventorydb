"""Tests for SQLiteInventoryStorage."""

import pytest

from inventorydb.storage.sqlite_storage import SQLiteInventoryStorage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture()
def storage(db_path) -> SQLiteInventoryStorage:
    return SQLiteInventoryStorage(db_path)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestSQLiteInventoryStorageInit:
    def test_init_creates_db_file(self, db_path):
        import os
        SQLiteInventoryStorage(db_path)
        assert os.path.exists(db_path)

    def test_init_creates_items_table(self, db_path):
        import sqlite3
        SQLiteInventoryStorage(db_path)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='items'"
            ).fetchone()
        assert row is not None

    def test_init_is_idempotent(self, db_path):
        """Constructing a second instance against the same file must not raise."""
        SQLiteInventoryStorage(db_path)
        SQLiteInventoryStorage(db_path)


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


class TestSQLiteInventoryStorageWrite:
    def test_write_returns_true(self, storage):
        assert storage.write("todo", {"id": "1", "title": "Buy milk"}) is True

    def test_write_creates_item(self, storage):
        item = {"id": "1", "title": "Buy milk"}
        storage.write("todo", item)
        assert storage.read("todo", "1") == item

    def test_write_stores_all_field_types(self, storage):
        item = {"id": "1", "title": "x", "done": False, "priority": 2, "score": 3.14}
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
            storage.write("todo", {"id": str(i), "val": i})
        assert len(storage.select("todo")) == 3

    def test_write_persists_across_instances(self, db_path):
        SQLiteInventoryStorage(db_path).write("todo", {"id": "1", "title": "Hello"})
        result = SQLiteInventoryStorage(db_path).read("todo", "1")
        assert result == {"id": "1", "title": "Hello"}


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


class TestSQLiteInventoryStorageRead:
    def test_read_returns_item_by_id(self, storage):
        item = {"id": "42", "title": "Hello"}
        storage.write("todo", item)
        assert storage.read("todo", "42") == item

    def test_read_returns_none_for_unknown_id(self, storage):
        storage.write("todo", {"id": "1"})
        assert storage.read("todo", "nonexistent") is None

    def test_read_returns_none_for_unknown_type(self, storage):
        assert storage.read("ghost_type", "1") is None

    def test_read_returns_correct_item_among_many(self, storage):
        for i in range(5):
            storage.write("todo", {"id": str(i), "val": i})
        assert storage.read("todo", "3") == {"id": "3", "val": 3}

    def test_read_does_not_cross_types(self, storage):
        storage.write("todos", {"id": "1", "kind": "todo"})
        assert storage.read("notes", "1") is None


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------


class TestSQLiteInventoryStorageSelect:
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


class TestSQLiteInventoryStorageDelete:
    def test_delete_returns_true_when_item_exists(self, storage):
        storage.write("todo", {"id": "1"})
        assert storage.delete("todo", "1") is True

    def test_delete_returns_false_for_unknown_id(self, storage):
        assert storage.delete("todo", "nonexistent") is False

    def test_delete_returns_false_for_unknown_type(self, storage):
        assert storage.delete("ghost_type", "1") is False

    def test_delete_item_no_longer_readable(self, storage):
        storage.write("todo", {"id": "1"})
        storage.delete("todo", "1")
        assert storage.read("todo", "1") is None

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

    def test_delete_only_removes_target_item(self, storage):
        storage.write("todo", {"id": "1"})
        storage.write("todo", {"id": "2"})
        storage.delete("todo", "1")
        assert storage.read("todo", "2") == {"id": "2"}
