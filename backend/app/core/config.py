import warnings

from pydantic_settings import BaseSettings

_INSECURE_DEFAULT_KEY = "change-me-in-production"


class Settings(BaseSettings):
    PROJECT_NAME: str = "OpenRooms"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = (
        "postgresql+asyncpg://openrooms:openrooms@localhost:5432/openrooms"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://openrooms:openrooms@localhost:5432/openrooms"
    )

    SECRET_KEY: str = _INSECURE_DEFAULT_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

if settings.SECRET_KEY == _INSECURE_DEFAULT_KEY:
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "SECRET_KEY must be set to a strong random value in production. "
            "Set it via the SECRET_KEY environment variable."
        )
    warnings.warn(
        "Using default SECRET_KEY — not suitable for production.",
        stacklevel=1,
    )
