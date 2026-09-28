import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymongo import MongoClient


def get_mongo_client(uri: str | None = None, ping: bool = False) -> "MongoClient[dict[str, Any]]":
    mongodb_uri = uri or os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI is not set in environment variables.")

    try:
        import pymongo
    except ImportError:
        raise ImportError("pymongo is not installed. Please install it with 'pip install pymongo'.") from None
    client: MongoClient[dict[str, Any]] = pymongo.MongoClient(mongodb_uri)

    if ping:
        try:
            # The ping command is cheap and does not require auth.
            client.admin.command('ping')
        except Exception as e:
            raise ConnectionError(f"Could not connect to MongoDB: {e}") from e
    return client


def mongodb_results_to_json(results: list[dict[str, Any]], strip_id: bool = True) -> list[dict[str, Any]]:
    json_results = []
    for doc in results:
        if strip_id and "_id" in doc:
            doc.pop("_id")
        elif "_id" in doc:
            doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
        json_results.append(doc)
    return json_results


def mongodb_result_to_json(result: dict[str, Any], strip_id: bool = True) -> dict[str, Any]:
    if result and "_id" in result:
        if strip_id and "_id" in result:
            result.pop("_id")
        elif "_id" in result:
            result["_id"] = str(result["_id"])  # Convert ObjectId to string
    return result
