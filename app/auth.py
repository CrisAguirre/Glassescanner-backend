from fastapi import Header, HTTPException
from .config import settings

async def require_admin(x_admin_key: str | None = Header(default=None)):
    if not settings.ADMIN_KEY or x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(401, "Requiere X-Admin-Key de administrador")
