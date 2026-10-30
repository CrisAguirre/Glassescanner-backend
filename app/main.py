import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import WEAK_ADMIN_KEYS, settings
from .routers import analyze, feedback, frames

logger = logging.getLogger("glassescanner")


def client_ip(request: Request) -> str:
    """IP del cliente para el rate limit.

    No se lee `X-Forwarded-For` aquí a propósito: un cliente podría rotarlo y
    obtener un cupo nuevo por minuto. Uvicorn reescribe `request.client` desde
    ese header solo cuando el peer es un proxy de confianza
    (`--proxy-headers --forwarded-allow-ips=...`), que es el caso de Render.
    """
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Límite básico por IP y ruta, en memoria y por proceso.

    Es suficiente para contener abuso accidental en una sola instancia. Para
    varias réplicas conviene moverlo a Redis o al proxy de Render.
    """

    def __init__(self, app, limit_per_minute: int = 60):
        super().__init__(app)
        self.limit = max(0, int(limit_per_minute))
        self.hits: dict[str, tuple[int, int]] = {}

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0 or request.method == "OPTIONS" or request.url.path == "/health":
            return await call_next(request)

        ip = client_ip(request)
        window = int(time.time() // 60)
        key = f"{ip}:{request.url.path}"
        count, stored_window = self.hits.get(key, (0, window))
        if stored_window != window:
            count = 0
        count += 1
        self.hits[key] = (count, window)

        # Evitar crecimiento indefinido de la tabla en procesos de larga vida.
        if len(self.hits) > 5000:
            self.hits = {k: v for k, v in self.hits.items() if v[1] == window}

        if count > self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Demasiadas solicitudes. Intenta de nuevo en un minuto."},
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


def validate_admin_key():
    settings.ADMIN_KEY = (settings.ADMIN_KEY or "").strip()
    weak = settings.ADMIN_KEY in WEAK_ADMIN_KEYS or len(settings.ADMIN_KEY) < 16
    is_production = (
        settings.ENVIRONMENT.lower() == "production"
        or os.getenv("RENDER", "").lower() == "true"
    )
    if weak:
        if is_production:
            raise RuntimeError(
                "ADMIN_KEY ausente o débil. Configura una clave de al menos 16 "
                "caracteres en el entorno de producción."
            )
        logger.warning(
            "ADMIN_KEY ausente o débil: el CRUD de monturas queda deshabilitado. "
            "Configura una clave larga en .env para desarrollo local."
        )
        settings.ADMIN_KEY = ""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_admin_key()
    yield


app = FastAPI(title="Glassescanner API", version="0.2.1", lifespan=lifespan)

# El limitador se agrega primero y CORS al final para que CORS quede en la capa
# más externa y también añada cabeceras a las respuestas 429.
app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.1", "db": bool(settings.MONGODB_URI)}


app.include_router(analyze.router)
app.include_router(frames.router)
app.include_router(feedback.router)
