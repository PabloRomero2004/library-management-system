import com.sun.source.tree.ClassTree;
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
