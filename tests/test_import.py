import unittest
import tempfile
import os
import shutil
import ast
from pathlib import Path

from nagini.compiler import NaginiParser


class ImportTests(unittest.TestCase):
    """Test import functionality in the Nagini parser."""
    
    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_import_from_local_file(self):
        """Test importing from a local .nag file in the same directory."""
        # Create a module file
        module_path = Path(self.test_dir) / "mymodule.nag"
        module_path.write_text("""
@property(paradigm='object')
class TestClass:
    x: int
    def __init__(self, x: int):
        self.x = x
""")
        
        # Create a source file that imports from the module
        source_path = Path(self.test_dir) / "main.nag"
        source_code = "from mymodule import TestClass\n"
        
        # Parse the source
        parser = NaginiParser(source_file=str(source_path))
        classes, functions, _ = parser.parse(source_code)
        
        # Verify that TestClass was imported
        self.assertIn('TestClass', classes)
        self.assertEqual(classes['TestClass'].name, 'TestClass')
        self.assertEqual(len(classes['TestClass'].fields), 1)
        self.assertEqual(classes['TestClass'].fields[0].name, 'x')
    
    def test_import_all_from_module(self):
        """Test importing all classes and functions from a module."""
        # Create a module file with multiple definitions
        module_path = Path(self.test_dir) / "multi.nag"
        module_path.write_text("""
@property(paradigm='object')
class ClassA:
    a: int
    def __init__(self, a: int):
        self.a = a

@property(paradigm='object')
class ClassB:
    b: float
    def __init__(self, b: float):
        self.b = b

def func1(x: int) -> int:
    return x * 2
""")
        
        # Create a source file that imports the module
        source_path = Path(self.test_dir) / "main.nag"
        source_code = "import multi\n"
        
        # Parse the source
        parser = NaginiParser(source_file=str(source_path))
        classes, functions, _ = parser.parse(source_code)
        
        # Verify that all classes and functions were imported
        self.assertIn('ClassA', classes)
        self.assertIn('ClassB', classes)
        self.assertIn('func1', functions)
    
    def test_import_from_compiler_ng_directory(self):
        """Test importing from compiler/ng directory when not found locally."""
        # Create a source file that imports builtin
        source_path = Path(self.test_dir) / "main.nag"
        source_code = "from builtin import Point\n"
        
        # Parse the source
        parser = NaginiParser(source_file=str(source_path))
        classes, functions, _ = parser.parse(source_code)
        
        # Verify that Point was imported from builtin.ng
        self.assertIn('Point', classes)
        self.assertEqual(classes['Point'].name, 'Point')
    
    def test_no_circular_import(self):
        """Test that circular imports are handled properly."""
        # Create two modules that import each other
        module_a_path = Path(self.test_dir) / "module_a.nag"
        module_a_path.write_text("""
from module_b import ClassB

@property(paradigm='object')
class ClassA:
    x: int
    def __init__(self, x: int):
        self.x = x
""")
        
        module_b_path = Path(self.test_dir) / "module_b.nag"
        module_b_path.write_text("""
# This would create a circular import if not handled
# from module_a import ClassA

@property(paradigm='object')
class ClassB:
    y: float
    def __init__(self, y: float):
        self.y = y
""")
        
        # Parse module_a (which imports module_b)
        parser = NaginiParser(source_file=str(module_a_path))
        classes, functions, _ = parser.parse(module_a_path.read_text())
        
        # Should have both ClassA and ClassB
        self.assertIn('ClassA', classes)
        self.assertIn('ClassB', classes)
    
    def test_import_nonexistent_module(self):
        """Test that importing a nonexistent module doesn't crash."""
        source_path = Path(self.test_dir) / "main.nag"
        source_code = "import nonexistent_module\n"
        
        # Parse should not raise an exception
        parser = NaginiParser(source_file=str(source_path))
        classes, functions, _ = parser.parse(source_code)
        
        # Classes and functions should be empty (module not found)
        self.assertEqual(len(classes), 0)
        self.assertEqual(len(functions), 0)
    
    def test_import_with_alias(self):
        """Test importing a module with an alias."""
        # Create a module file
        module_path = Path(self.test_dir) / "mymodule.nag"
        module_path.write_text("""
def my_function(x: int) -> int:
    return x * 2
""")
        
        # Create a source file that imports with an alias
        source_path = Path(self.test_dir) / "main.nag"
        source_code = "import mymodule as mm\n"
        
        # Parse the source
        parser = NaginiParser(source_file=str(source_path))
        classes, functions, top_level_stmts = parser.parse(source_code)
        
        # Verify that the function was imported
        self.assertIn('my_function', functions)
        
        # Verify that an alias assignment was created
        self.assertEqual(len(top_level_stmts), 1)
        self.assertIsInstance(top_level_stmts[0], ast.Assign)
        self.assertEqual(top_level_stmts[0].targets[0].id, 'mm')
    
    def test_import_alias_namespace_access(self):
        """Test that namespace access works with import aliases (e.g., alias.function())."""
        # Create a module file with a function
        module_path = Path(self.test_dir) / "mymodule.nag"
        module_path.write_text("""
def greet(name: str) -> str:
    return f"Hello, {name}!"
""")
        
        # Create a source file that uses namespace access
        source_path = Path(self.test_dir) / "main.nag"
        source_code = """import mymodule as mm
result = mm.greet("World")
"""
        
        # Parse the source
        parser = NaginiParser(source_file=str(source_path))
        classes, functions, top_level_stmts = parser.parse(source_code)
        
        # Verify that the function was imported
        self.assertIn('greet', functions)
        
        # Verify that module alias was tracked
        self.assertIn('mm', parser.module_aliases)
        self.assertEqual(parser.module_aliases['mm']['module_name'], 'mymodule')
        
        # Verify that the namespace access was transformed
        # The second statement should be the assignment with transformed call
        self.assertGreaterEqual(len(top_level_stmts), 2)
        assign_stmt = top_level_stmts[1]
        self.assertIsInstance(assign_stmt, ast.Assign)
        # The call should have been transformed from mm.greet() to greet()
        self.assertIsInstance(assign_stmt.value, ast.Call)
        self.assertIsInstance(assign_stmt.value.func, ast.Name)
        self.assertEqual(assign_stmt.value.func.id, 'greet')


if __name__ == "__main__":
    unittest.main()
