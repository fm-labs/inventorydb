import os
from typing import List


def get_mongo_client(uri=None, ping: bool = False) -> "pymongo.MongoClient":
    mongodb_uri = uri or os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URL is not set in environment variables.")

    try:
        import pymongo
        client = pymongo.MongoClient(mongodb_uri)
    except ImportError:
        raise ImportError("pymongo is not installed. Please install it with 'pip install pymongo'.")

    if ping:
        try:
            # The ismaster command is cheap and does not require auth.
            client.admin.command('ismaster')
        except Exception as e:
            raise ConnectionError(f"Could not connect to MongoDB: {e}")
    return client


def mongodb_results_to_json(results: List[dict], strip_id=True) -> List[dict]:
    json_results = []
    for doc in results:
        if strip_id and "_id" in doc:
            doc.pop("_id")
        elif "_id" in doc:
            doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
        json_results.append(doc)
    return json_results


def mongodb_result_to_json(result: dict, strip_id=True) -> dict:
    if result and "_id" in result:
        if strip_id and "_id" in result:
            result.pop("_id")
        elif "_id" in result:
            result["_id"] = str(result["_id"])  # Convert ObjectId to string
    return result