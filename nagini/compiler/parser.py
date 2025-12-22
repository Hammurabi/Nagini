"""
Nagini AST Parser
Parses Nagini source code using Python's built-in AST parser and extracts
class properties, field information, and allocation strategies.
"""

import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class FieldInfo:
    """Information about a class field"""
    name: str
    type_name: str
    offset: int = 0  # Will be calculated during layout
    size: int = 0    # Will be calculated based on type


@dataclass
class ClassInfo:
    """Information about a Nagini class"""
    name: str
    fields: List[FieldInfo]
    malloc_strategy: str = 'pool'  # pool, gc, heap
    layout: str = 'cpp'           # cpp, std430, custom
    paradigm: str = 'object'      # object, data
    parent: Optional[str] = None
    
    
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
        
    def parse(self, source_code: str) -> Dict[str, ClassInfo]:
        """
        Parse Nagini source code and extract class information.
        
        Args:
            source_code: Nagini source code as string
            
        Returns:
            Dictionary mapping class names to ClassInfo objects
        """
        tree = ast.parse(source_code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node)
                self.classes[class_info.name] = class_info
                
        return self.classes
    
    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse a class definition node"""
        # Extract properties from decorator
        malloc_strategy = 'pool'
        layout = 'cpp'
        paradigm = 'object'
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'property':
                    props = self._extract_decorator_props(decorator)
                    malloc_strategy = props.get('malloc_strategy', malloc_strategy)
                    layout = props.get('layout', layout)
                    paradigm = props.get('paradigm', paradigm)
        
        # Extract fields from class body
        fields = []
        offset = 0
        
        # Add object header for object paradigm
        if paradigm == 'object':
            # Object header: 32 bytes (type_id, alloc_type, ref_count, parent_ptr)
            offset = 32
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
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
        
        return ClassInfo(
            name=node.name,
            fields=fields,
            malloc_strategy=malloc_strategy,
            layout=layout,
            paradigm=paradigm
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
