"""API dependency helpers."""

from app.core.config import Settings


def get_settings() -> Settings:
    """Build default settings for the application."""
    return Settings()


def get_runtime_context() -> dict[str, str]:
    """Expose lightweight runtime metadata to the API layer."""
    settings = get_settings()
    return {"app_name": settings.app_name, "environment": settings.environment}
