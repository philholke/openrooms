from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "OpenRooms"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = (
        "postgresql+asyncpg://openrooms:openrooms@localhost:5432/openrooms"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://openrooms:openrooms@localhost:5432/openrooms"
    )

    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
