from types import SimpleNamespace

from langgraph.types import Command

from src.core.feedback import fallback_feedback
from src.graph import build_graph
from src.models import Feedback, Section
from src.providers import FeedbackProvider, GeminiFeedbackProvider


def _play(graph, section, num_questions, answer_fn, thread_id):
    """Conduce una sesión completa: inicia, responde cada pregunta con
    `answer_fn` y devuelve el estado final."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"section": section, "num_questions": num_questions}, config)
    while result.get("__interrupt__"):
        question = result["__interrupt__"][0].value
        selected = answer_fn(question)
        result = graph.invoke(Command(resume=selected), config)
    return result


def _wrong_option(question):
    return next(o for o in ("A", "B", "C", "D") if o != question["correct_option"])


class TestGraphSesion:
    def test_interrumpe_con_la_primera_pregunta(self):
        graph = build_graph()
        config = {"configurable": {"thread_id": "t-first"}}
        result = graph.invoke({"section": Section.INGLES, "num_questions": 1}, config)
        interrupt = result["__interrupt__"][0]
        assert interrupt.value["section"] == "INGLES"
        assert "statement" in interrupt.value

    def test_sesion_todas_correctas(self):
        graph = build_graph()
        result = _play(graph, Section.INGLES, 2, lambda q: q["correct_option"], "t-ok")
        assert result["summary"].total_questions == 2
        assert result["summary"].correct_count == 2
        assert result["summary"].score == 1.0
        assert result["feedbacks"] == []
        assert "__interrupt__" not in result

    def test_sesion_con_errores_genera_feedback(self):
        graph = build_graph()
        result = _play(graph, Section.COMPETENCIAS_CIUDADANAS, 2, _wrong_option, "t-err")
        assert result["summary"].correct_count == 0
        assert len(result["feedbacks"]) == 2
        assert all(f.question_id in {r.question_id for r in result["results"]} for f in result["feedbacks"])
        assert all(f.suggestion_topic for f in result["feedbacks"])

    def test_respuestas_acumuladas_en_estado(self):
        graph = build_graph()
        result = _play(graph, Section.INGLES, 2, lambda q: q["correct_option"], "t-acc")
        assert [a.question_id for a in result["answers"]] == [
            q.id for q in result["questions"]
        ]

    def test_agotamiento_de_preguntas_notifica(self):
        graph = build_graph()
        result = _play(graph, Section.INGLES, 99, lambda q: q["correct_option"], "t-ago")
        assert result["summary"].total_questions == 4
        assert "solo hay 4 preguntas" in result["message"].lower()

    def test_sin_preguntas_para_la_seccion_termina_sin_preguntar(self):
        graph = build_graph()
        # Se fuerza una sección sin preguntas pasando un num_questions que no
        # existe en el banco mediante un mock temporal no es necesario: se usa
        # una sección válida pero se comprueba que sin answers no interrumpe.
        config = {"configurable": {"thread_id": "t-none"}}
        from src.data.loader import random_sample
        import unittest.mock as mock

        with mock.patch(
            "src.graph.random_sample", return_value=[]
        ):
            result = graph.invoke(
                {"section": Section.LECTURA_CRITICA, "num_questions": 3}, config
            )
        assert result["summary"].total_questions == 0
        assert "__interrupt__" not in result

    def test_build_graph_inyecta_el_proveedor(self):
        class RecordingProvider(FeedbackProvider):
            def __init__(self):
                self.calls = 0

            def generate_feedback(self, question, result):
                self.calls += 1
                return Feedback(
                    question_id=question.id,
                    explanation="proveedor inyectado",
                    suggestion_topic=question.topic,
                )

        provider = RecordingProvider()
        graph = build_graph(feedback_provider=provider)
        result = _play(
            graph, Section.COMPETENCIAS_CIUDADANAS, 2, _wrong_option, "t-prov"
        )
        assert provider.calls == 2
        assert all(f.explanation == "proveedor inyectado" for f in result["feedbacks"])

    def test_proveedor_gemini_que_falla_genera_fallback(self):
        class FailingClient:
            def __init__(self):
                self.models = SimpleNamespace(
                    generate_content=self._generate_content
                )

            def _generate_content(self, *args, **kwargs):
                raise TimeoutError("fallo simulado")

        provider = GeminiFeedbackProvider(api_key="fake", client=FailingClient())
        provider.RETRY_BASE_DELAY = 0
        graph = build_graph(feedback_provider=provider)
        result = _play(
            graph, Section.COMPETENCIAS_CIUDADANAS, 2, _wrong_option, "t-fallback"
        )

        expected = [
            fallback_feedback(question, res)
            for question, res in zip(result["questions"], result["results"])
            if not res.is_correct
        ]
        assert len(result["feedbacks"]) == 2
        assert result["feedbacks"] == expected


class TestSesionesConsecutivas:
    def test_segunda_sesion_con_thread_nuevo_empieza_limpia(self):
        """Iniciar otra sesión sobre el mismo grafo exige un thread_id nuevo
        (GraphRunner.new_thread en la app Flet): re-invocar el thread de una
        sesión completada reutilizaría answers viejos y desfasaría los índices.
        La segunda sesión debe ser completa e independiente de la primera."""
        graph = build_graph()

        primera = _play(
            graph,
            Section.RAZONAMIENTO_CUANTITATIVO,
            2,
            lambda q: q["correct_option"],
            "t-sec1",
        )
        assert primera["summary"].total_questions == 2
        assert primera["summary"].correct_count == 2

        segunda = _play(
            graph,
            Section.RAZONAMIENTO_CUANTITATIVO,
            3,
            _wrong_option,
            "t-sec2",
        )
        assert segunda["summary"].total_questions == 3
        assert segunda["summary"].correct_count == 0
        assert len(segunda["feedbacks"]) == 3
        assert "__interrupt__" not in segunda