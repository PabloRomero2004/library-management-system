import com.sun.source.tree.CompilationUnitTree;
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
