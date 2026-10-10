"""LangGraph agent that generates tests for modified Java files."""

from __future__ import annotations

import json
import operator
import os
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import InjectedState
from typing_extensions import TypedDict


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if __package__:
    from .auxiliary_functions import (
        clean_java_output,
        compile_generated_test,
        find_test_file,
        get_dependencies,
        get_docs_context,
        get_modified_source_files,
        get_source_file_diff,
        read_file,
        run_maven_tests,
        validate_generated_test,
        write_test_content,
    )
else:
    from auxiliary_functions import (
        clean_java_output,
        compile_generated_test,
        find_test_file,
        get_dependencies,
        get_docs_context,
        get_modified_source_files,
        get_source_file_diff,
        read_file,
        run_maven_tests,
        validate_generated_test,
        write_test_content,
    )


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
    repo_path: str
    exception_occurred: bool
    exception_message: str


def _repository_root(repo_path: str) -> Path:
    """Resolve the supplied repository path and reject paths outside it."""
    repository = Path(repo_path).resolve()
    if not repository.is_dir():
        raise NotADirectoryError(f"Repository directory does not exist: {repository}")
    return repository


def _repository_file(repo_path: str, file_path: str) -> Path:
    """Resolve a repository-relative or in-repository absolute file path."""
    repository = _repository_root(repo_path)
    candidate = Path(file_path)
    resolved = (candidate if candidate.is_absolute() else repository / candidate).resolve()
    if not resolved.is_relative_to(repository):
        raise ValueError(f"File path must remain inside the repository: {file_path}")
    return resolved


def _relative_repository_path(repo_path: str, file_path: str) -> str:
    return _repository_file(repo_path, file_path).relative_to(
        _repository_root(repo_path)
    ).as_posix()


def _require_java_source(repo_path: str, file_path: str) -> str:
    relative_path = _relative_repository_path(repo_path, file_path)
    source_path = _repository_root(repo_path) / relative_path
    if source_path.suffix != ".java" or not source_path.is_file():
        raise ValueError(f"Expected an existing Java source file: {file_path}")
    if not source_path.is_relative_to(_repository_root(repo_path) / "src" / "main"):
        raise ValueError(f"Source file must be under src/main: {file_path}")
    return relative_path


def _get_api_key() -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "No API key found. Set GEMINI_API_KEY in the repository .env."
        )
    return GEMINI_API_KEY


@tool(parse_docstring=True)
def get_modified_source_files_tool(
    repo_path: Annotated[str, InjectedState("repo_path")],
) -> list[str]:
    """List Java source files changed between HEAD~1 and HEAD under src/main.

    Args:
        repo_path: Repository root path supplied by the graph state.

    Returns:
        Repository-relative paths of modified Java source files.
    """
    return get_modified_source_files(str(_repository_root(repo_path)))


@tool(parse_docstring=True)
def get_source_file_diff_tool(
    file_name: str,
    repo_path: Annotated[str, InjectedState("repo_path")],
) -> str:
    """Read the Git diff for one Java source file between HEAD~1 and HEAD.

    Args:
        file_name: Repository-relative Java source path under src/main.
        repo_path: Repository root path supplied by the graph state.

    Returns:
        Unified Git diff text for the requested file.
    """
    source = _require_java_source(repo_path, file_name)
    return get_source_file_diff(str(_repository_root(repo_path)), source)


@tool(parse_docstring=True)
def read_file_tool(
    file_path: str,
    repo_path: Annotated[str, InjectedState("repo_path")],
) -> str:
    """Read any file located inside the selected repository.

    Args:
        file_path: Repository-relative path of the file to read.
        repo_path: Repository root path supplied by the graph state.

    Returns:
        File contents, or an empty string if the file does not exist.
    """
    return read_file(_repository_file(repo_path, file_path))


@tool(parse_docstring=True)
def get_dependencies_tool(
    file_name: str,
    repo_path: Annotated[str, InjectedState("repo_path")],
) -> dict[str, Any]:
    """Find project Java dependencies used directly or transitively by a source.

    Args:
        file_name: Repository-relative Java source path under src/main.
        repo_path: Repository root path supplied by the graph state.

    Returns:
        Object with `dependencies` (path list), `exception_occurred` (boolean),
        and `exception_message` (string).
    """
    source = _require_java_source(repo_path, file_name)
    dependencies, exception_occurred, exception_message = get_dependencies(
        str(_repository_root(repo_path)),
        source,
    )
    return {
        "dependencies": dependencies,
        "exception_occurred": exception_occurred,
        "exception_message": exception_message,
    }


@tool(parse_docstring=True)
def find_test_file_tool(
    source_file: str,
    repo_path: Annotated[str, InjectedState("repo_path")],
) -> str | None:
    """Find the existing test file associated with a Java source file.

    Args:
        source_file: Repository-relative Java source path under src/main.
        repo_path: Repository root path supplied by the graph state.

    Returns:
        Repository-relative path to the matching test, or null if none exists.
    """
    source = _require_java_source(repo_path, source_file)
    test_path = find_test_file(str(_repository_root(repo_path)), source)
    if test_path is None:
        return None

    resolved_test = _repository_file(repo_path, str(test_path))
    if not resolved_test.is_relative_to(_repository_root(repo_path) / "src" / "test"):
        raise ValueError("Located test file is outside src/test.")
    return resolved_test.relative_to(_repository_root(repo_path)).as_posix()


@tool(parse_docstring=True)
def get_docs_context_tool(query: str) -> str | None:
    """Retrieve relevant excerpts from the repository Markdown documentation.

    Args:
        query: Changes, source behavior, or test requirements to search for.

    Returns:
        Relevant Markdown excerpts with their source paths, or null if none match.
    """
    return get_docs_context(query, _get_api_key())


@tool(parse_docstring=True)
def clean_java_output_tool(response: str) -> dict[str, Any]:
    """Extract Java test source code from a model response.

    Args:
        response: Raw model response, optionally containing Markdown code fences.

    Returns:
        Object with `code`, `information_source`, `passed`, and `error_message`.
    """
    code, information_source, passed, error_message = clean_java_output(response)
    return {
        "code": code,
        "information_source": information_source,
        "passed": passed,
        "error_message": error_message,
    }


@tool(parse_docstring=True)
def validate_generated_test_tool(
    test_code: str,
    repo_path: Annotated[str, InjectedState("repo_path")],
) -> dict[str, Any]:
    """Validate generated Java test structure and assertions using the AST checker.

    Args:
        test_code: Complete Java test source code to validate.
        repo_path: Repository root path supplied by the graph state.

    Returns:
        Object with `information_source`, `passed`, `exception_occurred`, and `message`.
    """
    information_source, passed, exception_occurred, message = validate_generated_test(
        test_code,
        _repository_root(repo_path),
    )
    return {
        "information_source": information_source,
        "passed": passed,
        "exception_occurred": exception_occurred,
        "message": message,
    }


@tool(parse_docstring=True)
def compile_generated_test_tool(
    test_code: str,
    repo_path: Annotated[str, InjectedState("repo_path")],
) -> dict[str, Any]:
    """Compile generated Java test source against this repository's Maven project.

    Args:
        test_code: Complete Java test source code to compile.
        repo_path: Repository root path supplied by the graph state.

    Returns:
        Object with `information_source`, `passed`, `exception_occurred`, and `message`.
    """
    information_source, passed, exception_occurred, message = compile_generated_test(
        test_code,
        _repository_root(repo_path),
    )
    return {
        "information_source": information_source,
        "passed": passed,
        "exception_occurred": exception_occurred,
        "message": message,
    }


@tool(parse_docstring=True)
def write_test_content_tool(
    modified_file_name: str,
    test_code: str,
    test_file_name: str | None = None,
    test_file_content: str | None = None,
    repo_path: Annotated[str, InjectedState("repo_path")] = ".",
) -> str:
    """Write validated Java test code under the repository's src/test directory.

    Args:
        modified_file_name: Repository-relative Java source path under src/main.
        test_code: Complete validated Java test source to write.
        test_file_name: Existing associated test path under src/test, if present.
        test_file_content: Existing test contents; pass null when creating a test.
        repo_path: Repository root path supplied by the graph state.

    Returns:
        Repository-relative path of the written test file.
    """
    source = _require_java_source(repo_path, modified_file_name)
    repository = _repository_root(repo_path)
    if test_file_name:
        target_test = _repository_file(repo_path, test_file_name)
        if not target_test.is_relative_to(repository / "src" / "test"):
            raise ValueError("Test file must be located under src/test.")
        relative_test_name = target_test.relative_to(repository).as_posix()
    else:
        relative_test_name = None

    target_path = write_test_content(
        str(repository),
        relative_test_name,
        test_file_content,
        source,
        test_code,
    )
    resolved_target = _repository_file(repo_path, str(target_path))
    if not resolved_target.is_relative_to(repository / "src" / "test"):
        raise ValueError("Generated test path is outside src/test.")
    return resolved_target.relative_to(repository).as_posix()


tools = [
    get_modified_source_files_tool,
    get_source_file_diff_tool,
    read_file_tool,
    get_dependencies_tool,
    find_test_file_tool,
    get_docs_context_tool,
    clean_java_output_tool,
    validate_generated_test_tool,
    compile_generated_test_tool,
    write_test_content_tool,
]
tools_by_name = {registered_tool.name: registered_tool for registered_tool in tools}

if not GEMINI_API_KEY:
    raise RuntimeError(
        "No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in the repository .env."
    )

model = init_chat_model(
    model="gemini-2.5-flash",
    model_provider="google_genai",
    api_key=GEMINI_API_KEY,
    temperature=0.2,
)
model_with_tools = model.bind_tools(tools)

SYSTEM_PROMPT = """You are an autonomous Java test-generation agent.
Your task is to generate and update tests for Java source files modified in the repository specified by the user.
The repository path is provided in the graph state. Use the available tools to inspect that repository; never assume a different repository.

Available tools:
- get_modified_source_files_tool: list changed Java source files under src/main.
- get_source_file_diff_tool: inspect a modified source file's diff.
- read_file_tool: read any file located inside the repository.
- get_dependencies_tool: find related project Java classes.
- find_test_file_tool: locate an existing test for a source file.
- get_docs_context_tool: retrieve relevant project Markdown documentation.
- clean_java_output_tool: extract Java code and report whether extraction succeeded.
- validate_generated_test_tool: validate test structure and assertions.
- compile_generated_test_tool: compile the proposed test against the Maven project.
- write_test_content_tool: write a validated test under src/test.

For each modified Java source file, inspect its diff and source, relevant dependencies, any existing test, and applicable documentation. Generate tests that match the actual code and project conventions. Clean the generated code, validate it, and compile it before writing it. If validation or compilation fails without an exception, use the returned message to revise the test and retry. Do not write a test that has not passed both validation and compilation.

If any tool raises an exception or returns `exception_occurred: true`, stop immediately and report the exception. Do not call any more tools after an exception. Process every modified Java source file before giving your final response. The Maven test suite is run automatically by the application after you finish; it is not a tool available to you. Do not claim a tool action succeeded unless its result confirms it."""


def llm_call(state: AgentState) -> dict[str, Any]:
    """Ask Gemini to respond or select the next repository tool."""
    response = model_with_tools.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    )
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def tool_node(state: AgentState) -> dict[str, Any]:
    """Execute the model-requested tools with the repository path from graph state."""
    results: list[ToolMessage] = []
    exception_message = ""
    for tool_call in state["messages"][-1].tool_calls:
        registered_tool = tools_by_name.get(tool_call["name"])
        if registered_tool is None:
            observation: Any = {
                "exception_occurred": True,
                "exception_message": f"Unknown tool: {tool_call['name']}",
            }
        else:
            try:
                observation = registered_tool.invoke(
                    {
                        **tool_call["args"],
                        "repo_path": state["repo_path"],
                    }
                )
            except Exception as exc:
                observation = {
                    "exception_occurred": True,
                    "exception_message": f"{type(exc).__name__}: {exc}",
                }

        if isinstance(observation, dict) and observation.get("exception_occurred"):
            exception_message = str(
                observation.get("exception_message")
                or observation.get("message")
                or "The tool reported an exception."
            )

        results.append(
            ToolMessage(
                content=json.dumps(observation, ensure_ascii=False, default=str),
                tool_call_id=tool_call["id"],
            )
        )
        if exception_message:
            break

    # Complete any parallel tool calls already requested by the model without executing them.
    completed_call_ids = {message.tool_call_id for message in results}
    for tool_call in state["messages"][-1].tool_calls:
        if tool_call["id"] not in completed_call_ids:
            results.append(
                ToolMessage(
                    content=json.dumps(
                        {
                            "exception_occurred": True,
                            "exception_message": (
                                "Skipped because an earlier tool call raised an exception."
                            ),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            )

    if exception_message:
        return {
            "messages": results,
            "exception_occurred": True,
            "exception_message": exception_message,
        }
    return {"messages": results}


def should_continue(state: AgentState) -> Literal["tool_node", "__end__"]:
    """Route model tool calls to the executor and finish on a normal response."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tool_node"
    return "__end__"


def after_tool_execution(
    state: AgentState,
) -> Literal["exception_report", "llm_call"]:
    """Stop on a tool exception or return to the model for the next step."""
    if state.get("exception_occurred", False):
        return "exception_report"
    return "llm_call"


def exception_report(state: AgentState) -> dict[str, list[AIMessage]]:
    """Append a final user-facing report after an exception."""
    message = state.get("exception_message", "Unknown tool exception.")
    return {
        "messages": [
            AIMessage(
                content=(
                    "Execution stopped because a tool raised an exception:\n"
                    f"{message}"
                )
            )
        ]
    }


agent_builder = StateGraph(AgentState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_node("exception_report", exception_report)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END],
)
agent_builder.add_conditional_edges(
    "tool_node",
    after_tool_execution,
    ["exception_report", "llm_call"],
)
agent_builder.add_edge("exception_report", END)
agent = agent_builder.compile()


def main() -> None:
    """Run the test-generation agent against the current repository."""
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Generate or update tests for the Java source files modified "
                        "in the specified repository. Use the available repository tools."
                    )
                )
            ],
            "llm_calls": 0,
            "repo_path": ".",
            "exception_occurred": False,
            "exception_message": "",
        },
        config={"recursion_limit": 100},
    )
    print(result["messages"][-1].content)
    if result.get("exception_occurred", False):
        return

    print("\nRunning Maven tests after test generation is complete...")
    try:
        repo_path = result.get("repo_path", ".")
        maven_result = run_maven_tests(str(_repository_root(repo_path)))
    except Exception as exc:
        print(f"Maven test execution raised an exception: {type(exc).__name__}: {exc}")
        return
    print(maven_result)


if __name__ == "__main__":
    main()
