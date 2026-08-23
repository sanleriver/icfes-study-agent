# Modelo de Datos

Dominios Pydantic (`src/models/`) y esquema del banco de preguntas (`data/questions.json`).

## 1. Secciones

`Section` (`src/models/section.py`) — enum `str` con las 5 secciones del examen:

| Sección | Valor |
| :--- | :--- |
| Lectura Crítica | `LECTURA_CRITICA` |
| Razonamiento Cuantitativo | `RAZONAMIENTO_CUANTITATIVO` |
| Competencias Ciudadanas | `COMPETENCIAS_CIUDADANAS` |
| Comunicación Escrita | `COMUNICACION_ESCRITA` |
| Inglés | `INGLES` |

Cada sección expone `.label` (nombre legible en español). Toda pregunta del banco pertenece a una de ellas.

## 2. Pregunta (`Question`, `src/models/question.py`)

| Campo | Tipo | Descripción / validación |
| :--- | :--- | :--- |
| `id` | `str` | Identificador único (ej: `RQ-002`). |
| `section` | `Section` | Sección a la que pertenece. |
| `topic` | `str` | Tema de la pregunta. |
| `statement` | `str` | Enunciado. |
| `options` | `dict[str, str]` | **Exactamente** las claves `A, B, C, D`. |
| `correct_option` | `str` | Dentro de `A–D`. |
| `key_points` | `list[str]` | Puntos clave (usados por `fallback_feedback`). |
| `statement_image` | `str \| None` | Ruta local (relativa a `data/images/`) o URL `http(s)://`. No puede estar vacío si se indica. |

### Imágenes

- `src/data/images.py` — `image_source(question)` devuelve:
  - `None` si no hay imagen;
  - la **URL tal cual** (str);
  - un `Path` local resuelto contra `IMAGES_DIR = data/images/`.
- `validate_image_references(questions)` (en `loader.py`) lanza `FileNotFoundError` si una ruta local no existe (las URLs se ignoran).

### Ejemplo de pregunta en `data/questions.json`

```json
{
  "id": "RQ-002",
  "section": "RAZONAMIENTO_CUANTITATIVO",
  "topic": "Probabilidad",
  "statement": "Una bolsa contiene 3 bolas rojas, 2 verdes y 5 azules. ¿Cuál es la probabilidad de sacar una roja?",
  "options": {"A": "1/5", "B": "3/10", "C": "1/3", "D": "2/5"},
  "correct_option": "B",
  "key_points": ["La probabilidad es casos favorables sobre casos totales."],
  "statement_image": "RQ-002.png"
}
```

## 3. Estado de la sesión (`SessionState`, `src/models/session.py`)

Esquema del grafo LangGraph:

| Campo | Tipo | Reducer |
| :--- | :--- | :--- |
| `section` | `Section \| None` | sobrescribe |
| `num_questions` | `int` (default 10, ≥1) | sobrescribe |
| `questions` | `list[Question]` | sobrescribe |
| `answers` | `list[AnswerRecord]` | **`operator.add` (acumula)** |
| `results` | `list[EvaluationResult]` | sobrescribe |
| `feedbacks` | `list[Feedback]` | sobrescribe |
| `summary` | `Summary \| None` | sobrescribe |
| `message` | `str` | sobrescribe |

## 4. Otros modelos

| Modelo | Campos |
| :--- | :--- |
| `AnswerRecord` | `question_id`, `selected_option` (A–D validado). |
| `EvaluationResult` | `question_id`, `selected_option`, `correct_option`, `is_correct`. |
| `Feedback` | `question_id`, `explanation`, `error_analysis`, `positive_reinforcement`, `suggestion_topic`. |
| `TopicPerformance` | `topic`, `total`, `correct`. |
| `Summary` | `section`, `total_questions`, `correct_count`, `incorrect_count`, `score` (0–1), `by_topic`. |
| `FeedbackContent` (`src/providers/gemini.py`) | Esquema JSON del LLM (sin `question_id`); se completa al construir el `Feedback`. |

## 5. Banco de preguntas

- 20 preguntas, 4 por sección, en `data/questions.json`.
- Se carga con `load_questions()`; se filtra con `get_questions_by_section(section)` y se muestrea con `random_sample(section, n)` (respeta el agotamiento del banco).
- `random_sample` no repite preguntas dentro de una sesión.