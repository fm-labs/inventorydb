import os


def get_async_redis_client() -> "redis.asyncio.Redis":
    try:
        import redis.asyncio
    except ImportError:
        raise ImportError("redis is not installed. Please install it with 'pip install redis'.")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not redis_url:
        raise ValueError("REDIS_URL is not set in environment variables.")
    return redis.asyncio.from_url(redis_url, decode_responses=True)


# Backwards-compatible name; the standalone aioredis package is abandoned and
# has been merged into redis-py as redis.asyncio.
get_aioredis_client = get_async_redis_client


def get_redis_client() -> "redis.Redis":
    try:
        import redis
    except ImportError:
        raise ImportError("redis is not installed. Please install it with 'pip install redis'.")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not redis_url:
        raise ValueError("REDIS_URL is not set in environment variables.")
    return redis.from_url(redis_url, decode_responses=True)
