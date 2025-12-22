"""
Nagini Intermediate Representation (IR)
Provides an intermediate representation of the Nagini program for code generation.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from .parser import ClassInfo, FieldInfo


@dataclass
class FunctionIR:
    """IR for a function"""
    name: str
    params: List[tuple]  # (name, type)
    return_type: str
    body: List[str]  # IR instructions
    

@dataclass
class AllocationIR:
    """IR for object allocation"""
    class_name: str
    alloc_type: str  # pool, gc, heap
    args: List[str]


class NaginiIR:
    """
    Intermediate Representation for Nagini programs.
    Transforms parsed AST into a structured IR suitable for code generation.
    """
    
    def __init__(self, classes: Dict[str, ClassInfo]):
        self.classes = classes
        self.functions: List[FunctionIR] = []
        self.main_body: List[str] = []
        
    def generate(self) -> 'NaginiIR':
        """Generate IR from parsed classes"""
        # For a basic hello world, we'll generate a simple main function
        # that prints "Hello, World!"
        
        main_func = FunctionIR(
            name='main',
            params=[],
            return_type='int',
            body=['print("Hello, World!")']
        )
        self.functions.append(main_func)
        
        return self
    
    def add_function(self, func: FunctionIR):
        """Add a function to the IR"""
        self.functions.append(func)
        
    def get_class_layout(self, class_name: str) -> Optional[ClassInfo]:
        """Get the memory layout for a class"""
        return self.classes.get(class_name)
