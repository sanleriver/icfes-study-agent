from enum import Enum


class Section(str, Enum):
    """Secciones del examen ICFES Saber Pro."""

    LECTURA_CRITICA = "LECTURA_CRITICA"
    RAZONAMIENTO_CUANTITATIVO = "RAZONAMIENTO_CUANTITATIVO"
    COMPETENCIAS_CIUDADANAS = "COMPETENCIAS_CIUDADANAS"
    COMUNICACION_ESCRITA = "COMUNICACION_ESCRITA"
    INGLES = "INGLES"

    @property
    def label(self) -> str:
        return {
            Section.LECTURA_CRITICA: "Lectura Crítica",
            Section.RAZONAMIENTO_CUANTITATIVO: "Razonamiento Cuantitativo",
            Section.COMPETENCIAS_CIUDADANAS: "Competencias Ciudadanas",
            Section.COMUNICACION_ESCRITA: "Comunicación Escrita",
            Section.INGLES: "Inglés",
        }[self]