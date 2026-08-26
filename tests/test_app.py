import random
from pathlib import Path

import pytest

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None  # type: ignore

from src.models import Section

# app.py deprecado → movido a archive/app_streamlit.py (Fase Docker)
APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
ARCHIVE_PATH = Path(__file__).resolve().parent.parent / "archive" / "app_streamlit.py"
if not APP_PATH.exists() and ARCHIVE_PATH.exists():
    APP_PATH = ARCHIVE_PATH

pytestmark = pytest.mark.skipif(
    AppTest is None or not APP_PATH.exists(),
    reason="Streamlit deprecado / app.py no disponible (migrado a Flet)",
)


def _app() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception
    return at


def _configurar(at: AppTest, section: Section, n: int) -> None:
    at.selectbox[0].set_value(section)
    at.number_input[0].set_value(n)
    at.button[0].click()
    at.run()
    assert not at.exception


def _responder(at: AppTest, option: str) -> None:
    at.radio[0].set_value(option)
    at.button[0].click()
    at.run()
    assert not at.exception


def _jugar(at: AppTest, elegir) -> None:
    guard = 0
    while at.radio:
        guard += 1
        assert guard <= 4, "Demasiadas preguntas; el flujo no terminó"
        pending = at.session_state["pending"]
        _responder(at, elegir(pending))


class TestApp:
    def test_arranca_con_formulario_de_configuracion(self):
        at = _app()
        assert at.title[0].value == "Tutor adaptativo ICFES Saber Pro"
        assert len(at.selectbox) == 1
        assert len(at.selectbox[0].options) == 5
        assert len(at.number_input) == 1
        assert len(at.button) == 1

    def test_flujo_todas_correctas(self):
        at = _app()
        _configurar(at, Section.INGLES, 2)
        _jugar(at, lambda q: q["correct_option"])
        final = at.session_state["final"]
        assert final["summary"].total_questions == 2
        assert final["summary"].correct_count == 2
        assert final["summary"].score == 1.0
        assert final["feedbacks"] == []
        assert at.metric[0].value == "100%"
        assert at.metric[1].value == "2"

    def test_flujo_con_errores_genera_feedback(self):
        at = _app()
        _configurar(at, Section.INGLES, 2)

        def wrong(q):
            return next(o for o in ("A", "B", "C", "D") if o != q["correct_option"])

        _jugar(at, wrong)
        final = at.session_state["final"]
        assert final["summary"].correct_count == 0
        assert len(final["feedbacks"]) == 2
        assert len(at.expander) == 2

    def test_renderiza_imagen_en_pregunta_con_statement_image(self):
        random.seed(42)
        at = _app()
        _configurar(at, Section.RAZONAMIENTO_CUANTITATIVO, 4)

        images = 0
        guard = 0
        while at.radio:
            guard += 1
            assert guard <= 4
            images += len(at.image)
            pending = at.session_state["pending"]
            _responder(at, pending["correct_option"])
        assert 1 <= images <= 4  # al menos 1 imagen en la sesión (banco RQ mixto)

    def test_nueva_sesion_vuelve_a_configuracion(self):
        at = _app()
        _configurar(at, Section.INGLES, 1)
        _jugar(at, lambda q: q["correct_option"])
        assert at.selectbox == []
        at.button[0].click()
        at.run()
        assert not at.exception
        assert len(at.selectbox) == 1