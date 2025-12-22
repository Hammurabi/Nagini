"""
Nagini Compiler Package
Contains the AST parser, IR generator, and backend code generation.
"""

from .parser import NaginiParser
from .ir import NaginiIR
from .backend import LLVMBackend

__all__ = ['NaginiParser', 'NaginiIR', 'LLVMBackend']
