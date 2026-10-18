import os
from pathlib import Path
from pydantic import BaseModel

# Read .env if present
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

class Settings(BaseModel):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vajra.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "vajra-secret-key-defence-sih2026-air-force-secure")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    ML_ENABLED: bool = os.getenv("ML_ENABLED", "true").lower() in ("true", "1", "yes")
    OFFLINE_MODE: bool = os.getenv("OFFLINE_MODE", "true").lower() in ("true", "1", "yes")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    SIMULATOR_SPEED: float = float(os.getenv("SIMULATOR_SPEED", "1.0"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Also ensure MPLCONFIGDIR is set to /tmp or a local directory
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

settings = Settings()
