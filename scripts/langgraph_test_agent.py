"""Agente base para generación de tests con LangGraph.

Ubicación recomendada: scripts/langgraph_test_agent.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
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

class ReportCallState(TypedDict):
    type: str | None
    generated_test: str
    information_source: str
    description: str
    attempt: int
    modified_file_name: str

class TestAgentState(TypedDict, total=False):
    repo_path: str
    readme_content: str
    modified_files: list[ModifiedFile]
    modified_files_count: int
    current_file_ind: int
    attempts: int
    report_call_state: ReportCallState
    report_call_states: list[ReportCallState]
    context: str
    llm_response: str
    test_execution_output: str
    written_test_file: str
    validation_errors: list[dict[str, str]]
    ast_parsing_passed: bool
    compiler_passed: bool
    llm_call_failed: bool
    file_skipped: bool


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


def record_validation_error(state: TestAgentState, node_name: str, message: str) -> None:
    errors = state.setdefault("validation_errors", [])
    errors.append({"node": node_name, "message": message})


def add_report(
    state: TestAgentState,
    report_type: str,
    information_source: str,
    description: str,
) -> None:
    report: ReportCallState = {
        "type": report_type,
        "generated_test": state.get("llm_response", "") or "",
        "information_source": information_source,
        "description": description,
        "attempt": int(state.get("attempts", 0)),
        "modified_file_name": get_current_modified_file_name(state),
    }
    state["report_call_state"] = report
    state.setdefault("report_call_states", []).append(report)


def validation_description(state: TestAgentState, fallback: str) -> str:
    errors = state.get("validation_errors", [])
    details = "; ".join(error.get("message", "") for error in errors if error.get("message"))
    return details or fallback


def get_current_modified_file_name(state: TestAgentState) -> str:
    modified_files = state.get("modified_files", [])
    current_file_ind = int(state.get("current_file_ind", 0))
    if 0 <= current_file_ind < len(modified_files):
        return modified_files[current_file_ind].get("modified_file_name", "")
    return ""


def reset_file_iteration_state(state: TestAgentState) -> None:
    state["attempts"] = 0
    state["context"] = ""
    state["llm_response"] = ""
    state["written_test_file"] = ""
    state["validation_errors"] = []
    state["ast_parsing_passed"] = False
    state["compiler_passed"] = False
    state["llm_call_failed"] = False
    state["file_skipped"] = False
    state["report_call_state"] = {
        "type": None,
        "generated_test": "",
        "information_source": "",
        "description": "",
        "attempt": 0,
        "modified_file_name": "",
    }


def advance_to_next_file(state: TestAgentState) -> None:
    state["current_file_ind"] = int(state.get("current_file_ind", 0)) + 1
    reset_file_iteration_state(state)


def clean_output(state: TestAgentState) -> TestAgentState:
    """Elimina Markdown y texto adicional, dejando solo la región de código Java."""
    response = state.get("llm_response", "") or ""
    if state.get("llm_call_failed"):
        return state

    if not response.strip():
        record_validation_error(state, "clean_output", "El output está vacío.")
        return state

    fenced_block = re.search(r"```[^\r\n]*\r?\n(.*?)\r?\n```", response, re.DOTALL)
    cleaned = fenced_block.group(1).strip() if fenced_block else response.strip()
    start_match = re.search(r"(?:package\b|import\b|public\s+class\b|class\b|@Test\b)", cleaned)
    end_index = cleaned.rfind("}")

    if not start_match or end_index == -1 or end_index < start_match.start():
        record_validation_error(state, "clean_output", "La región de código está vacía después de la partición.")
        state["llm_response"] = ""
        return state

    code_region = cleaned[start_match.start() : end_index + 1].strip()
    if not code_region:
        record_validation_error(state, "clean_output", "La región de código está vacía después de la partición.")
        state["llm_response"] = ""
        return state

    state["llm_response"] = code_region
    return state


def _ast_validator_java_source() -> str:
    return """import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ImportTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.util.JavacTask;
import javax.tools.JavaCompiler;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import javax.tools.JavaFileObject;
import java.io.File;
import java.util.Arrays;

public class LangGraphJavaAstValidator {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.out.println("FAIL:Se esperaba la ruta de un archivo Java.");
            System.exit(1);
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            System.out.println("FAIL:No se encontró el compilador Java en el JDK.");
            System.exit(1);
        }

        File file = new File(args[0]);
        if (!file.exists()) {
            System.out.println("FAIL:El archivo Java proporcionado no existe.");
            System.exit(1);
        }

        StandardJavaFileManager fileManager = compiler.getStandardFileManager(null, null, null);
        Iterable<? extends JavaFileObject> compilationUnits = fileManager.getJavaFileObjects(file);
        JavacTask task = (JavacTask) compiler.getTask(null, fileManager, null, Arrays.asList("-proc:none"), null, compilationUnits);

        boolean foundImport = false;
        boolean foundClass = false;
        boolean foundTestMethod = false;
        int topLevelClassCount = 0;

        Iterable<? extends CompilationUnitTree> trees = task.parse();
        for (CompilationUnitTree tree : trees) {
            for (ImportTree importTree : tree.getImports()) {
                String importStr = importTree.getQualifiedIdentifier().toString();
                if (importStr.equals("org.junit.jupiter.api.Test") || importStr.equals("org.junit.Test")) {
                    foundImport = true;
                }
            }

            for (var typeDecl : tree.getTypeDecls()) {
                if (typeDecl instanceof ClassTree) {
                    topLevelClassCount++;
                    ClassTree classTree = (ClassTree) typeDecl;
                    foundClass = true;
                    for (var member : classTree.getMembers()) {
                        if (member instanceof MethodTree) {
                            MethodTree method = (MethodTree) member;
                            boolean hasTestAnnotation = method.getModifiers().getAnnotations().stream()
                                    .anyMatch(a -> a.getAnnotationType().toString().endsWith("Test"));
                            if (hasTestAnnotation) {
                                foundTestMethod = true;
                            }
                        }
                    }
                }
            }
        }

        if (!foundClass) {
            System.out.println("FAIL:No se ha detectado ninguna clase Java en el archivo.");
            System.exit(1);
        }
        if (topLevelClassCount > 1) {
            System.out.println("FAIL:Se detectaron varias clases de nivel superior.");
            System.exit(1);
        }
        if (!foundImport) {
            System.out.println("FAIL:No se ha detectado la importación de JUnit 5 Test.");
            System.exit(1);
        }
        if (!foundTestMethod) {
            System.out.println("FAIL:No se ha detectado ningún método anotado con @Test.");
            System.exit(1);
        }

        System.out.println("PASS");
    }
}
"""


def _ensure_ast_validator(repo_path: Path) -> Path:
    helper_dir = repo_path / "validator" / ".langgraph_ast_validator"
    helper_dir.mkdir(parents=True, exist_ok=True)

    source_file = helper_dir / "LangGraphJavaAstValidator.java"
    class_file = helper_dir / "LangGraphJavaAstValidator.class"

    source = _ast_validator_java_source()
    if not source_file.exists() or source_file.read_text(encoding="utf-8") != source:
        source_file.write_text(source, encoding="utf-8")

    if not class_file.exists() or class_file.stat().st_mtime < source_file.stat().st_mtime:
        compile_result = subprocess.run(
            ["javac", str(source_file)],
            cwd=str(helper_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(
                "No se pudo compilar el validador AST Java: "
                + compile_result.stderr.strip()
            )

    return helper_dir


def _run_ast_validator(java_file: Path, repo_path: Path) -> tuple[bool, str]:
    helper_dir = _ensure_ast_validator(repo_path)

    result = subprocess.run(
        ["java", "-cp", str(helper_dir), "LangGraphJavaAstValidator", str(java_file)],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout.strip() or result.stderr.strip()
    if result.returncode == 0 and output.startswith("PASS"):
        return True, ""
    return False, output


def ast_parsing(state: TestAgentState) -> TestAgentState:
    response = state.get("llm_response", "") or ""
    state["ast_parsing_passed"] = False

    if not response.strip():
        record_validation_error(state, "ast_parsing", "No hay código para analizar.")
        return state

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(state["repo_path"])
        temp_file = Path(tmpdir) / "GeneratedTest.java"
        temp_file.write_text(response, encoding="utf-8")

        try:
            passed, message = _run_ast_validator(temp_file, repo_path)
        except Exception as exc:
            record_validation_error(state, "ast_parsing", f"Error al ejecutar el validador AST: {exc}")
            return state

    if not passed:
        record_validation_error(state, "ast_parsing", f"AST validation failed: {message}")
        return state

    state["ast_parsing_passed"] = True
    return state


def structural_validation(state: TestAgentState) -> TestAgentState:
    """Valida el formato generado y su estructura Java mediante AST."""
    state["validation_errors"] = []
    state["ast_parsing_passed"] = False
    clean_output(state)
    if state.get("validation_errors"):
        add_report(
            state,
            "STRUCTURAL_ERROR_REPORT",
            "clean output",
            validation_description(state, "The generated test could not be cleaned into a valid Java code region."),
        )
        return state

    ast_parsing(state)
    if state.get("validation_errors"):
        add_report(
            state,
            "STRUCTURAL_ERROR_REPORT",
            "ast parsing",
            validation_description(state, "The generated test failed structural AST validation."),
        )
    return state


def _get_maven_test_classpath(repo_path: Path) -> str:
    output_path = repo_path / "target" / "langgraph_test_classpath.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    is_windows = os.name == "nt"
    result = subprocess.run(
        [
            "mvn",
            "-q",
            "-DincludeScope=test",
            f"-Dmdep.outputFile={output_path}",
            "dependency:build-classpath",
        ],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        check=False,
        shell=is_windows,
    )

    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(
            "No se pudo obtener el classpath de Maven para la compilación: "
            + (result.stderr.strip() or result.stdout.strip())
        )

    return output_path.read_text(encoding="utf-8").strip()


def compiler(state: TestAgentState) -> TestAgentState:
    response = state.get("llm_response", "") or ""
    state["compiler_passed"] = False

    if not response.strip():
        record_validation_error(state, "compiler", "No hay código para compilar.")
        return state

    repo_path = Path(state["repo_path"])
    is_windows = os.name == "nt"

    try:
        subprocess.run(
            ["mvn", "-q", "-DskipTests=true", "compile"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
            shell=is_windows,
        )
    except subprocess.CalledProcessError as exc:
        record_validation_error(state, "compiler", "Error al compilar las clases del proyecto antes de validar el test: " + exc.stderr.strip())
        return state

    try:
        classpath = _get_maven_test_classpath(repo_path)
    except Exception as exc:
        record_validation_error(state, "compiler", str(exc))
        return state

    classpath_parts = [classpath]
    main_classes = repo_path / "target" / "classes"
    if main_classes.exists():
        classpath_parts.append(str(main_classes))
    full_classpath = os.pathsep.join(classpath_parts)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = Path(tmpdir) / "GeneratedTest.java"
        temp_file.write_text(response, encoding="utf-8")
        out_dir = Path(tmpdir) / "classes"
        out_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["javac", "-classpath", full_classpath, "-d", str(out_dir), str(temp_file)],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_output = result.stderr.strip() or result.stdout.strip()
            record_validation_error(state, "compiler", f"javac falló: {error_output}")
            return state

    state["compiler_passed"] = True
    return state


def compilation_validation(state: TestAgentState) -> TestAgentState:
    """Valida que el test generado compile con el proyecto y sus dependencias."""
    state["validation_errors"] = []
    compiler(state)
    if state.get("validation_errors"):
        add_report(
            state,
            "COMPILATION-ERROR_REPORT",
            "compiler",
            validation_description(
                state,
                "The generated test failed compilation. Review the compiler diagnostics and correct the test.",
            ),
        )
    return state


def improvement_validation(state: TestAgentState) -> TestAgentState:
    """Punto de extensión para branch covering y rule covering."""
    return state


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


def _ast_dependency_parser_source() -> str:
    return """import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.IdentifierTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.Trees;
import com.sun.source.util.TreeScanner;
import javax.lang.model.element.Element;
import javax.lang.model.element.ElementKind;
import javax.lang.model.element.QualifiedNameable;
import javax.tools.JavaCompiler;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import javax.tools.JavaFileObject;
import java.io.File;
import java.util.Arrays;

public class LangGraphJavaDependencyParser {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.exit(1);
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            System.exit(1);
        }

        StandardJavaFileManager fileManager = compiler.getStandardFileManager(null, null, null);
        Iterable<? extends JavaFileObject> files = fileManager.getJavaFileObjects(new File(args[0]));
        JavacTask task = (JavacTask) compiler.getTask(null, fileManager, null,
            Arrays.asList("-proc:none", "-sourcepath", args[1]), null, files);
        Iterable<? extends CompilationUnitTree> units = task.parse();
        task.analyze();
        Trees trees = Trees.instance(task);

        for (CompilationUnitTree tree : units) {
            new TreeScanner<Void, Void>() {
                @Override
                public Void visitIdentifier(IdentifierTree node, Void unused) {
                    Element element = trees.getElement(trees.getPath(tree, node));
                    if (element != null && (element.getKind() == ElementKind.CLASS
                            || element.getKind() == ElementKind.INTERFACE
                            || element.getKind() == ElementKind.ENUM
                            || element.getKind() == ElementKind.RECORD)) {
                        if (element instanceof QualifiedNameable qualified) {
                            System.out.println("TYPE:" + element.getKind() + ":" + qualified.getQualifiedName());
                        }
                    }
                    return super.visitIdentifier(node, unused);
                }
            }.scan(tree, null);
        }
    }
}
"""


def _get_ast_dependency_metadata(repo_path: Path, target_path: Path) -> set[str]:
    helper_dir = repo_path / "validator" / ".langgraph_dependency_parser"
    helper_dir.mkdir(parents=True, exist_ok=True)
    source_file = helper_dir / "LangGraphJavaDependencyParser.java"
    class_file = helper_dir / "LangGraphJavaDependencyParser.class"
    source = _ast_dependency_parser_source()

    if not source_file.exists() or source_file.read_text(encoding="utf-8") != source:
        source_file.write_text(source, encoding="utf-8")
    if not class_file.exists() or class_file.stat().st_mtime < source_file.stat().st_mtime:
        result = subprocess.run(
            ["javac", source_file.name], cwd=str(helper_dir), capture_output=True,
            text=True, check=False
        )
        if result.returncode != 0:
            raise RuntimeError("No se pudo compilar el parser AST de dependencias: " + result.stderr.strip())

    result = subprocess.run(
        [
            "java",
            "-cp",
            str(helper_dir),
            "LangGraphJavaDependencyParser",
            str(target_path),
            str(repo_path / "src" / "main"),
        ],
        cwd=str(repo_path), capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "El parser AST no pudo analizar el archivo.")

    type_names: set[str] = set()
    for line in result.stdout.splitlines():
        if line.startswith("TYPE:"):
            _, _, qualified_name = line.removeprefix("TYPE:").partition(":")
            if qualified_name:
                type_names.add(qualified_name.strip())
    return type_names


def get_dependencies(repo_path: str, file_name: str) -> list[str]:
    """Obtiene recursivamente mediante AST las clases del proyecto usadas por un archivo Java."""
    repo = Path(repo_path).resolve()
    target_path = repo / file_name
    source_root = repo / "src" / "main"
    if not target_path.exists() or target_path.suffix != ".java" or not source_root.exists():
        return []

    project_files = list(source_root.rglob("*.java"))
    by_qualified_name = {}
    for project_file in project_files:
        relative = project_file.relative_to(source_root).with_suffix("")
        qualified_name = ".".join(relative.parts)
        by_qualified_name[qualified_name] = project_file

    dependencies: set[str] = set()
    pending = [target_path]
    visited: set[Path] = set()

    while pending:
        current_path = pending.pop(0).resolve()
        if current_path in visited:
            continue
        visited.add(current_path)

        try:
            type_names = _get_ast_dependency_metadata(repo, current_path)
        except (OSError, RuntimeError):
            continue

        direct_dependencies: set[Path] = set()
        for qualified_name in type_names:
            project_file = by_qualified_name.get(qualified_name)
            if project_file is not None:
                direct_dependencies.add(project_file.resolve())

        for dependency_path in direct_dependencies:
            if dependency_path == current_path or dependency_path in visited:
                continue
            dependency_name = dependency_path.relative_to(repo).as_posix()
            dependencies.add(dependency_name)
            pending.append(dependency_path)

    return sorted(dependencies)


def get_context(state: TestAgentState) -> TestAgentState:

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

        # contenido
        content = read_file(file_path)

        # dependencias
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
    state["llm_call_failed"] = False
    state["file_skipped"] = False
    current_file_ind = int(state.get("current_file_ind", 0))
    modified_files_count = int(state.get("modified_files_count", 0))
    attempts = int(state.get("attempts", 0))

    if current_file_ind >= modified_files_count:
        state["file_skipped"] = True
        return state

    if attempts >= 10:
        advance_to_next_file(state)
        state["file_skipped"] = True
        return state

    state["attempts"] = attempts + 1
    prompt = state.get("context", "") or ""
    if not prompt.strip():
        state["llm_response"] = "No hay contexto disponible para enviar al modelo."
        state["llm_call_failed"] = True
        return state

    report = state.get("report_call_state", {})
    report_type = report.get("type")
    if report_type:
        guidance_by_type = {
            "STRUCTURAL_ERROR_REPORT": "Fix the Java output structure and AST issues described in the report.",
            "COMPILATION-ERROR_REPORT": "Fix the compilation errors described in the report while preserving the requested tests.",
            "IMPROVEMENT_REPORT": "Improve branch and rule coverage according to the report without breaking compilation.",
        }
        guidance = guidance_by_type.get(report_type, "Correct the generated test according to the report.")
        prompt = (
            f"{prompt}\n\nCorrection instructions:\n{guidance}"
            f"\nReport from the previous attempt:\n{json.dumps(report, ensure_ascii=True)}"
        )

    try:
        api_key = load_api_key()
    except Exception as exc:
        state["llm_response"] = f"Error al cargar la API key: {exc}"
        state["llm_call_failed"] = True
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
        state["llm_response"] = response_text

    except Exception as exc:
        state["llm_response"] = f"Error al llamar a LangChain: {exc}"
        state["llm_call_failed"] = True

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
    advance_to_next_file(state)
    
    return state


def write_report_call_states(state: TestAgentState) -> TestAgentState:
    """Guarda todos los reportes generados durante la ejecución."""
    report_path = Path(state.get("repo_path", ".")) / "report_call_states.json"
    report_path.write_text(
        json.dumps(state.get("report_call_states", []), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return state


def execute_test_files(state: TestAgentState) -> TestAgentState:
    """
    Ejecuta las pruebas unitarias del proyecto mediante Maven (mvn test).
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
    state["test_execution_output"] = f"Maven Execution Return Code: {result.returncode}\n\n{output}"
    return state


def should_continue(state: TestAgentState) -> str:
    """
    Determina si quedan más archivos modificados por procesar o 
    si se debe proceder a ejecutar los tests.
    """
    current_file_ind = int(state.get("current_file_ind", 0))
    modified_files_count = int(state.get("modified_files_count", 0))

    if current_file_ind >= modified_files_count:
        return "write_report_call_states"
    
    return "send_context"


def llm_call_decision(state: TestAgentState) -> str:
    if state.get("file_skipped"):
        if int(state.get("current_file_ind", 0)) >= int(state.get("modified_files_count", 0)):
            return "write_report_call_states"
        return "send_context"
    return "structural_validation"


def structural_validation_decision(state: TestAgentState) -> str:
    if state.get("ast_parsing_passed"):
        return "compilation_validation"
    return "llm_call"


def compilation_validation_decision(state: TestAgentState) -> str:
    if state.get("compiler_passed"):
        return "improvement_validation"
    return "llm_call"


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


def print_test_execution_output(result: dict) -> None:
    """Imprime la salida de la ejecución de Maven separada de la respuesta del modelo."""
    output = result.get("test_execution_output", "")
    print("\n=== Salida de las pruebas Maven ===")
    if output:
        print(output)
    else:
        print("No se ejecutaron las pruebas Maven.")


def print_validation_errors(result: dict) -> None:
    """Imprime los errores registrados durante la validación."""
    errors = result.get("validation_errors", [])
    print("\n=== Errores de validación ===")
    if not errors:
        print("No se registraron errores de validación.")
        return

    for error in errors:
        node_name = error.get("node", "<nodo desconocido>")
        message = error.get("message", "<mensaje vacío>")
        print(f"- [{node_name}] {message}")


workflow = StateGraph(TestAgentState)
workflow.add_node("get_context", get_context)
workflow.add_node("send_context", send_context)
workflow.add_node("llm_call", llm_call)
workflow.add_node("structural_validation", structural_validation)
workflow.add_node("compilation_validation", compilation_validation)
workflow.add_node("improvement_validation", improvement_validation)
workflow.add_node("write_test_file", write_test_file)
workflow.add_node("write_report_call_states", write_report_call_states)
workflow.add_node("execute_test_files", execute_test_files)

workflow.add_edge(START, "get_context")
workflow.add_edge("get_context", "send_context")
workflow.add_edge("send_context", "llm_call")
workflow.add_conditional_edges(
    "llm_call",
    llm_call_decision,
    {
        "structural_validation": "structural_validation",
        "send_context": "send_context",
        "write_report_call_states": "write_report_call_states",
    },
)
workflow.add_conditional_edges(
    "structural_validation",
    structural_validation_decision,
    {
        "compilation_validation": "compilation_validation",
        "llm_call": "llm_call",
    },
)
workflow.add_conditional_edges(
    "compilation_validation",
    compilation_validation_decision,
    {
        "improvement_validation": "improvement_validation",
        "llm_call": "llm_call",
    },
)
workflow.add_edge("improvement_validation", "write_test_file")

workflow.add_conditional_edges(
    "write_test_file",
    should_continue,
    {
        "send_context": "send_context",
        "write_report_call_states": "write_report_call_states",
    }
)

workflow.add_edge("write_report_call_states", "execute_test_files")
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
    print_test_execution_output(result)
    print_validation_errors(result)
