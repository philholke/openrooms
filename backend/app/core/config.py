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

    # Redis / task queue
    REDIS_URL: str = "redis://redis:6379/0"

    # Application base URL (used for links in emails)
    APP_BASE_URL: str = "http://localhost:3000"

    # Email / SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@openrooms.dev"
    SMTP_FROM_NAME: str = "OpenRooms"
    SMTP_USE_TLS: bool = True
    EMAIL_ENABLED: bool = False

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
