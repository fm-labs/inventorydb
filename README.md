# InventoryDB

Damn simple object store for Python dicts and Pydantic models across multiple backends
(in-memory, file-based, SQLite, Redis, MongoDB, and more).
Provides a minimal API for storing, retrieving, updating, and deleting objects.

__No thrills__ - **just a simple key-value store for serializable Python objects, with a consistent API across different storage backends.**


## What you get

- Basic CRUD operations: `save`, `get`, `filter`, `patch`, `delete`
- Multiple storage adapters (in-memory, file-based, SQLite, Redis, MongoDB)
- Optional Pydantic model validation with `PydanticInventory`
- Async support with some storage adapters (e.g. `AsyncRedisInventoryStorage`)
- Easy FastAPI integration with dependency injection


---

## Installation

```bash
pip install inventorydb
# or with uv
uv add inventorydb
```

---

## Quick Start

Every item must have an `"id"` field. Use `Inventory` with any storage adapter:

```python
from inventorydb.inventory import Inventory
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage

storage = InMemoryInventoryStorage()
todos = Inventory(item_type="todo", storage=storage)

todos.save({"id": "1", "title": "Buy milk", "done": False})
todos.save({"id": "2", "title": "Walk dog", "done": False})

todos.get("1")                   # → {"id": "1", "title": "Buy milk", "done": False}
todos.filter()                   # → [{"id": "1", ...}, {"id": "2", ...}]
todos.patch("1", {"done": True}) # → {"id": "1", ..., "done": True}
todos.delete("1")                # → True
```

Swapping the backend requires only changing the `storage` argument — the `Inventory`
API stays identical.

### Behaviour

All adapters follow the same contract (verified by a shared test suite):

- `get` returns `None` for a missing item; `filter` returns `[]` for an empty type.
- `save` inserts a new item or **replaces** an existing one entirely (it does not merge fields).
- `patch` merges the given fields into an existing item. It cannot change the item's `id`.
- `delete` returns `True` if the item was removed, `False` if it did not exist.
- Items you get back are copies; mutating them does not change stored data.

Errors are raised, not returned:

| Situation | Exception |
|---|---|
| `save` an item without an `id` | `ValueError` |
| `patch` a missing item | `inventorydb.errors.ItemNotFoundError` (a `LookupError`) |
| The storage backend reports a failed write | `inventorydb.errors.InventoryError` |

---

## Storage Adapters

| Adapter | Class | When to use |
|---|---|---|
| In-Memory | `InMemoryInventoryStorage` | Testing / prototyping — volatile |
| File (one file per type) | `FileBasedInventoryStorage` | Simple persistence for small datasets |
| File (one file per item) | `DirectoryBasedInventoryStorage` | Medium datasets; per-item file operations |
| SQLite | `SQLiteInventoryStorage` | ACID persistence with zero external deps |
| Redis | `RedisInventoryStorage` | High-performance / distributed sync access |
| MongoDB | `MongoDBInventoryStorage` | Document-oriented storage and complex queries |

### In-Memory

```python
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage

storage = InMemoryInventoryStorage()
```

No configuration needed. Data is lost when the process exits.
Also implements `AsyncInventoryStorage` — the async methods delegate to their
sync counterparts.

### File-Based (single file per type)

```python
from inventorydb.storage.file_storage import FileBasedInventoryStorage

storage = FileBasedInventoryStorage(base_dir="/var/data/myapp")
```

All items of one type are stored in `{base_dir}/{item_type}.json`.
The directory must exist before construction; type files are created on first write.
Item types must be safe file names (no `/`, `\`, `..`), otherwise `ValueError` is raised.

### File-Based (one file per item)

```python
from inventorydb.storage.file_storage import DirectoryBasedInventoryStorage

storage = DirectoryBasedInventoryStorage(base_dir="/var/data/myapp")
```

Items are stored at `{base_dir}/{item_type}/{id}.json`.
Type directories are created automatically on first write.
Item types and ids must be safe file names (no `/`, `\`, `..`), otherwise `ValueError` is raised.

### SQLite

```python
from inventorydb.storage.sqlite_storage import SQLiteInventoryStorage

storage = SQLiteInventoryStorage(db_path="myapp.db")
```

Uses a single `items` table with a `(item_type, id)` primary key and JSON
blob storage. The table is created automatically. No external dependencies needed.

### Redis

```python
import redis
from inventorydb.storage.redis_storage import RedisInventoryStorage

client = redis.Redis(host="localhost", port=6379, decode_responses=True)
storage = RedisInventoryStorage(redis_client=client)
```

Each item type is one Redis hash, `inventory:{item_type}`, mapping item ids to
JSON-encoded items, so value types (numbers, booleans, lists, nested dicts) are
preserved. Pass `key_prefix="myapp:"` to use a different prefix than `inventory:`.

Pass a pre-configured `redis.Redis` client (sync); `decode_responses` may be on or off.
Requires `redis-py`. `AsyncRedisInventoryStorage` takes a `redis.asyncio.Redis` client
and uses the same layout, so sync and async adapters can share data.

### MongoDB

```python
import pymongo
from inventorydb.storage.mongodb_storage import MongoDBInventoryStorage

client = pymongo.MongoClient("mongodb://localhost:27017")
storage = MongoDBInventoryStorage(mongo_client=client)
```

Items are stored in the `inventory` database, one collection per `item_type`.
The MongoDB `_id` field is stripped from results automatically.
Pass a pre-configured `pymongo.MongoClient`. Requires `pymongo`.

---

## Pydantic Models

Use `PydanticInventory` to validate items against a Pydantic `BaseModel`.
`save` and `get` return typed model instances instead of plain dicts.

```python
from pydantic import BaseModel
from inventorydb.pydantic import PydanticInventory
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage

class Todo(BaseModel):
    id: str
    title: str
    done: bool = False

todos = PydanticInventory(
    item_type="todo",
    storage=InMemoryInventoryStorage(),
    model_class=Todo,
)

todos.save(Todo(id="1", title="Buy milk"))
item: Todo = todos.get("1")   # returns a Todo instance, not a dict
print(item.done)              # False
```

---

## Async Usage

`AsyncRedisInventoryStorage` provides a fully async API for use with `asyncio`.
All methods are prefixed with `a` to distinguish them from sync equivalents.

```python
import redis.asyncio as aioredis
from inventorydb.asyncio.async_redis_storage import AsyncRedisInventoryStorage

client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
storage = AsyncRedisInventoryStorage(redis_client=client)

await storage.awrite("todo", {"id": "1", "title": "Buy milk"})
item   = await storage.aread("todo", "1")
items  = await storage.aselect("todo")
deleted = await storage.adelete("todo", "1")
```

---

## FastAPI Integration

### 1. Initialise storage with `lifespan`

Use FastAPI's `lifespan` context manager to create the client and storage adapter
once at startup and tear them down cleanly on shutdown.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as aioredis
from inventorydb.asyncio.async_redis_storage import AsyncRedisInventoryStorage

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
    app.state.storage = AsyncRedisInventoryStorage(redis_client=client)
    yield
    await client.aclose()

app = FastAPI(lifespan=lifespan)
```

### 2. Inject `Inventory` with `Depends`

Wrap the `Inventory` construction in a dependency function so routes stay clean
and the storage adapter is easy to swap out (e.g. in tests).

```python
from fastapi import Depends, Request
from inventorydb.inventory import Inventory

def get_todos(request: Request) -> Inventory:
    return Inventory(item_type="todo", storage=request.app.state.storage)

@app.get("/todos")
async def list_todos(todos: Inventory = Depends(get_todos)):
    return await todos.storage.aselect("todo")

@app.post("/todos")
async def create_todo(item: dict, todos: Inventory = Depends(get_todos)):
    return todos.save(item)
```

### 3. Sync routes with SQLite

For simpler apps without async requirements, SQLite is the easiest option.
Declare routes without `async def` — FastAPI runs them in a thread pool
automatically, keeping the event loop unblocked.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from inventorydb.inventory import Inventory
from inventorydb.storage.sqlite_storage import SQLiteInventoryStorage

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.storage = SQLiteInventoryStorage("app.db")
    yield

app = FastAPI(lifespan=lifespan)

def get_todos(request: Request) -> Inventory:
    return Inventory(item_type="todo", storage=request.app.state.storage)

@app.get("/todos")                      # sync — runs in threadpool
def list_todos(todos: Inventory = Depends(get_todos)):
    return todos.filter()
```

### 4. Override the dependency in tests

Swap the storage backend for the entire test run without touching any route code:

```python
from inventorydb.inventory import Inventory
from inventorydb.storage.inmemory_storage import InMemoryInventoryStorage
from fastapi.testclient import TestClient

def override_todos():
    return Inventory(item_type="todo", storage=InMemoryInventoryStorage())

app.dependency_overrides[get_todos] = override_todos
client = TestClient(app)
```

### Adapter recommendation by scenario

| Scenario | Recommended adapter |
|---|---|
| Single-process, low traffic | `SQLiteInventoryStorage` — zero deps, ACID, simple |
| Multi-worker / multi-process | `RedisInventoryStorage` or `MongoDBInventoryStorage` |
| Async routes | `AsyncRedisInventoryStorage` — non-blocking, fits the event loop |
| Testing / local dev | `InMemoryInventoryStorage` — fast, no infrastructure needed |

---

## Writing a Custom Adapter

Both interfaces are defined as `typing.Protocol` with `@runtime_checkable`.
This means **no import or inheritance is required** — any class that implements
the right methods is automatically a valid adapter (structural subtyping).

### Sync — `InventoryStorage`

```python
# inventorydb/interface.py
from typing import List, Protocol, runtime_checkable

@runtime_checkable
class InventoryStorage(Protocol):
    def select(self, item_type: str) -> List[dict]: ...
    def read(self, item_type: str, id: str) -> dict: ...
    def write(self, item_type: str, item: dict) -> bool: ...
    def delete(self, item_type: str, id: str) -> bool: ...
```

### Async — `AsyncInventoryStorage`

```python
# inventorydb/asyncio/async_storage.py
from typing import List, Protocol, runtime_checkable

@runtime_checkable
class AsyncInventoryStorage(Protocol):
    async def aselect(self, item_type: str) -> List[dict]: ...
    async def aread(self, item_type: str, id: str) -> dict: ...
    async def awrite(self, item_type: str, item: dict) -> bool: ...
    async def adelete(self, item_type: str, id: str) -> bool: ...
```

### Duck-typing — no inheritance needed

Because `Protocol` uses structural subtyping, a third-party class is a valid
adapter as long as it has the right methods — it does not need to import or
subclass anything from `inventorydb`:

```python
class MyCustomStorage:
    def select(self, item_type: str) -> list[dict]:
        ...

    def read(self, item_type: str, id: str) -> dict:
        ...

    def write(self, item_type: str, item: dict) -> bool:
        ...

    def delete(self, item_type: str, id: str) -> bool:
        ...

# Works — no explicit inheritance required
todos = Inventory(item_type="todo", storage=MyCustomStorage())
```

### Optional explicit inheritance

You can still inherit from the Protocol if you want IDE support for "find all
implementations" or early feedback from a type checker when a method is missing:

```python
from inventorydb.interface import InventoryStorage

class MyCustomStorage(InventoryStorage):  # explicit, but optional
    ...
```

### Runtime checks with `isinstance`

Both protocols are `@runtime_checkable`, so you can verify compatibility at
runtime without instantiating the adapter:

```python
from inventorydb.interface import InventoryStorage

isinstance(MyCustomStorage(), InventoryStorage)  # True
isinstance("not a storage", InventoryStorage)    # False
```
