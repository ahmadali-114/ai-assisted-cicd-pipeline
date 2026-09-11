"""Environment-based configuration for the application."""

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Defaults make the service easy to run locally. Deployment environments can
    override values without changing source code.
    """

    app_name: str = getenv("APP_NAME", "System Health & Service Monitoring API")
    app_version: str = getenv("APP_VERSION", "1.0.0")
    environment: str = getenv("APP_ENVIRONMENT", "development")


settings = Settings()
