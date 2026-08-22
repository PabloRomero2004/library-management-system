import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.IdentifierTree;
import com.sun.source.tree.ImportTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.TreeScanner;
import javax.tools.JavaCompiler;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import javax.tools.JavaFileObject;
import java.io.File;
import java.util.Arrays;

public class LangGraphJavaDependencyParser {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.exit(1);
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            System.exit(1);
        }

        StandardJavaFileManager fileManager = compiler.getStandardFileManager(null, null, null);
        Iterable<? extends JavaFileObject> files = fileManager.getJavaFileObjects(new File(args[0]));
        JavacTask task = (JavacTask) compiler.getTask(null, fileManager, null,
                Arrays.asList("-proc:none"), null, files);

        for (CompilationUnitTree tree : task.parse()) {
            if (tree.getPackageName() != null) {
                System.out.println("PACKAGE:" + tree.getPackageName());
            }
            for (ImportTree importTree : tree.getImports()) {
                System.out.println("IMPORT:" + importTree.getQualifiedIdentifier());
            }
            new TreeScanner<Void, Void>() {
                @Override
                public Void visitIdentifier(IdentifierTree node, Void unused) {
                    System.out.println("TYPE:" + node.getName());
                    return super.visitIdentifier(node, unused);
                }
            }.scan(tree, null);
        }
    }
}
