import com.sun.source.tree.AssertTree;
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
