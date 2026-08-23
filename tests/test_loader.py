from src.data.loader import get_questions_by_section, load_questions, random_sample
from src.models import Section


def test_banco_carga_entre_16_y_20_preguntas():
    questions = load_questions()
    assert 16 <= len(questions) <= 20


def test_todas_las_preguntas_son_validas():
    questions = load_questions()
    assert all(q.correct_option in q.options for q in questions)


def test_cada_seccion_tiene_al_menos_tres_preguntas():
    questions = load_questions()
    for section in Section:
        by_section = get_questions_by_section(section, questions)
        assert len(by_section) >= 3, f"{section} tiene menos de 3 preguntas"


def test_get_questions_by_section_filtra_correctamente():
    questions = load_questions()
    ingles = get_questions_by_section(Section.INGLES, questions)
    assert all(q.section is Section.INGLES for q in ingles)


def test_random_sample_devuelve_n_preguntas():
    questions = load_questions()
    sample = random_sample(Section.LECTURA_CRITICA, 3, questions)
    assert len(sample) == 3
    assert all(q.section is Section.LECTURA_CRITICA for q in sample)
    assert len({q.id for q in sample}) == 3


def test_random_sample_no_repite_preguntas():
    questions = load_questions()
    sample = random_sample(Section.RAZONAMIENTO_CUANTITATIVO, 5, questions)
    ids = [q.id for q in sample]
    assert len(ids) == len(set(ids))


def test_random_sample_con_n_mayor_al_banco_devuelve_disponibles():
    questions = load_questions()
    ingles = get_questions_by_section(Section.INGLES, questions)
    sample = random_sample(Section.INGLES, 99, questions)
    assert len(sample) == len(ingles)


def test_random_sample_con_seccion_vacia():
    questions = load_questions()
    sample = random_sample(Section.COMPETENCIAS_CIUDADANAS, 0, questions)
    assert sample == []