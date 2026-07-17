"""Agente base para generación de tests con LangGraph.

Ubicación recomendada: scripts/langgraph_test_agent.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


class SourceFile(TypedDict):
    file_name: str
    file_content: str

class ModifiedFile(TypedDict):
    modified_file_name: str
    modified_file_content: str
    modified_file_changes: str
    dependencies: list[SourceFile]
    test_file_name: str | None
    test_file_content: str | None

class TestAgentState(TypedDict, total=False):
    repo_path: str
    readme_content: str
    modified_files: list[ModifiedFile]
    modified_files_count: int
    current_file_ind: int
    context: str
    llm_response: str
    written_test_file: str


def git(repo_path: str, *args: str) -> str:
    """
    Ejecuta un comando git dentro del repositorio.
    """

    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return result.stdout.strip() or result.stderr.strip()

    return result.stdout.strip()


def read_file(path: Path) -> str:
    """
    Lee el contenido de un archivo, tolerando archivos no UTF-8.
    """
    if not path.exists():
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return path.read_text(encoding="utf-8", errors="ignore")


def sanitize_generated_code(text: str) -> str:
    """Quita delimitadores de bloque de código Markdown y devuelve solo el contenido del test."""
    if text is None:
        return ""

    cleaned = str(text).strip()
    if not cleaned:
        return ""

    fenced_block = re.search(r"```(?:\w+)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
    if fenced_block:
        return fenced_block.group(1).strip()

    return cleaned


def find_test_file(repo_path: str, source_file: str) -> Path | None:
    """
    Busca el archivo de test asociado al archivo modificado.
    Busca solo bajo src/test y con el patrón exacto <nombre>Test.*.
    """

    repo = Path(repo_path)
    test_root = repo / "src" / "test"
    if not test_root.exists():
        return None

    file_name = Path(source_file).stem
    expected_name = f"{file_name}Test"

    candidates = list(test_root.rglob(f"{expected_name}.*"))
    return candidates[0] if candidates else None


def get_dependencies(repo_path: str, file_name: str) -> list[str]:
    """
    Intenta encontrar nombres de archivos dependientes para un archivo dado.
    Implementación simple basada en referencias a tipos y otros archivos del repo.
    """
    repo = Path(repo_path)
    target_path = repo / file_name

    if not target_path.exists():
        return []

    content = read_file(target_path)
    candidates: list[str] = []

    # 1) Buscar referencias a nombres de archivo con extensión evidentes
    for token in content.split():
        base_name = Path(token).name
        if base_name.endswith((".java", ".kt", ".py", ".xml", ".json", ".yml", ".yaml", ".txt")):
            candidate_path = repo / base_name
            if candidate_path.exists():
                candidates.append(base_name)

    # 2) Buscar tipos Java usados en el archivo (ej. Author, User, Book)
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        for token in line.replace("{", " ").replace("(", " ").replace(")", " ").replace(";", " ").replace(".", " ").split():
            if not token:
                continue
            if token in {"private", "protected", "public", "final", "static", "return", "new", "this", "super"}:
                continue
            if token.startswith("//"):
                break
            if token and token[0].isupper():
                candidate_path = repo / "src" / "main" / "model" / f"{token}.java"
                if candidate_path.exists():
                    candidates.append(str(candidate_path.relative_to(repo)).replace("\\", "/"))

    return sorted(set(candidates))


def get_context(state: TestAgentState) -> TestAgentState:

    repo = Path(state["repo_path"])

    state["modified_files"] = []
    state["readme_content"] = ""
    state["modified_files_count"] = 0
    state["current_file_ind"] = 0
    state["context"] = ""

    #
    # README
    #

    readme = repo / "README.md"

    if readme.exists():
        state["readme_content"] = read_file(readme)
    else:
        state["readme_content"] = ""

    #
    # archivos modificados
    #

    modified_files = git(
        state["repo_path"],
        "diff",
        "--name-only",
        "HEAD~1",
        "HEAD",
        "--",
        "src/main",
    ).splitlines()

    for file_name in modified_files:

        file_path = repo / file_name

        if not file_path.exists():
            continue

        #
        # diff
        #

        diff = git(
            state["repo_path"],
            "diff",
            "HEAD~1",
            "HEAD",
            "--",
            file_name,
        )

        #
        # contenido
        #

        content = read_file(file_path)

        #
        # dependencias
        #

        dependency_objects = []

        dependency_names = get_dependencies(
            state["repo_path"],
            file_name,
        )

        for dependency in dependency_names:

            dependency_path = repo / dependency

            if dependency_path.exists():

                dependency_objects.append(
                    {
                        "file_name": dependency,
                        "file_content": read_file(dependency_path),
                    }
                )

        #
        # test
        #

        test_file = find_test_file(
            state["repo_path"],
            file_name,
        )

        test_name = None
        test_content = None

        if test_file is not None:

            test_name = str(test_file.relative_to(repo))
            test_content = read_file(test_file)

        #
        # guardar
        #

        state["modified_files"].append(
            {
                "modified_file_name": file_name,
                "modified_file_content": content,
                "modified_file_changes": diff,
                "dependencies": dependency_objects,
                "test_file_name": test_name,
                "test_file_content": test_content,
            }
        )

    state["modified_files_count"] = len(state["modified_files"])
    state["current_file_ind"] = 0

    return state


def send_context(state: TestAgentState) -> TestAgentState:
    """
    Prepara el contexto en inglés para el fichero modificado actual.
    """

    modified_files = state.get("modified_files", [])
    current_file_ind = int(state.get("current_file_ind", 0))
    modified_files_count = int(state.get("modified_files_count", len(modified_files)))

    if not modified_files:
        state["context"] = "No modified files were found in the repository."
        return state

    if current_file_ind >= modified_files_count:
        state["context"] = "All modified files have already been processed."
        return state

    modified_file = modified_files[current_file_ind]
    modified_file_name = modified_file.get("modified_file_name", "<unknown>")
    modified_file_content = modified_file.get("modified_file_content", "")
    modified_file_changes = modified_file.get("modified_file_changes", "")
    dependencies = modified_file.get("dependencies", [])
    test_file_name = modified_file.get("test_file_name")
    test_file_content = modified_file.get("test_file_content")

    dependency_lines = []
    if dependencies:
        for dependency in dependencies:
            dependency_name = dependency.get("file_name", "<unknown>")
            dependency_content = dependency.get("file_content", "")
            dependency_lines.append(f"- {dependency_name}")
            if dependency_content and dependency_content.strip():
                dependency_lines.append("  Content:")
                for line in dependency_content.splitlines():
                    dependency_lines.append(f"    {line}")
            else:
                dependency_lines.append("  Content: <empty file>")
    else:
        dependency_lines.append("- No dependencies found.")

    if test_file_name:
        test_name_text = test_file_name
    else:
        test_name_text = "No test file found."

    if test_file_content and test_file_content.strip():
        test_content_text = test_file_content
    else:
        test_content_text = "No test file content found."

    context_lines = [
        "You are an automated test generator for modified files.",
        "Your job is to inspect the modified file, its changes, its dependencies, and any existing test file, then produce the final content of a test file.",
        "Return only the final content of a test file, including imports and package declarations, and nothing else.",
        "",
        "Modified file name:",
        modified_file_name,
        "",
        "Modified file content:",
        modified_file_content or "<empty file>",
        "",
        "Changes for this file:",
        modified_file_changes or "No changes detected.",
        "",
        "Dependencies:",
        *dependency_lines,
        "",
        "Associated test file name:",
        test_name_text,
        "",
        "Associated test file content:",
        test_content_text,
        "",
        "Instructions:",
        "- If a test file already exists, use its content as a base and add the new tests required to validate the recent code changes.",
        "- If no test file exists, create a complete test file content that covers the new changes.",
        "- The final result must be only a test file content (with imports and package declarations included) and no extra commentary.",
    ]

    state["context"] = "\n".join(context_lines)
    state["current_file_ind"] = current_file_ind

    return state


def load_api_key() -> str:
    """Lee la API key desde la variable global cargada del .env."""
    if not GEMINI_API_KEY:
        raise RuntimeError("No se encontró ninguna API key. Define GEMINI_API_KEY o GOOGLE_API_KEY en el archivo .env del repositorio.")
    return GEMINI_API_KEY


def llm_call(state: TestAgentState) -> TestAgentState:
    """Invoca al modelo Gemini con la variable de estado context como prompt."""
    prompt = state.get("context", "") or ""
    if not prompt.strip():
        state["llm_response"] = "No hay contexto disponible para enviar al modelo."
        return state

    try:
        api_key = load_api_key()
    except Exception as exc:
        state["llm_response"] = f"Error al cargar la API key: {exc}"
        return state

    try:
        llm = init_chat_model(
            model="gemini-2.5-flash",
            model_provider="google_genai",
            api_key=api_key,
            temperature=0.2,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if hasattr(response, "content") else str(response)
        state["llm_response"] = sanitize_generated_code(response_text)

    except Exception as exc:
        state["llm_response"] = f"Error al llamar a LangChain: {exc}"

    return state


def build_test_file_path(repo_path: str, modified_file_name: str) -> Path:
    """Construye la ruta del archivo de test a partir del archivo modificado."""
    repo = Path(repo_path)
    modified_path = Path(modified_file_name)
    parts = modified_path.parts

    if len(parts) >= 2 and parts[0] == "src" and parts[1] == "main":
        relative_parts = parts[2:]
    else:
        relative_parts = parts

    if not relative_parts:
        return repo / "src" / "test" / "GeneratedTest.java"

    file_name = Path(relative_parts[-1]).stem
    target_name = f"{file_name}Test.java"
    target_parts = ("src", "test") + relative_parts[:-1] + (target_name,)
    return repo.joinpath(*target_parts)


def write_test_file(state: TestAgentState) -> TestAgentState:
    """Crea o sobrescribe el archivo de test según exista o no para el archivo modificado actual."""
    repo_path = state.get("repo_path", ".")
    modified_files = state.get("modified_files", [])
    current_file_ind = int(state.get("current_file_ind", 0))

    if not modified_files or current_file_ind >= len(modified_files):
        state["written_test_file"] = ""
        return state

    modified_file = modified_files[current_file_ind]
    generated_content = state.get("llm_response", "") or ""
    test_file_name = modified_file.get("test_file_name")
    test_file_content = modified_file.get("test_file_content")

    if test_file_name and str(test_file_name).strip() and test_file_content is not None:
        target_path = Path(repo_path) / test_file_name
    else:
        target_path = build_test_file_path(repo_path, modified_file.get("modified_file_name", ""))

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(generated_content, encoding="utf-8")

    state["written_test_file"] = str(target_path.relative_to(Path(repo_path))).replace("\\", "/")
    state["current_file_ind"] = current_file_ind + 1
    
    return state


def execute_test_files(state: TestAgentState) -> TestAgentState:
    """
    Ejecuta las pruebas unitarias del proyecto mediante Maven (mvn test)
    y almacena la salida del proceso en la respuesta del LLM para el reporte.
    """
    print("\n=== Ejecutando pruebas unitarias con Maven ===")
    repo_path = state.get("repo_path", ".")

    # En Windows, para ejecutar 'mvn' (que es un archivo .cmd/.bat) necesitamos shell=True
    is_windows = os.name == "nt"
    
    result = subprocess.run(
        ["mvn", "test"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
        shell=is_windows,
    )
    
    # Consolidamos la salida estándar y la de error para el reporte del agente
    output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    state["llm_response"] = f"Maven Execution Return Code: {result.returncode}\n\n{output}"
    return state


def should_continue(state: TestAgentState) -> str:
    """
    Determina si quedan más archivos modificados por procesar o 
    si se debe proceder a ejecutar los tests.
    """
    current_file_ind = int(state.get("current_file_ind", 0))
    modified_files_count = int(state.get("modified_files_count", 0))

    if current_file_ind >= modified_files_count:
        return "execute_test_files"
    
    return "send_context"


def print_context_summary(result: dict) -> None:
    """Imprime por pantalla los nombres relevantes del contexto recopilado."""
    print("Archivos modificados:")
    for item in result.get("modified_files", []):
        print(f"- {item.get('modified_file_name', '<sin nombre>')}")

        dependency_names = [dep.get("file_name", "") for dep in item.get("dependencies", []) if dep.get("file_name")]
        if dependency_names:
            print("  Dependencias:")
            for dep_name in dependency_names:
                print(f"    - {dep_name}")
        else:
            print("  Dependencias: ninguna")

        test_name = item.get("test_file_name")
        if test_name:
            print(f"  Test: {test_name}")
        else:
            print("  Test: no encontrado")


def print_generated_context(result: dict) -> None:
    """Imprime el contexto generado por send_context."""
    context = result.get("context", "")
    if not context:
        print("No se generó contexto.")
        return

    print("\n=== Contexto generado por send_context ===")
    print(context)


def print_llm_response(result: dict) -> None:
    """Imprime la respuesta del modelo Gemini."""
    response = result.get("llm_response", "")
    print("\n=== Respuesta de Gemini ===")
    if response:
        print(response)
    else:
        print("No se recibió respuesta del modelo.")


workflow = StateGraph(TestAgentState)
workflow.add_node("get_context", get_context)
workflow.add_node("send_context", send_context)
workflow.add_node("llm_call", llm_call)
workflow.add_node("write_test_file", write_test_file)
workflow.add_node("execute_test_files", execute_test_files)

workflow.add_edge(START, "get_context")
workflow.add_edge("get_context", "send_context")
workflow.add_edge("send_context", "llm_call")
workflow.add_edge("llm_call", "write_test_file")

workflow.add_conditional_edges(
    "write_test_file",
    should_continue,
    {
        "send_context": "send_context",
        "execute_test_files": "execute_test_files",
    }
)

workflow.add_edge("execute_test_files", END)

app = workflow.compile()


def run_agent(repo_path: str) -> dict:
    initial_state = {
        "repo_path": repo_path,
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    result = run_agent(repo_path=".")
    print_context_summary(result)
    print_generated_context(result)
    print_llm_response(result)
