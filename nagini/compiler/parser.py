"""
Nagini AST Parser
Parses Nagini source code using Python's built-in AST parser and extracts
class properties, field information, and allocation strategies.
"""

import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FieldInfo:
    """Information about a class field"""
    name: str
    type_name: str
    offset: int = 0  # Will be calculated during layout
    size: int = 0    # Will be calculated based on type


@dataclass
class FunctionInfo:
    """Information about a function definition"""
    name: str
    params: List[tuple]  # (name, type_annotation)
    return_type: Optional[str]
    body: List[ast.stmt]  # AST statements
    is_lambda: bool = False
    has_varargs: bool = False  # *args
    varargs_name: Optional[str] = None
    has_kwargs: bool = False  # **kwargs
    kwargs_name: Optional[str] = None
    strict_params: List[str] = field(default_factory=list)  # Parameters with type annotations (strict typing)
    line_no: int = 0  # Line number in source code
    is_static: bool = False  # Whether the function is static (for methods)


@dataclass
class ClassInfo:
    """Information about a Nagini class"""
    name: str
    fields: List[FieldInfo]
    methods: List[FunctionInfo]  # Class methods
    malloc_strategy: str = 'gc'   # gc (default), pool, heap
    layout: str = 'cpp'           # cpp, std430, custom
    paradigm: str = 'object'      # object, data
    parent: Optional[str] = 'Object'  # All classes inherit from Object by default
    name_id: Optional[int] = None  # Unique identifier for the class name
    
    
class NaginiParser:
    """
    Parses Nagini source code and extracts class definitions with their
    properties and field information.
    """
    
    # Type size mapping for layout calculation
    TYPE_SIZES = {
        'int': 8,      # 64-bit integer
        'float': 8,    # 64-bit float
        'bool': 1,     # 1 byte
        'str': 8,      # pointer size
    }
    
    def __init__(self):
        self.classes: Dict[str, ClassInfo] = {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.top_level_stmts: List[ast.stmt] = []
        
    def parse(self, source_code: str) -> tuple[Dict[str, ClassInfo], Dict[str, FunctionInfo], List[ast.stmt]]:
        """
        Parse Nagini source code and extract class, function, and top-level statement information.
        
        Args:
            source_code: Nagini source code as string
            
        Returns:
            Tuple of (classes dict, functions dict, top-level statements)
        """
        tree = ast.parse(source_code)
        
        # Parse top-level nodes (not using ast.walk to avoid nested functions)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node)
                self.classes[class_info.name] = class_info
            elif isinstance(node, ast.FunctionDef):
                func_info = self._parse_function(node)
                self.functions[func_info.name] = func_info
            else:
                # Collect top-level statements (assignments, expressions, etc.)
                self.top_level_stmts.append(node)

        return self.classes, self.functions, self.top_level_stmts
    
    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse a class definition node"""
        # Extract properties from decorator
        malloc_strategy = 'gc'  # Default to gc strategy
        layout = 'cpp'
        paradigm = 'object'
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'property':
                    props = self._extract_decorator_props(decorator)
                    malloc_strategy = props.get('malloc_strategy', malloc_strategy)
                    layout = props.get('layout', layout)
                    paradigm = props.get('paradigm', paradigm)
        
        # Extract parent class (all classes inherit from Object by default)
        parent = 'Object'
        if node.bases:
            # Get the first base class
            if isinstance(node.bases[0], ast.Name):
                parent = node.bases[0].id
        
        # Extract fields and methods from class body
        fields = []
        methods = []
        offset = 0
        
        # Add object header for object paradigm
        if paradigm == 'object':
            # Object header: 8 bytes (reference counter)
            # Inherited from Object class
            offset = 8
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Field definition
                field_name = item.target.id
                type_name = self._extract_type_name(item.annotation)
                size = self.TYPE_SIZES.get(type_name, 8)
                
                field = FieldInfo(
                    name=field_name,
                    type_name=type_name,
                    offset=offset,
                    size=size
                )
                fields.append(field)
                offset += size
            elif isinstance(item, ast.FunctionDef):
                # Method definition
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
        """Extract properties from @property decorator"""
        props = {}
        
        for keyword in decorator.keywords:
            if isinstance(keyword.value, ast.Constant):
                props[keyword.arg] = keyword.value.value
                
        return props
    
    def _extract_type_name(self, annotation) -> str:
        """Extract type name from annotation"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        return 'unknown'
    
    def _parse_function(self, node: ast.FunctionDef) -> FunctionInfo:
        """Parse a function definition node"""
        # Extract parameters with type annotations
        params = []
        strict_params = []  # Track which parameters have type annotations
        
        for arg in node.args.args:
            param_name = arg.arg
            param_type = None
            if arg.annotation:
                param_type = self._extract_type_name(arg.annotation)
                strict_params.append(param_name)  # Has type annotation = strict typing
            params.append((param_name, param_type))
        
        # Check for *args
        has_varargs = node.args.vararg is not None
        varargs_name = None
        if has_varargs and hasattr(node.args.vararg, 'arg'):
            varargs_name = node.args.vararg.arg
        
        # Check for **kwargs
        has_kwargs = node.args.kwarg is not None
        kwargs_name = None
        if has_kwargs and hasattr(node.args.kwarg, 'arg'):
            kwargs_name = node.args.kwarg.arg
        
        # Extract return type
        return_type = None
        if node.returns:
            return_type = self._extract_type_name(node.returns)
        
        # Store the body as AST statements (will be converted to IR later)
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
            is_static=any(isinstance(deco, ast.Name) and deco.id == 'staticmethod' for deco in node.decorator_list)
        )
