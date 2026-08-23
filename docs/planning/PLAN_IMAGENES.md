# Plan — Soporte de imágenes en preguntas

> **HISTÓRICO (plan ejecutado).** Las 7 secciones del plan están aplicadas (modelo, resolución, banco, render en Streamlit y visión en Gemini). Ver `docs/ARCHITECTURE.md` y `docs/DATA_MODEL.md` para la implementación real.

**Estado:** Aplicado (todas las fases del plan de imágenes completas)
**Decisiones de diseño:** imagen solo en el enunciado · almacenamiento local o URL · Gemini con visión en el feedback · render en Streamlit.

---

## 1. Modelo `Question` (refinar Fase 1)
- Añadir campo opcional `statement_image: str | None = None` a `src/models/question.py`
- Sin nuevo tipo; el valor será una URL (`http(s)://...`) o una ruta relativa a un archivo local (ej: `RQ-003.png`)
- Validación ligera: si no es URL, no debe estar vacío

## 2. Resolución de imágenes (nueva capa en `src/data/`)
- Nuevo módulo `src/data/images.py`:
  - `IMAGES_DIR = PROJECT_ROOT / "data" / "images"`
  - `image_source(question) -> str | Path | None`: devuelve la URL tal cual, resuelve la ruta local contra `data/images/`, o `None` si no hay imagen
- Extender `loader.py`:
  - `validate_image_references(questions)` → verifica que las rutas locales existan (con advertencia/error claro)
  - Carga sin cambios de interfaz

## 3. Banco de preguntas y muestras (refinar Fase 2)
- Generar 2–3 imágenes de ejemplo con Pillow (ya disponible vía Streamlit):
  - `RQ-003.png`: gráfica de barras de ventas (enero 100, febrero 120, marzo 90) — coincide con la pregunta existente
  - `RQ-002.png`: bolsa con bolas de colores (3 rojas, 2 verdes, 5 azules) para la de probabilidad
- Añadir `statement_image` a esas preguntas en `data/questions.json`
- La capacidad URL queda soportada por el resolver (probada con mocks, sin URLs falsas en el banco)

## 4. Interfaz Streamlit (aplicado en Fase 6) ✅
- Al presentar una pregunta, si `image_source` devuelve algo → `st.image(path_o_url)` (acepta ambos)

## 5. Proveedor LLM con visión (aplicado en Fase 5) ✅
- La interfaz `FeedbackProvider` recibe la pregunta; el `GeminiFeedbackProvider` arma los `parts` de `google-genai` con texto + imagen (`inline_data`) al generar feedback de preguntas con imagen
- Imagen local: se leen los bytes (resueltos por `image_source` contra `data/images/`) y el MIME se infiere de la extensión
- Imagen por URL: se descarga con `urllib` (timeout 10s) y se pasa como `inline_data`
- El `MockFeedbackProvider` ignora la imagen

## 6. Pruebas (refinar Fase 7)
- Modelo acepta `statement_image` local y URL
- `image_source`: None / Path local / URL sin cambios
- `validate_image_references` detecta rutas inexistentes

## 7. Documentación
- Actualizar `docs/specs/01_specification.md` (estructura de pregunta con imagen opcional + criterio de presentación)

---

## Orden de ejecución
1 → 2 → 3 → 6 → 5 → 4 (aplicados) · 7 al cierre.