from pathlib import Path

from src.config import PROJECT_ROOT
from src.models import Question

IMAGES_DIR = PROJECT_ROOT / "data" / "images"


def image_source(question: Question) -> str | Path | None:
    """Devuelve la fuente de la imagen del enunciado de una pregunta.

    - `None`: la pregunta no tiene imagen.
    - `str` (URL `http(s)://`): se devuelve tal cual.
    - `Path`: ruta local resuelta contra `data/images/`.
    """
    ref = question.statement_image
    if not ref:
        return None
    if ref.startswith(("http://", "https://")):
        return ref
    return IMAGES_DIR / ref