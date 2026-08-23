from src.config import Settings, get_settings

from .base import FeedbackProvider
from .gemini import GeminiFeedbackProvider
from .mock import MockFeedbackProvider

__all__ = [
    "FeedbackProvider",
    "MockFeedbackProvider",
    "GeminiFeedbackProvider",
    "create_feedback_provider",
]


def create_feedback_provider(settings: Settings | None = None) -> FeedbackProvider:
    """Crea el proveedor según la config (`FEEDBACK_PROVIDER=mock|gemini`)."""
    config = settings if settings is not None else get_settings()
    if config.uses_gemini:
        if not config.gemini_api_key:
            raise ValueError(
                "FEEDBACK_PROVIDER=gemini requiere GEMINI_API_KEY en .env"
            )
        return GeminiFeedbackProvider(
            api_key=config.gemini_api_key, model=config.gemini_model
        )
    return MockFeedbackProvider()