# 🎯 Objetivo Principal
Desarrollar un agente educativo inteligente para la preparación del examen ICFES Saber Pro en Colombia, utilizando LangGraph y Python, que simule un tutor personalizado capaz de:
 - Gestionar sesiones de estudio adaptativas
 - Seleccionar preguntas estratégicamente según el rendimiento del estudiante
 - Evaluar respuestas de manera automática
 - Proporcionar retroalimentación pedagógica personalizada
 - Integrar modelos de lenguaje (LLM) para explicaciones conceptuales

---

## 🛠️ Herramientas Base


| Herramienta | Propósito | Versión |
| :--- | :--- | :--- |
| **Python** | Lenguaje de programación principal | 3.12+ |
| **LangGraph** | Orquestación de flujos mediante grafos de estado | ≥ 0.0.20 |
| **LangChain** | Framework para integración con LLMs | ≥ 0.1.0 |
| **Pydantic** | Validación de datos y modelos | ≥ 2.0.0 |
| **Gemini 3.6 flash (o similar)** | Motor de lenguaje para generación de feedback | API actual |

---

## 📋 Alcance Inicial (MVP)

El proyecto se enfocará en construir un sistema funcional que permita:

1. Definir un estado de sesión tipado para almacenar el progreso del estudiante
2. Construir un grafo de estudio con nodos especializados
3. Controlar el flujo mediante bordes condicionales
4. Simular integración con LLM para retroalimentación pedagógica