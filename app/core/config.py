from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional, Union


class Settings(BaseSettings):
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(default_factory=list)


    LOG_LEVEL: str = "INFO"  
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE: str = "app.log"

    # Database
    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_NAME: str = "inventory"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DATABASE_URL: Optional[str] = None

    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    #env
    SECRET_KEY: str = "for_example"
    ALGORITHM: str ="HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int =1

    # Validators

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        Convert comma-separated string to list[str]
        """
        if isinstance(v, str):
            # Remove surrounding quotes first
            v = v.strip('"').strip("'")
            # Then split by comma and filter empty strings
            return [x.strip() for x in v.split(",") if x.strip()]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v, info):
        if v:
            return v
        data = info.data
        return f"postgresql+psycopg2://{data['DB_USER']}:{data['DB_PASSWORD']}@{data['DB_HOST']}:{data['DB_PORT']}/{data['DB_NAME']}"

    # Properties
    @property
    def is_postgresql(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    # Config
    model_config = SettingsConfigDict(
        env_file="env/.env.local",
        case_sensitive=True,
        extra="ignore"
    )


# Global instance
settings = Settings()
