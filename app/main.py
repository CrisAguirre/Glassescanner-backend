from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import analyze, frames

app = FastAPI(title="Glassescanner API", version="0.2.0")

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0", "db": bool(settings.MONGODB_URI)}

app.include_router(analyze.router)
app.include_router(frames.router)
