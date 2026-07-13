"""Agente base para generación de tests con LangGraph.

Ubicación recomendada: scripts/langgraph_test_agent.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph


class TestAgentState(TypedDict):
    repo_path: str
    target_class: str
    readme_content: str
    modified_files_context: list[dict[str, Any]]


def _run_git(repo_path: str, *args: str) -> str:
    """Ejecuta un comando git y devuelve la salida estándar."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return completed.stdout.strip() or completed.stderr.strip()
    return completed.stdout.strip()


def _list_modified_files(repo_path: str) -> list[str]:
    """Obtiene los archivos modificados usando git status."""
    output = _run_git(repo_path, "status", "--porcelain")
    files: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        candidate = line[3:].strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ")[-1]
        if not candidate:
            continue
        full_path = Path(repo_path) / candidate
        if full_path.exists() and full_path.is_dir():
            continue
        files.append(candidate)
    return sorted(set(files))


def _find_test_file(repo_path: str, relative_path: str) -> str:
    """Intenta localizar un fichero de test asociado al archivo modificado."""
    path = Path(relative_path)
    candidates = []
    if path.suffix in {".java", ".kt", ".py", ".js", ".ts"}:
        candidates.append(str(path.with_name(path.stem + "Test" + path.suffix)))

    if "/src/main/" in relative_path.replace("\\", "/"):
        normalized = relative_path.replace("\\", "/").replace("/src/main/", "/src/test/")
        candidates.append(normalized)

    for candidate in candidates:
        full_path = Path(repo_path) / candidate
        if full_path.exists():
            return candidate.replace("\\", "/")

    for root, _, files in os.walk(repo_path):
        for file_name in files:
            if file_name.endswith("Test.java") or file_name.endswith("_test.py"):
                full_path = Path(root) / file_name
                try:
                    relative = full_path.relative_to(repo_path).as_posix()
                except ValueError:
                    continue
                if path.stem.lower() in relative.lower():
                    return relative
    return ""


def _collect_dependency_manifests(repo_path: str) -> list[dict[str, str]]:
    """Recoge los ficheros de dependencias que existan en el repositorio."""
    manifests = [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "requirements.txt",
        "package.json",
        "pyproject.toml",
    ]
    dependency_files: list[dict[str, str]] = []
    for manifest_name in manifests:
        manifest_path = Path(repo_path) / manifest_name
        if manifest_path.exists():
            dependency_files.append(
                {
                    "file_name": manifest_name,
                    "content": manifest_path.read_text(encoding="utf-8", errors="ignore"),
                }
            )
    return dependency_files


def get_context(state: TestAgentState) -> TestAgentState:
    """Recoge el README y la información de cada archivo modificado usando git."""
    repo_path = state.get("repo_path", os.getcwd())
    repo_path = os.path.abspath(repo_path)

    readme_path = None
    for candidate in ("README.md", "README.MD", "readme.md", "README.txt"):
        candidate_path = Path(repo_path) / candidate
        if candidate_path.exists():
            readme_path = candidate_path
            break

    readme_content = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path else ""

    modified_files = _list_modified_files(repo_path)
    context_entries: list[dict[str, Any]] = []

    for relative_path in modified_files:
        absolute_path = Path(repo_path) / relative_path
        if absolute_path.exists() and absolute_path.is_dir():
            continue

        file_content = ""
        if absolute_path.exists() and absolute_path.is_file():
            file_content = absolute_path.read_text(encoding="utf-8", errors="ignore")

        file_changes = _run_git(repo_path, "diff", "--", relative_path)
        if not file_changes:
            file_changes = _run_git(repo_path, "diff", "--cached", "--", relative_path)

        context_entries.append(
            {
                "file_name": relative_path.replace("\\", "/"),
                "file_content": file_content,
                "file_changes": file_changes,
                "test_file": _find_test_file(repo_path, relative_path),
                "dependencies": _collect_dependency_manifests(repo_path),
            }
        )

    state["readme_content"] = readme_content
    state["modified_files_context"] = context_entries
    return state



workflow = StateGraph(TestAgentState)
workflow.add_node("get_context", get_context)


workflow.add_edge(START, "get_context")
workflow.add_edge("get_context", END)

app = workflow.compile()


def run_agent(repo_path: str, target_class: str) -> dict:
    initial_state = {
        "repo_path": repo_path,
        "target_class": target_class,
        "readme_content": "",
        "modified_files_context": [],
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    result = run_agent(repo_path=".", target_class="User")
    print("README length:", len(result.get("readme_content", "")))
    print("Modified files:", len(result.get("modified_files_context", [])))
    if result.get("modified_files_context"):
        print("First context entry:")
        print(result["modified_files_context"][0])
