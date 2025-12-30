"""
Nagini AST Parser

This module is the first phase of the Nagini compiler pipeline. It leverages Python's
built-in AST (Abstract Syntax Tree) parser to parse Nagini source code, which uses
Python-compatible syntax. The parser extracts:
- Class definitions with their @property decorators
- Field information with type annotations
- Method definitions
- Function definitions
- Top-level statements

The output is a collection of structured metadata (ClassInfo, FunctionInfo) that
will be used by the IR generator in the next phase.

Key Design Decision: We reuse Python's AST parser instead of building a custom
parser, allowing rapid development and leveraging Python's robust parsing capabilities.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, field


@dataclass
class FieldInfo:
    """
    Information about a class field.
    
    Stores metadata for each field in a class, including its name, type,
    memory offset (for layout calculation), and size in bytes.
    """
    name: str
    type_name: str
    offset: int = 0  # Byte offset in the struct (calculated during layout phase)
    size: int = 0    # Size in bytes (determined by type, e.g., int=8, float=8)


@dataclass
class FunctionInfo:
    """
    Information about a function or method definition.
    
    Stores complete metadata about a function including its signature, parameters,
    return type, and body. Supports advanced features like *args/**kwargs and
    distinguishes between strict (type-annotated) and loose (untyped) parameters.
    """
    name: str
    params: List[tuple]  # List of (name, type_annotation) tuples for each parameter
    return_type: Optional[str]  # Return type annotation, None if not specified
    body: List[ast.stmt]  # AST statements representing the function body
    is_lambda: bool = False  # True if this is a lambda expression
    has_varargs: bool = False  # True if function accepts *args
    varargs_name: Optional[str] = None  # Name of the *args parameter
    has_kwargs: bool = False  # True if function accepts **kwargs
    kwargs_name: Optional[str] = None  # Name of the **kwargs parameter
    strict_params: List[str] = field(default_factory=list)  # Parameters with type annotations (enables runtime checking)
    line_no: int = 0  # Line number in source code (for debugging and error messages)
    is_static: bool = False  # Whether this is a static method (no self parameter)
    name_id: Optional[int] = None  # Unique identifier for the function name (set during IR generation)
    func_id: Optional[int] = None  # Unique identifier for the function (set during IR generation)
    full_name: Optional[str] = None  # Full name including class prefix (set during IR generation)

@dataclass
class ClassInfo:
    """
    Complete metadata about a Nagini class.
    
    Stores everything needed to generate code for a class, including:
    - Fields with their types and memory layout
    - Methods (including __init__ and other methods)
    - Memory allocation strategy (how instances are created)
    - Memory layout strategy (how fields are arranged in memory)
    - Paradigm (whether it's an object with hash table or plain data struct)
    """
    name: str
    fields: List[FieldInfo]  # List of field definitions
    methods: List[FunctionInfo]  # Class methods (including __init__)
    malloc_strategy: str = 'gc'   # Memory allocation: 'gc' (default, auto), 'pool' (fixed), or 'heap' (manual)
    layout: str = 'cpp'           # Memory layout: 'cpp' (C++ compatible), 'std430' (GPU shader), or 'custom'
    paradigm: str = 'object'      # 'object' = hash table with metadata, 'data' = plain struct (no overhead)
    parent: Optional[str] = 'Object'  # Parent class name (all classes inherit from Object by default)
    name_id: Optional[int] = None  # Unique identifier for the class name (set during IR generation)
    
    
class NaginiParser:
    """
    Main parser class for Nagini source code.
    
    Uses Python's built-in ast.parse() to create an Abstract Syntax Tree,
    then walks the tree to extract Nagini-specific constructs:
    - Classes with @property decorators
    - Functions with type annotations
    - Top-level statements
    
    The parser doesn't validate semantics or types - it just extracts
    structural information. Semantic analysis happens in later phases.
    """
    
    # Type size mapping for memory layout calculation
    # These sizes are used to calculate field offsets in structs
    TYPE_SIZES = {
        'int': 8,      # 64-bit integer (int64_t in C)
        'float': 8,    # 64-bit float (double in C)
        'bool': 1,     # 1 byte (uint8_t in C)
        'str': 8,      # Pointer size (char* in C)
    }
    
    def __init__(self, source_file: Optional[str] = None):
        """
        Initialize the Nagini parser.
        
        Args:
            source_file: Optional path to the source file being parsed. 
                        Used for resolving import statements relative to the source file location.
        """
        self.classes: Dict[str, ClassInfo] = {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.top_level_stmts: List[ast.stmt] = []
        self.source_file = source_file
        self.imported_files: Set[str] = set()  # Track imported files to avoid circular imports
        self.module_aliases: Dict[str, Dict[str, str]] = {}  # Track module aliases: {alias_name: {module_name: module_path, functions: {func_name: ...}}}
        
    def parse(self, source_code: str) -> tuple[Dict[str, ClassInfo], Dict[str, FunctionInfo], List[ast.stmt]]:
        """
        Main entry point: Parse Nagini source code.
        
        Takes raw source code and produces structured metadata about the program.
        This is Phase 1 of the compilation pipeline.
        
        Process:
        1. Use Python's ast.parse() to create an AST
        2. Walk top-level nodes (classes, functions, statements)
        3. For each class: extract fields, methods, and @property decorators
        4. For each function: extract parameters, return type, and body
        5. Collect other statements for main function generation
        
        Args:
            source_code: Nagini source code as a string
            
        Returns:
            Tuple of (classes dict, functions dict, top-level statements list)
        """
        # Parse the source code into an AST using Python's parser
        tree = ast.parse(source_code)
        
        # Walk only top-level nodes (we don't use ast.walk to avoid nested functions)
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Handle import statements
                self._handle_import(node)
            elif isinstance(node, ast.ClassDef):
                # Extract class definition
                class_info = self._parse_class(node)
                self.classes[class_info.name] = class_info
            elif isinstance(node, ast.FunctionDef):
                # Extract function definition
                func_info = self._parse_function(node)
                self.functions[func_info.name] = func_info
            else:
                # Collect other top-level statements (assignments, expressions, etc.)
                # These will be used to generate the main() function
                self.top_level_stmts.append(node)

        # Post-process: Transform module alias attribute accesses
        if self.module_aliases:
            self.top_level_stmts = [self._transform_module_aliases(stmt) for stmt in self.top_level_stmts]

        return self.classes, self.functions, self.top_level_stmts
    
    def _transform_module_aliases(self, node):
        """
        Transform AST nodes to replace module alias attribute accesses.
        For example, `o.get_os_name()` becomes `get_os_name()` where `o` is an alias for module `os`.
        """
        class ModuleAliasTransformer(ast.NodeTransformer):
            def __init__(self, module_aliases):
                self.module_aliases = module_aliases
            
            def visit_Attribute(self, node):
                # Check if this is accessing an attribute on a module alias
                if isinstance(node.value, ast.Name) and node.value.id in self.module_aliases:
                    # This is module_alias.attribute_name
                    # We don't transform it here, it will be handled in visit_Call
                    pass
                return self.generic_visit(node)
            
            def visit_Call(self, node):
                # Check if we're calling a function via module alias (e.g., o.get_os_name())
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id in self.module_aliases:
                        alias_name = node.func.value.id
                        func_name = node.func.attr
                        module_info = self.module_aliases[alias_name]
                        
                        # Check if this function exists in the module
                        if func_name in module_info['functions']:
                            # Transform o.get_os_name() to get_os_name()
                            new_func_name = ast.Name(id=func_name, ctx=ast.Load())
                            ast.copy_location(new_func_name, node.func)
                            new_node = ast.Call(
                                func=new_func_name,
                                args=node.args,
                                keywords=node.keywords
                            )
                            new_node = ast.copy_location(new_node, node)
                            ast.fix_missing_locations(new_node)
                            return new_node
                
                return self.generic_visit(node)
        
        transformer = ModuleAliasTransformer(self.module_aliases)
        transformed = transformer.visit(node)
        # Ensure all nodes have location information
        ast.fix_missing_locations(transformed)
        return transformed
    
    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """
        Extract complete information from a class definition.
        
        Parses:
        - @property decorator with malloc_strategy, layout, and paradigm options
        - Parent class (base class in inheritance)
        - Fields with type annotations (e.g., x: int)
        - Methods including __init__ and other methods
        - Memory layout (calculates field offsets based on paradigm)
        
        Returns:
            ClassInfo object with all extracted metadata
        """
        # Extract properties from @property decorator
        # These control memory management and layout
        malloc_strategy = 'gc'  # Default: automatic garbage collection
        layout = 'cpp'          # Default: C++ compatible layout
        paradigm = 'object'     # Default: object paradigm with hash table
        
        # Look for @property decorator on the class
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'property':
                    props = self._extract_decorator_props(decorator)
                    malloc_strategy = props.get('malloc_strategy', malloc_strategy)
                    layout = props.get('layout', layout)
                    paradigm = props.get('paradigm', paradigm)
        
        # Extract parent class (inheritance)
        # In Nagini, all classes inherit from Object by default
        parent = 'Object'
        if node.bases:
            # Get the first base class name
            if isinstance(node.bases[0], ast.Name):
                parent = node.bases[0].id
        
        # Extract fields and methods from class body
        fields = []
        methods = []
        offset = 0  # Track byte offset for field layout
        
        # If using object paradigm, reserve space for object header
        # The object header contains metadata inherited from the base Object class
        if paradigm == 'object':
            # Object header: 8 bytes for reference counter (__refcount__)
            # This is inherited from the Object class and managed by the runtime
            offset = 8
        
        # Walk through class body to extract fields and methods
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # This is a field definition with type annotation (e.g., x: int)
                field_name = item.target.id
                type_name = self._extract_type_name(item.annotation)
                
                # Validate native paradigm classes require strict type annotations
                if paradigm == 'native' and type_name == 'unknown':
                    raise SyntaxError(
                        f"Native paradigm class '{node.name}' requires strict type annotation for field '{field_name}'. "
                        f"Please specify a type (e.g., {field_name}: float)"
                    )
                
                size = self.TYPE_SIZES.get(type_name, 8)  # Get size in bytes
                
                # Create field info with calculated offset
                field = FieldInfo(
                    name=field_name,
                    type_name=type_name,
                    offset=offset,  # Current offset in the struct
                    size=size       # Size in bytes
                )
                fields.append(field)
                offset += size  # Move offset forward for next field
            elif isinstance(item, ast.FunctionDef):
                # This is a method definition (including __init__)
                method_info = self._parse_function(item)
                methods.append(method_info)
        
        return ClassInfo(
            name=node.name,
            fields=fields,
            methods=methods,
            malloc_strategy=malloc_strategy,
            layout=layout,
            paradigm=paradigm,
            parent=parent
        )
    
    def _extract_decorator_props(self, decorator: ast.Call) -> Dict[str, str]:
        """
        Extract keyword arguments from @property decorator.
        
        Example decorator:
            @property(malloc_strategy='pool', layout='cpp', paradigm='object')
        
        Returns:
            Dictionary with decorator properties, e.g.:
            {'malloc_strategy': 'pool', 'layout': 'cpp', 'paradigm': 'object'}
        """
        props = {}
        
        # Extract each keyword argument from the decorator
        for keyword in decorator.keywords:
            if isinstance(keyword.value, ast.Constant):
                props[keyword.arg] = keyword.value.value
                
        return props
    
    def _extract_type_name(self, annotation) -> str:
        """
        Extract type name from a type annotation node.
        
        Handles different AST node types that can represent type annotations:
        - ast.Name: Simple type like 'int', 'str', 'MyClass'
        - ast.Constant: String literal type annotation
        
        Args:
            annotation: AST node representing a type annotation
            
        Returns:
            Type name as a string (e.g., 'int', 'float', 'str')
        """
        if isinstance(annotation, ast.Name):
            # Simple type name (e.g., int, float, MyClass)
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            # String literal type annotation
            return str(annotation.value)
        return 'unknown'
    
    def _parse_function(self, node: ast.FunctionDef) -> FunctionInfo:
        """
        Extract complete information from a function or method definition.
        
        Parses:
        - Function name
        - Parameters with type annotations (strict typing)
        - Return type annotation
        - *args and **kwargs support
        - Function body as AST nodes
        - Decorators (e.g., @staticmethod)
        
        This method handles both standalone functions and class methods.
        
        Returns:
            FunctionInfo object with all extracted metadata
        """
        # Extract parameters with type annotations
        params = []
        strict_params = []  # Track which parameters have type annotations (strict typing)
        
        for arg in node.args.args:
            param_name = arg.arg
            param_type = None
            if arg.annotation:
                # This parameter has a type annotation (e.g., x: int)
                param_type = self._extract_type_name(arg.annotation)
                strict_params.append(param_name)  # Mark as strictly typed
            params.append((param_name, param_type))
        
        # Check for *args (variable positional arguments)
        # Example: def func(*args)
        has_varargs = node.args.vararg is not None
        varargs_name = None
        if has_varargs and hasattr(node.args.vararg, 'arg'):
            varargs_name = node.args.vararg.arg
        
        # Check for **kwargs (variable keyword arguments)
        # Example: def func(**kwargs)
        has_kwargs = node.args.kwarg is not None
        kwargs_name = None
        if has_kwargs and hasattr(node.args.kwarg, 'arg'):
            kwargs_name = node.args.kwarg.arg
        
        # Extract return type annotation
        # Example: def func() -> int:
        return_type = None
        if node.returns:
            return_type = self._extract_type_name(node.returns)
        
        # Store the function body as AST statements
        # These will be converted to IR in the next phase
        return FunctionInfo(
            name=node.name,
            params=params,
            return_type=return_type,
            body=node.body,
            is_lambda=False,
            has_varargs=has_varargs,
            varargs_name=varargs_name,
            has_kwargs=has_kwargs,
            kwargs_name=kwargs_name,
            strict_params=strict_params,
            line_no=node.lineno,
            # Check if function has @staticmethod decorator
            is_static=any(isinstance(deco, ast.Name) and deco.id == 'staticmethod' for deco in node.decorator_list)
        )
    
    def _handle_import(self, node: Union[ast.Import, ast.ImportFrom]):
        """
        Handle import and from...import statements.
        
        Resolves the module file path and parses it to import classes and functions.
        Search order:
        1. Local directory (same as source file) - looks for .nag files
        2. compiler/ng directory - looks for .ng files
        
        Args:
            node: ast.Import or ast.ImportFrom node
            
        Note:
            This method handles file I/O and parsing errors gracefully by issuing warnings
            rather than raising exceptions. Missing modules or parse errors will not halt
            compilation, which allows for importing Python built-ins or external modules
            that don't require Nagini compilation.
        """
        if isinstance(node, ast.Import):
            # Handle: import module_name [as alias]
            for alias in node.names:
                module_name = alias.name
                alias_name = alias.asname if alias.asname else None
                
                # Import the module contents  
                imported_functions = self._import_module(module_name)
                
                # If an alias is used (e.g., import os as o), track it
                if alias_name and imported_functions is not None:
                    # Store module alias mapping
                    self.module_aliases[alias_name] = {
                        'module_name': module_name,
                        'functions': imported_functions
                    }
                    # Create an assignment: alias = "<module_name>"
                    # This allows the alias to be referenced in code (e.g., print(o))
                    assign_node = ast.Assign(
                        targets=[ast.Name(id=alias_name, ctx=ast.Store())],
                        value=ast.Constant(value=f"<module '{module_name}'>")
                    )
                    # Copy location information from the import statement
                    ast.copy_location(assign_node, node)
                    assign_node.targets[0].lineno = node.lineno
                    assign_node.targets[0].col_offset = node.col_offset
                    assign_node.value.lineno = node.lineno
                    assign_node.value.col_offset = node.col_offset
                    self.top_level_stmts.append(assign_node)
        elif isinstance(node, ast.ImportFrom):
            # Handle: from module_name import name1, name2
            module_name = node.module
            if module_name:
                self._import_module(module_name, from_names=[alias.name for alias in node.names])
    
    def _import_module(self, module_name: str, from_names: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Import a module by resolving its file path and parsing it.
        
        Args:
            module_name: Name of the module to import (e.g., 'vec3', 'builtin')
            from_names: Optional list of specific names to import (for 'from X import Y' syntax)
            
        Returns:
            Dictionary of imported functions if successful, None otherwise
        """
        # Resolve the module file path
        module_path = self._resolve_module_path(module_name)
        
        if not module_path:
            # Module not found - this is not an error for now, as it might be a Python built-in
            # or external module that doesn't need Nagini compilation
            return None
        
        # Check if already imported to avoid circular imports
        if module_path in self.imported_files:
            # Already imported - return the functions we already have
            return {name: func for name, func in self.functions.items()}
        
        # Mark as imported
        self.imported_files.add(module_path)
        
        # Read and parse the imported file
        try:
            with open(module_path, 'r') as f:
                imported_source = f.read()
        except (FileNotFoundError, PermissionError, IOError) as e:
            print(f"Warning: Could not read import file '{module_path}': {e}")
            return None
        
        # Create a new parser for the imported file
        imported_parser = NaginiParser(source_file=str(module_path))
        imported_parser.imported_files = self.imported_files  # Share the imported files set
        
        try:
            imported_classes, imported_functions, _ = imported_parser.parse(imported_source)
            
            # Merge imported classes and functions into current parser
            # If from_names is specified, only import those specific names
            if from_names:
                # Import only specified names
                for name in from_names:
                    if name in imported_classes:
                        self.classes[name] = imported_classes[name]
                    elif name in imported_functions:
                        self.functions[name] = imported_functions[name]
                    else:
                        # Warn if the requested name is not found
                        print(f"Warning: Name '{name}' not found in module '{module_path}'")
                return None  # Don't return functions for "from" imports
            else:
                # Import all classes and functions from the module
                self.classes.update(imported_classes)
                self.functions.update(imported_functions)
                return imported_functions  # Return the imported functions for alias tracking
        except (SyntaxError, ValueError) as e:
            print(f"Warning: Could not parse import file '{module_path}': {e}")
            return None
    
    def _resolve_module_path(self, module_name: str) -> Optional[str]:
        """
        Resolve a module name to a file path.
        
        Search order:
        1. Look for {module_name}.nag in the same directory as source file
        2. Look for {module_name}.ng in compiler/ng directory
        
        Args:
            module_name: Name of the module (e.g., 'vec3', 'builtin')
            
        Returns:
            Absolute path to the module file, or None if not found
        """
        # Determine the source directory
        if self.source_file:
            source_dir = Path(self.source_file).parent.absolute()
        else:
            source_dir = Path.cwd()
        
        # First, search locally for .nag files
        local_path = source_dir / f"{module_name}.nag"
        if local_path.exists() and local_path.is_file():
            return str(local_path.absolute())
        
        # Second, search in compiler/ng directory for .ng files
        # Get the compiler package directory
        compiler_dir = Path(__file__).parent
        ng_dir = compiler_dir / 'ng'
        ng_path = ng_dir / f"{module_name}.ng"
        
        if ng_path.exists() and ng_path.is_file():
            return str(ng_path.absolute())
        
        # Module not found
        return None
