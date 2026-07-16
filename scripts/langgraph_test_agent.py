"""Agente base para generación de tests con LangGraph.

Ubicación recomendada: scripts/langgraph_test_agent.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


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
        if not line or line.startswith("package") or line.startswith("import") or line.startswith("public"):
            continue
        for token in line.replace("{", " ").replace("(", " ").replace(")", " ").replace(";", " ").split():
            if not token:
                continue
            if token in {"private", "protected", "public", "final", "static", "return", "new", "this", "super"}:
                continue
            if token.startswith("//"):
                break
            if token.endswith((";", ",", "{", "}", "(", ")")):
                token = token.rstrip(";{},()")
            if token and token[0].isupper() and token[0:2] != "//":
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
            dependency_lines.append(f"- {dependency_name}")
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
    state["current_file_ind"] = current_file_ind + 1

    return state


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


workflow = StateGraph(TestAgentState)
workflow.add_node("get_context", get_context)
workflow.add_node("send_context", send_context)

workflow.add_edge(START, "get_context")
workflow.add_edge("get_context", "send_context")
workflow.add_edge("send_context", END)

app = workflow.compile()


def run_agent(repo_path: str) -> dict:
    initial_state = {
        "repo_path": repo_path,
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    result = run_agent(repo_path=".")
    print_context_summary(result)
