"""Agente base para generación de tests con LangGraph.

Ubicación recomendada: scripts/langgraph_test_agent.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


if __package__:
    from .auxiliary_functions import (
        clean_java_output,
        compile_generated_test,
        find_test_file,
        get_dependencies,
        get_modified_source_files,
        read_file,
        run_maven_tests,
        get_source_file_diff,
        validate_generated_test,
        write_test_content,
        get_docs_context
    )
else:
    from auxiliary_functions import (
        clean_java_output,
        compile_generated_test,
        find_test_file,
        get_dependencies,
        get_modified_source_files,
        read_file,
        run_maven_tests,
        get_source_file_diff,
        validate_generated_test,
        write_test_content,
        get_docs_context
    )


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
    written_test_file: str

class Report(TypedDict):
    information_source: str
    description: str
    generated_test: str

class TestFlowState(TypedDict, total=False):
    repo_path: str
    modified_files: list[ModifiedFile]
    modified_files_count: int
    current_file_ind: int
    attempts: int
    report_call_state: Report
    report_call_states: list[Report]
    context: str
    llm_response: str
    cleaning_passed: bool
    ast_parsing_passed: bool
    compiler_passed: bool
    test_execution_output: str
    llm_call_failed: bool
    exception_occurred: bool
    exception_message: str



def reset_file_iteration_state(state: TestFlowState) -> None:
    state["attempts"] = 0
    state["context"] = ""
    state["llm_response"] = ""
    state["ast_parsing_passed"] = False
    state["compiler_passed"] = False
    state["llm_call_failed"] = False
    state["report_call_state"] = {
        "generated_test": "",
        "information_source": "",
        "description": "",
    }


def advance_to_next_file(state: TestFlowState) -> None:
    state["current_file_ind"] = int(state.get("current_file_ind", 0)) + 1
    reset_file_iteration_state(state)


def add_report(
    state: TestFlowState,
    information_source: str,
    description: str,
) -> None:

    report: Report = {
        "information_source": information_source,
        "description": description,
        "generated_test": state.get("llm_response", "") or "",
        
    }
    state["report_call_state"] = report
    state.setdefault("report_call_states", []).append(report)



def get_context(state: TestFlowState) -> TestFlowState:

    repo = Path(state["repo_path"])

    state["modified_files"] = []
    state["readme_content"] = ""
    state["modified_files_count"] = 0
    state["current_file_ind"] = 0
    state["attempts"] = 0
    state["report_call_state"] = {
        "type": None,
        "generated_test": "",
        "information_source": "",
        "description": "",
        "attempt": 0,
        "modified_file_name": "",
    }
    state["report_call_states"] = []
    state["context"] = ""

    #
    # archivos modificados
    #

    modified_files = get_modified_source_files(state["repo_path"])

    for file_name in modified_files:

        file_path = repo / file_name

        if not file_path.exists():
            continue

        #
        # diff
        #

        diff = get_source_file_diff(state["repo_path"], file_name)

        # contenido
        content = read_file(file_path)

        # dependencias
        dependency_objects = []

        dependency_names, exception_occurred, exception_message = get_dependencies(
            state["repo_path"],
            file_name,
        )

        if exception_occurred:
            state["exception_occurred"] = True
            state["exception_message"] = exception_message
            return state

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
                "written_test_file": "",
            }
        )

    state["modified_files_count"] = len(state["modified_files"])
    state["current_file_ind"] = 0

    if state["modified_files_count"] == 0:
        state["exception_occurred"] = True
        state["exception_message"] = "No se encontraron archivos modificados en el repositorio."

    return state


def send_context(state: TestFlowState) -> TestFlowState:
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
            dependency_name = dependency["file_name"]
            dependency_content = dependency["file_content"]
            dependency_lines.append(f"- {dependency_name}")
            if dependency_content and dependency_content.strip():
                dependency_lines.append("  Content:")
                for line in dependency_content.splitlines():
                    dependency_lines.append(f"    {line}")
            else:
                dependency_lines.append("  Content: <empty file>")
    else:
        dependency_lines.append("- No dependencies found.")
    
    test_name_text = test_file_name or "No test file found."
    test_content_text = (
        test_file_content
        if test_file_content and test_file_content.strip()
        else "No test file content found."
    )
    
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

    return state


def load_api_key() -> str:
    """Lee la API key desde la variable global cargada del .env."""
    if not GEMINI_API_KEY:
        raise RuntimeError("No se encontró ninguna API key. Define GEMINI_API_KEY o GOOGLE_API_KEY en el archivo .env del repositorio.")
    return GEMINI_API_KEY


def llm_call(state: TestFlowState) -> TestFlowState:
    """Invoca al modelo Gemini con la variable de estado context como prompt."""
    state["exception_occurred"] = False
    state["exception_message"] = ""

    prompt = state.get("context", "") or ""
    if not prompt.strip():
        state["exception_occurred"] = True
        state["exception_message"] = "No hay contexto disponible para enviar al modelo."
        return state

    report = state.get("report_call_state", None)

    if report and report.get("description"):
        prompt = (
            f"{prompt}\n\nPrevious generated test:\n"
            f"{report.get('generated_test', '')}\n\nInformation source:\n"
            f"{report.get('information_source', '')}\nError message:\n"
            f"{report.get('description', '')}"
        )

    try:
        api_key = load_api_key()
    except Exception as exc:
        state["exception_occurred"] = True
        state["exception_message"] = f"Error loading the API key: {exc}"
        return state

    try:
        docs_context = get_docs_context(prompt, api_key)
    except Exception as exc:
        state["exception_occurred"] = True
        state["exception_message"] = f"Error fetching documentation context: {exc}"
        return state

    if docs_context:
        prompt = f"{prompt}\n\nDocumentation context:\n{docs_context}"

    try:
        llm = init_chat_model(
            model="gemini-2.5-flash",
            model_provider="google_genai",
            api_key=api_key,
            temperature=0.2,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = (
            response.content
            if isinstance(response.content, str)
            else str(response)
        )

    except Exception as exc:
        state["exception_occurred"] = True
        state["exception_message"] = f"Error calling LangChain: {exc}"
        return state

    state["llm_response"] = response_text

    state["attempts"] = int(state.get("attempts", 0)) + 1

    return state



def cleaning_validation(state: TestFlowState) -> TestFlowState:
    """Limpia el output de posible texto adicional o Markdown y comprueba que haya código Java y se queda solo con ese código."""
    state["cleaning_passed"] = False

    if not state.get("exception_occurred"):
        cleaned_code, info_source, passed, error_message = clean_java_output(state.get("llm_response", "") or "")
        if not passed:
            add_report(
                state,
                info_source,
                error_message
            )
        else:
            state["cleaning_passed"] = True
            state["llm_response"] = cleaned_code
        
    return state


def parsing_validation(state: TestFlowState) -> TestFlowState:
    """Valida el formato generado y su estructura Java mediante AST."""
    state["ast_parsing_passed"] = False

    info_source, passed, exception_occurred, message = validate_generated_test(
        state.get("llm_response", "") or "",
        Path(state["repo_path"]),
    )

    if exception_occurred:
        state["exception_occurred"] = True
        state["exception_message"] = f"Error al ejecutar el validador AST: {message}"
        return state

    if passed:
        state["ast_parsing_passed"] = True
    else:
        add_report(
            state,
            info_source,
            message,
        )

    return state


def compilation_validation(state: TestFlowState) -> TestFlowState:
    """Valida que el test generado compile con el proyecto y sus dependencias."""
    state["compiler_passed"] = False
    info_source, passed, exception_occurred, message = compile_generated_test(
        state.get("llm_response", "") or "",
        Path(state["repo_path"]),
    )
    if exception_occurred:
        state["exception_occurred"] = True
        state["exception_message"] = f"Error al ejecutar el compilador: {message}"
        return state

    if passed:
        state["compiler_passed"] = True
    else:
        add_report(
            state,
            info_source,
            message,
        )
    return state



def write_test_file(state: TestFlowState) -> TestFlowState:
    """Nodo que delega la escritura y conserva aquí las mutaciones del estado."""
    modified_files = state.get("modified_files", [])
    current_file_ind = int(state.get("current_file_ind", 0))
    validation_passed = state.get("cleaning_passed", False) and state.get("ast_parsing_passed", False) and state.get("compiler_passed", False)

    if not modified_files or current_file_ind >= len(modified_files):
        return state

    if validation_passed:
        modified_file = modified_files[current_file_ind]
        test_code = state.get("llm_response", "") or ""
        write_test_content(state.get("repo_path", "."), modified_file.get("test_file_name"), modified_file.get("test_file_content"), modified_file.get("modified_file_name", ""), test_code)
        modified_file["written_test_file"] = test_code
        
    else:
        modified_file["written_test_file"] = "No test file written due to validation errors."

    advance_to_next_file(state)
    
    return state



def execute_test_files(state: TestFlowState) -> TestFlowState:
    """Nodo que ejecuta la operación auxiliar y almacena su resultado."""
    state["test_execution_output"] = run_maven_tests(state.get("repo_path", "."))
    return state


def get_context_decision(state: TestFlowState) -> str:
    """
    Determina si se debe proceder a enviar el contexto al LLM o si se debe pasar al siguiente archivo.
    """
    exception_occurred = state.get("exception_occurred", False)

    if exception_occurred:
        return END
    
    return "send_context"


def llm_call_decision(state: TestFlowState) -> str:
    """
    Determina si se debe proceder a la validación o si se debe intentar otra llamada al LLM.
    """
    exception_occurred = state.get("exception_occurred", False)

    if exception_occurred:
        return END
    
    return "cleaning_validation"



def should_continue(state: TestFlowState) -> str:
    """
    Determina si quedan más archivos modificados por procesar o 
    si se debe proceder a ejecutar los tests.
    """
    current_file_ind = int(state.get("current_file_ind", 0))
    modified_files_count = int(state.get("modified_files_count", 0))

    if current_file_ind >= modified_files_count:
        return "execute_test_files"
    
    return "send_context"



def cleaning_validation_decision(state: TestFlowState) -> str:
    if state.get("cleaning_passed"):
        return "parsing_validation"
    return attempt_verification(state)

def parsing_validation_decision(state: TestFlowState) -> str:
    if state.get("exception_occurred"):
        return END
    if state.get("ast_parsing_passed"):
        return "compilation_validation"
    return attempt_verification(state)

def compilation_validation_decision(state: TestFlowState) -> str:
    if state.get("exception_occurred"):
        return END
    if state.get("compiler_passed"):
        return "write_test_file"
    return attempt_verification(state)


def attempt_verification(state: TestFlowState) -> str:
    """
    Determina si se debe intentar otra llamada al LLM o si se debe pasar al siguiente archivo.
    """
    attempts = int(state.get("attempts", 0))
    if attempts >= 10:
        return "write_test_file"
    
    return "llm_call"


def write_report_call_states(result: dict) -> None:
    """Guarda todos los reportes generados durante la ejecución."""
    
    repo_path = Path(result.get("repo_path", "."))
    report_call_states = result.get("report_call_states", [])
    modified_files = result.get("modified_files", [])

    (repo_path / "report_call_states.json").write_text(
            json.dumps(report_call_states, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
    (repo_path / "modified_files.json").write_text(
        json.dumps(modified_files, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )



def print_test_execution_output(result: dict) -> None:
    """Imprime la salida de la ejecución de Maven."""
    output = result.get("test_execution_output", "")
    print("\n=== Salida de las pruebas Maven ===")
    if output:
        print(output)
    else:
        print("No se ejecutaron las pruebas Maven.")


workflow = StateGraph(TestFlowState)
workflow.add_node("get_context", get_context)
workflow.add_node("send_context", send_context)
workflow.add_node("llm_call", llm_call)
workflow.add_node("cleaning_validation", cleaning_validation)
workflow.add_node("parsing_validation", parsing_validation)
workflow.add_node("compilation_validation", compilation_validation)
workflow.add_node("write_test_file", write_test_file)
workflow.add_node("execute_test_files", execute_test_files)

workflow.add_edge(START, "get_context")
workflow.add_conditional_edges(
    "get_context",
    get_context_decision,
    {
        "send_context": "send_context",
        END: END,
    },
)

workflow.add_edge("send_context", "llm_call")
workflow.add_conditional_edges(
    "llm_call",
    llm_call_decision,
    {
        "cleaning_validation": "cleaning_validation",
        END: END,
    }
)

workflow.add_conditional_edges(
    "cleaning_validation",
    cleaning_validation_decision,
    {
        "parsing_validation": "parsing_validation",
        "llm_call": "llm_call",
        "write_test_file": "write_test_file",
    },
)
workflow.add_conditional_edges(
    "parsing_validation",
    parsing_validation_decision,
    {
        END: END,
        "compilation_validation": "compilation_validation",
        "llm_call": "llm_call",
        "write_test_file": "write_test_file",
    },
)
workflow.add_conditional_edges(
    "compilation_validation",
    compilation_validation_decision,
    {
        END: END,
        "write_test_file": "write_test_file",
        "llm_call": "llm_call",
    },
)

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
    if(result.get("exception_occurred", False)):
        print("The program execution was interrupted due to an exception.\n")
        print(f"Exception: {result.get('exception_message', 'Unknown error')}")
    else:
        write_report_call_states(result)
        print_test_execution_output(result)
