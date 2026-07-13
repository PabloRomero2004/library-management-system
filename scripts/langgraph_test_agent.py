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

class TestAgentState(TypedDict):
    repo_path: str
    readme_content: str
    modified_files: list[ModifiedFile]


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
    """

    repo = Path(repo_path)

    stem = Path(source_file).stem

    candidates = list(repo.rglob(f"*{stem}*Test.*"))
    candidates += list(repo.rglob(f"test_{stem}.*"))
    candidates += list(repo.rglob(f"{stem}_test.*"))

    return candidates[0] if candidates else None


def get_dependencies(repo_path: str, file_name: str) -> list[str]:
    """
    TODO:
    Implementar usando AST, tree-sitter o similar.
    """
    return []


def get_context(state: TestAgentState) -> TestAgentState:

    repo = Path(state["repo_path"])

    state["modified_files"] = []

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


workflow.add_edge(START, "get_context")
workflow.add_edge("get_context", END)

app = workflow.compile()


def run_agent(repo_path: str) -> dict:
    initial_state = {
        "repo_path": repo_path,
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    result = run_agent(repo_path=".")
    print_context_summary(result)
