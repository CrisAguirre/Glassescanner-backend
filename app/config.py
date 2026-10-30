from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Claves que nunca deben usarse en producción. Si ADMIN_KEY queda vacía o
# coincide con un placeholder, el CRUD de monturas se deshabilita.
WEAK_ADMIN_KEYS = {"", "cambia-esta-clave", "cambia-esta-clave-en-produccion"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173,"
        "https://glassescanner.vercel.app,https://grupoprismavision.vercel.app"
    )
    # Opcional para previews controlados, p. ej. ^https://.*\.vercel\.app$
    CORS_ORIGIN_REGEX: str = ""
    MAX_PHOTO_MB: float = Field(default=5, gt=0, le=50)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=0, le=1000)
    STORE_PHOTOS: bool = False
    MONGODB_URI: str = "mongodb://localhost:27017/glassescanner"
    MONGODB_DB: str = "glassescanner"
    # Sin valor por defecto: las mutaciones quedan bloqueadas hasta configurarla.
    ADMIN_KEY: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
