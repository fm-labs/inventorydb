import json
import sqlite3
from typing import List

from inventorydb.interface import InventoryStorage

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS items (
        inventory_type  TEXT NOT NULL,
        id              TEXT NOT NULL,
        data            TEXT NOT NULL,
        PRIMARY KEY (inventory_type, id)
    )
"""


class SQLiteInventoryStorage(InventoryStorage):
    """SQLite-backed storage. Each item is stored as a JSON blob in a single table."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._connect() as conn:
            conn.execute(CREATE_TABLE_SQL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def select(self, inventory_type: str) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM items WHERE inventory_type = ?",
                (inventory_type,),
            ).fetchall()
        return [json.loads(row["data"]) for row in rows]

    def read(self, inventory_type: str, id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM items WHERE inventory_type = ? AND id = ?",
                (inventory_type, id),
            ).fetchone()
        return json.loads(row["data"]) if row else {}

    def write(self, inventory_type: str, item: dict) -> bool:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO items (inventory_type, id, data)
                VALUES (?, ?, ?)
                ON CONFLICT (inventory_type, id) DO UPDATE SET data = excluded.data
                """,
                (inventory_type, item["id"], json.dumps(item)),
            )
        return True

    def delete(self, inventory_type: str, id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM items WHERE inventory_type = ? AND id = ?",
                (inventory_type, id),
            )
        return cursor.rowcount > 0
