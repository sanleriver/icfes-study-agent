from pydantic import BaseModel, Field, field_validator

from .section import Section

OPTION_KEYS = ("A", "B", "C", "D")


class Question(BaseModel):
    """Pregunta de una sección del examen ICFES Saber Pro."""

    id: str
    section: Section
    topic: str
    statement: str
    options: dict[str, str]
    correct_option: str
    key_points: list[str] = Field(default_factory=list)
    statement_image: str | None = Field(default=None)

    @field_validator("statement_image")
    @classmethod
    def validate_statement_image(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("La ruta de la imagen no puede estar vacía")
        return value

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: dict[str, str]) -> dict[str, str]:
        if set(value.keys()) != set(OPTION_KEYS):
            raise ValueError(f"Las opciones deben contener exactamente {OPTION_KEYS}")
        return value

    @field_validator("correct_option")
    @classmethod
    def validate_correct_option(cls, value: str, info) -> str:
        if value not in OPTION_KEYS:
            raise ValueError(f"La opción correcta debe ser una de {OPTION_KEYS}")
        return value