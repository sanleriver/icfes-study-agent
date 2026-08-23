import json
import random
from pathlib import Path

from src.config import PROJECT_ROOT
from src.data.images import IMAGES_DIR, image_source
from src.models import Question, Section

DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "data" / "questions.json"


def load_questions(path: Path | str | None = None) -> list[Question]:
    """Carga las preguntas del banco desde un archivo JSON."""
    questions_path = Path(path) if path else DEFAULT_QUESTIONS_PATH
    with questions_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return [Question.model_validate(item) for item in data]


def validate_image_references(questions: list[Question]) -> list[Path]:
    """Verifica que las imágenes locales referenciadas existan.

    Devuelve la lista de rutas locales resueltas. Lanza `FileNotFoundError`
    con detalle si alguna ruta local referenciada no existe. Las URLs se ignoran.
    """
    missing = []
    for question in questions:
        source = image_source(question)
        if isinstance(source, Path) and not source.exists():
            missing.append((question.id, source))
    if missing:
        details = ", ".join(f"{qid}: {path}" for qid, path in missing)
        raise FileNotFoundError(f"Imágenes locales inexistentes: {details}")
    return [source for q in questions if isinstance((source := image_source(q)), Path)]


def get_questions_by_section(
    section: Section,
    questions: list[Question] | None = None,
) -> list[Question]:
    """Devuelve las preguntas que pertenecen a la sección indicada."""
    pool = questions if questions is not None else load_questions()
    return [q for q in pool if q.section is section]


def random_sample(
    section: Section,
    n: int,
    questions: list[Question] | None = None,
) -> list[Question]:
    """Selecciona aleatoriamente hasta `n` preguntas de la sección.

    Si la sección tiene menos preguntas que `n`, devuelve todas las disponibles
    (caso límite: agotamiento de preguntas).
    """
    pool = get_questions_by_section(section, questions)
    size = min(n, len(pool))
    return random.sample(pool, size)