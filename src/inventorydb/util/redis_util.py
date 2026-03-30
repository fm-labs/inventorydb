import os

def get_aioredis_client() -> "aioredis.Redis":
    try:
        import aioredis
    except ImportError:
        raise ImportError("aioredis is not installed. Please install it with 'pip install aioredis'.")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not redis_url:
        raise ValueError("REDIS_URL is not set in environment variables.")
    return aioredis.from_url(redis_url, decode_responses=True)


def get_redis_client() -> "redis.Redis":
    try:
        import redis
    except ImportError:
        raise ImportError("redis is not installed. Please install it with 'pip install redis'.")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not redis_url:
        raise ValueError("REDIS_URL is not set in environment variables.")
    return redis.from_url(redis_url, decode_responses=True)
