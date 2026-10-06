from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

_client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient | None:
    global _client
    if _client is None and settings.MONGODB_URI:
        _client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
    return _client

def get_db():
    c = get_client()
    return c[settings.MONGODB_DB] if c is not None else None
