from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    CORS_ORIGINS: str = "http://localhost:5173,https://glassescanner.vercel.app"
    MAX_PHOTO_MB: float = 5
    STORE_PHOTOS: bool = False
    MONGODB_URI: str = "mongodb://localhost:27017/glassescanner"
    MONGODB_DB: str = "glassescanner"

settings = Settings()
