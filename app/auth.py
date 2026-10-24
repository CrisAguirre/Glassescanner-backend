import secrets

from fastapi import Header, HTTPException

from .config import settings


async def require_admin(x_admin_key: str | None = Header(default=None)):
    expected = (settings.ADMIN_KEY or "").encode("utf-8")
    provided = (x_admin_key or "").encode("utf-8")
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(401, "Requiere X-Admin-Key de administrador")
