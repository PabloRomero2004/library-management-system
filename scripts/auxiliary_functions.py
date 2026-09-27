from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, TypedDict


class SourceFile(TypedDict):
    file_name: str
    file_content: str


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
        


def get_modified_source_files(repo_path: str) -> list[str]:
    """Obtiene archivos modificados bajo src/main entre HEAD~1 y HEAD."""
    output = git(
        repo_path,
        "diff",
        "--name-only",
        "HEAD~1",
        "HEAD",
        "--",
        "src/main",
    )
    return output.splitlines()


def get_source_file_diff(repo_path: str, file_name: str) -> str:
    """Obtiene el diff de un archivo entre HEAD~1 y HEAD."""
    return git(repo_path, "diff", "HEAD~1", "HEAD", "--", file_name)


def build_test_context(
    modified_file_name: str,
    modified_file_content: str,
    modified_file_changes: str,
    dependencies: list[SourceFile],
    test_file_name: str | None,
    test_file_content: str | None,
) -> str:
    """Construye el prompt de generación de tests a partir del contexto del archivo."""
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
    return "\n".join(context_lines)


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


def get_dependencies(repo_path: str, file_name: str) -> tuple[list[str], bool, str]:
    """Obtiene recursivamente mediante AST las clases del proyecto usadas por un archivo Java."""
    repo = Path(repo_path).resolve()
    target_path = repo / file_name
    source_root = repo / "src" / "main"
    error_occurred = False
    error_message = ""
    if not target_path.exists() or target_path.suffix != ".java" or not source_root.exists():
        return [], error_occurred, error_message

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
        except (Exception) as e:
            error_occurred = True
            error_message = f"Error al analizar dependencias para {current_path}: {str(e)}"
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

    return sorted(dependencies), error_occurred, error_message



def clean_java_output(response: str) -> tuple[str, str | None, str | None]:
    """Extrae la región Java de la respuesta y devuelve un posible error."""
    if not response.strip():
        return response, "cleaner", "El output está vacío."

    fenced_block = re.search(r"```[^\r\n]*\r?\n(.*?)\r?\n```", response, re.DOTALL)
    cleaned = fenced_block.group(1).strip() if fenced_block else response.strip()
    start_match = re.search(r"(?:package\b|import\b|public\s+class\b|class\b|@Test\b)", cleaned)
    end_index = cleaned.rfind("}")


    if not start_match or end_index == -1 or end_index < start_match.start():
        return "", "cleaner", "La región de código está vacía después de la partición."

    code_region = cleaned[start_match.start() : end_index + 1].strip()
    if not code_region:
        return "", "cleaner", "No se ha encontrado una región de código válida."
    else:
        return code_region, "", ""


def _ast_validator_java_source() -> str:
    return """import com.sun.source.tree.AssertTree;
import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ImportTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.tree.MethodInvocationTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.TreePathScanner;
import com.sun.source.util.TreeScanner;
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
        JavacTask task = (JavacTask) compiler.getTask(null, fileManager, null,
                Arrays.asList("-proc:none"), null, compilationUnits);

        TestValidatorScanner scanner = new TestValidatorScanner();
        for (CompilationUnitTree tree : task.parse()) {
            scanner.scan(tree, null);
        }

        if (scanner.topLevelClassCount == 0) {
            System.out.println("FAIL:No se ha detectado ninguna clase Java en el archivo.");
            System.exit(1);
        }
        if (scanner.topLevelClassCount > 1) {
            System.out.println("FAIL:Se detectaron varias clases de nivel superior.");
            System.exit(1);
        }
        if (!scanner.foundJUnitImport) {
            System.out.println("FAIL:No se ha detectado la importación de JUnit (org.junit.Test, org.junit.jupiter.api.Test u org.junit.jupiter.api.*).");
            System.exit(1);
        }
        if (scanner.testMethodCount == 0) {
            System.out.println("FAIL:No se ha detectado ningún método anotado con @Test.");
            System.exit(1);
        }
        if (scanner.testMethodsWithoutAssert > 0) {
            System.out.println("FAIL:Se detectó al menos un método @Test sin ningún assert ni verificación (Assertions, assertThat, verify, etc.).");
            System.exit(1);
        }

        System.out.println("PASS");
    }

    private static class TestValidatorScanner extends TreePathScanner<Void, Void> {
        boolean foundJUnitImport = false;
        int topLevelClassCount = 0;
        int testMethodCount = 0;
        int testMethodsWithoutAssert = 0;

        @Override
        public Void visitImport(ImportTree node, Void p) {
            String importStr = node.getQualifiedIdentifier().toString();
            if (importStr.equals("org.junit.jupiter.api.Test")
                    || importStr.equals("org.junit.Test")
                    || importStr.startsWith("org.junit.jupiter.api.")
                    || importStr.startsWith("org.junit.framework.")) {
                foundJUnitImport = true;
            }
            return super.visitImport(node, p);
        }

        @Override
        public Void visitClass(ClassTree node, Void p) {
            if (getCurrentPath().getParentPath().getLeaf() instanceof CompilationUnitTree) {
                topLevelClassCount++;
            }
            return super.visitClass(node, p);
        }

        @Override
        public Void visitMethod(MethodTree node, Void p) {
            boolean isTestMethod = node.getModifiers().getAnnotations().stream()
                    .anyMatch(a -> {
                        String name = a.getAnnotationType().toString();
                        return name.equals("Test") || name.endsWith(".Test");
                    });

            if (isTestMethod) {
                testMethodCount++;
                AssertVisitor assertVisitor = new AssertVisitor();
                assertVisitor.scan(node.getBody(), null);
                if (!assertVisitor.hasAssert) {
                    testMethodsWithoutAssert++;
                }
            }
            return super.visitMethod(node, p);
        }
    }

    private static class AssertVisitor extends TreeScanner<Void, Void> {
        boolean hasAssert = false;

        @Override
        public Void visitAssert(AssertTree node, Void p) {
            hasAssert = true;
            return super.visitAssert(node, p);
        }

        @Override
        public Void visitMethodInvocation(MethodInvocationTree node, Void p) {
            String expr = node.getMethodSelect().toString();
            if (expr.contains("assert") || expr.contains("Assert")
                    || expr.startsWith("assertThat") || expr.contains("verify")
                    || expr.contains("fail")) {
                hasAssert = true;
            }
            return super.visitMethodInvocation(node, p);
        }
    }
}
"""


def _ensure_ast_validator(repo_path: Path) -> Path:
    helper_dir = repo_path.resolve() / "validator" / ".langgraph_ast_validator"
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


def validate_generated_test(response: str, repo_path: Path) -> tuple[bool, str, str, bool]:
    if not response.strip():
        return False, "AST validator", "No hay código para analizar.", False

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = Path(tmpdir) / "GeneratedTest.java"
        temp_file.write_text(response, encoding="utf-8")

        try:
            passed, message = _run_ast_validator(temp_file, repo_path)
        except Exception as exc:
            return False, "AST validator", f"Error al ejecutar el validador AST: {exc}", True

    if not passed:
        return False, "AST validator", f"AST validation failed: {message}", False
    return True, "AST validator", "", False


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


def compile_generated_test(response: str, repo_path: Path) -> tuple[bool, str, str, bool]:
    if not response.strip():
        return False, "compiler", "No hay código para compilar.", False

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
    except Exception as exc:
        return False, "compiler", str(exc), True

    try:
        classpath = _get_maven_test_classpath(repo_path)
    except Exception as exc:
        return False, "compiler", str(exc), True

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
            return False, "compiler", f"javac falló: {error_output}", False

    return True, "compiler", "", False



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


def write_test_content(
    repo_path: str,
    modified_file: dict[str, Any],
    generated_content: str,
) -> Path:
    """Escribe el contenido generado y devuelve la ruta del archivo de test."""
    test_file_name = modified_file.get("test_file_name")
    test_file_content = modified_file.get("test_file_content")

    if test_file_name and str(test_file_name).strip() and test_file_content is not None:
        target_path = Path(repo_path) / test_file_name
    else:
        target_path = build_test_file_path(repo_path, modified_file.get("modified_file_name", ""))

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(generated_content, encoding="utf-8")
    return target_path


def write_run_reports(
    repo_path: str,
    report_call_states: list[dict[str, Any]],
    modified_files: list[dict[str, Any]],
) -> None:
    """Guarda en JSON los reportes y archivos modificados de una ejecución."""
    repo = Path(repo_path)
    (repo / "report_call_states.json").write_text(
        json.dumps(report_call_states, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (repo / "modified_files.json").write_text(
        json.dumps(modified_files, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def run_maven_tests(repo_path: str) -> str:
    """Ejecuta Maven y devuelve la salida consolidada de la ejecución."""
    print("\n=== Ejecutando pruebas unitarias con Maven ===")
    is_windows = os.name == "nt"
    result = subprocess.run(
        ["mvn", "test"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
        shell=is_windows,
    )
    output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    return f"Maven Execution Return Code: {result.returncode}\n\n{output}"
