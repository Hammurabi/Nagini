"""
Nagini Intermediate Representation (IR)
Provides an intermediate representation of the Nagini program for code generation.
"""

import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .parser import ClassInfo, FieldInfo, FunctionInfo


@dataclass
class ExprIR:
    """Base class for expression IR nodes"""
    pass


@dataclass
class ConstantIR(ExprIR):
    """Constant value"""
    value: Any
    type_name: str


@dataclass
class VariableIR(ExprIR):
    """Variable reference"""
    name: str


@dataclass
class BinOpIR(ExprIR):
    """Binary operation"""
    left: ExprIR
    op: str  # +, -, *, /, //, %, **, ==, !=, <, <=, >, >=, and, or
    right: ExprIR


@dataclass
class UnaryOpIR(ExprIR):
    """Unary operation"""
    op: str  # -, not, +
    operand: ExprIR


@dataclass
class CallIR(ExprIR):
    """Function/method call"""
    func_name: str
    args: List[ExprIR]
    is_method: bool = False
    obj: Optional[ExprIR] = None  # For method calls


@dataclass
class AttributeIR(ExprIR):
    """Member access (obj.member)"""
    obj: ExprIR
    attr: str


@dataclass
class SubscriptIR(ExprIR):
    """Subscript access (obj[key])"""
    obj: ExprIR
    index: ExprIR


@dataclass
class StmtIR:
    """Base class for statement IR nodes"""
    pass


@dataclass
class AssignIR(StmtIR):
    """Assignment statement"""
    target: str
    value: ExprIR


@dataclass
class ReturnIR(StmtIR):
    """Return statement"""
    value: Optional[ExprIR]


@dataclass
class IfIR(StmtIR):
    """If statement"""
    condition: ExprIR
    then_body: List[StmtIR]
    elif_parts: List[tuple]  # [(condition, body), ...]
    else_body: Optional[List[StmtIR]]


@dataclass
class WhileIR(StmtIR):
    """While loop"""
    condition: ExprIR
    body: List[StmtIR]


@dataclass
class ForIR(StmtIR):
    """For loop"""
    target: str
    iter_expr: ExprIR
    body: List[StmtIR]


@dataclass
class ExprStmtIR(StmtIR):
    """Expression statement (e.g., function call)"""
    expr: ExprIR


@dataclass
class FunctionIR:
    """IR for a function"""
    name: str
    params: List[tuple]  # (name, type)
    return_type: str
    body: List[StmtIR]  # IR statements
    
    
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
    
    def __init__(self, classes: Dict[str, ClassInfo], functions: Dict[str, FunctionInfo]):
        self.classes = classes
        self.parsed_functions = functions
        self.functions: List[FunctionIR] = []
        self.main_body: List[StmtIR] = []
        
    def generate(self) -> 'NaginiIR':
        """Generate IR from parsed classes and functions"""
        # Convert parsed functions to IR
        for func_name, func_info in self.parsed_functions.items():
            func_ir = self._convert_function_to_ir(func_info)
            self.functions.append(func_ir)
        
        # If no main function exists, generate a simple hello world
        if not any(f.name == 'main' for f in self.functions):
            main_func = FunctionIR(
                name='main',
                params=[],
                return_type='int',
                body=[
                    ExprStmtIR(CallIR('printf', [ConstantIR('"Hello, World!"', 'str')]))
                ]
            )
            self.functions.append(main_func)
        
        return self
    
    def _convert_function_to_ir(self, func_info: FunctionInfo) -> FunctionIR:
        """Convert a parsed function to IR"""
        body_ir = []
        for stmt in func_info.body:
            stmt_ir = self._convert_stmt_to_ir(stmt)
            if stmt_ir:
                body_ir.append(stmt_ir)
        
        return FunctionIR(
            name=func_info.name,
            params=func_info.params,
            return_type=func_info.return_type or 'void',
            body=body_ir
        )
    
    def _convert_stmt_to_ir(self, stmt: ast.stmt) -> Optional[StmtIR]:
        """Convert an AST statement to IR"""
        if isinstance(stmt, ast.Assign):
            # Simple assignment (only single target for now)
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                target = stmt.targets[0].id
                value = self._convert_expr_to_ir(stmt.value)
                return AssignIR(target, value)
        
        elif isinstance(stmt, ast.AnnAssign):
            # Annotated assignment (e.g., x: int = 5)
            if isinstance(stmt.target, ast.Name):
                target = stmt.target.id
                value = self._convert_expr_to_ir(stmt.value) if stmt.value else ConstantIR(0, 'int')
                return AssignIR(target, value)
        
        elif isinstance(stmt, ast.Return):
            value = self._convert_expr_to_ir(stmt.value) if stmt.value else None
            return ReturnIR(value)
        
        elif isinstance(stmt, ast.If):
            condition = self._convert_expr_to_ir(stmt.test)
            then_body = [self._convert_stmt_to_ir(s) for s in stmt.body]
            then_body = [s for s in then_body if s]  # Filter None
            
            # Handle elif and else
            elif_parts = []
            else_body = None
            
            if stmt.orelse:
                # Check if it's an elif (single If statement) or else
                if len(stmt.orelse) == 1 and isinstance(stmt.orelse[0], ast.If):
                    # This is an elif
                    elif_stmt = stmt.orelse[0]
                    elif_cond = self._convert_expr_to_ir(elif_stmt.test)
                    elif_body = [self._convert_stmt_to_ir(s) for s in elif_stmt.body]
                    elif_body = [s for s in elif_body if s]
                    elif_parts.append((elif_cond, elif_body))
                    
                    # Check for more elif or else
                    if elif_stmt.orelse:
                        else_body = [self._convert_stmt_to_ir(s) for s in elif_stmt.orelse]
                        else_body = [s for s in else_body if s]
                else:
                    # This is an else
                    else_body = [self._convert_stmt_to_ir(s) for s in stmt.orelse]
                    else_body = [s for s in else_body if s]
            
            return IfIR(condition, then_body, elif_parts, else_body)
        
        elif isinstance(stmt, ast.While):
            condition = self._convert_expr_to_ir(stmt.test)
            body = [self._convert_stmt_to_ir(s) for s in stmt.body]
            body = [s for s in body if s]
            return WhileIR(condition, body)
        
        elif isinstance(stmt, ast.For):
            if isinstance(stmt.target, ast.Name):
                target = stmt.target.id
                iter_expr = self._convert_expr_to_ir(stmt.iter)
                body = [self._convert_stmt_to_ir(s) for s in stmt.body]
                body = [s for s in body if s]
                return ForIR(target, iter_expr, body)
        
        elif isinstance(stmt, ast.Expr):
            # Expression statement (e.g., function call)
            # Skip string constants (docstrings) only if they appear at the start
            if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                # This is likely a docstring, skip it
                return None
            expr = self._convert_expr_to_ir(stmt.value)
            return ExprStmtIR(expr)
        
        return None
    
    def _convert_expr_to_ir(self, expr: ast.expr) -> ExprIR:
        """Convert an AST expression to IR"""
        if isinstance(expr, ast.Constant):
            # Infer type from value
            value = expr.value
            if isinstance(value, int):
                type_name = 'int'
            elif isinstance(value, float):
                type_name = 'float'
            elif isinstance(value, bool):
                type_name = 'bool'
            elif isinstance(value, str):
                type_name = 'str'
            else:
                type_name = 'unknown'
            return ConstantIR(value, type_name)
        
        elif isinstance(expr, ast.Name):
            return VariableIR(expr.id)
        
        elif isinstance(expr, ast.BinOp):
            left = self._convert_expr_to_ir(expr.left)
            right = self._convert_expr_to_ir(expr.right)
            op = self._binop_to_str(expr.op)
            return BinOpIR(left, op, right)
        
        elif isinstance(expr, ast.UnaryOp):
            operand = self._convert_expr_to_ir(expr.operand)
            op = self._unaryop_to_str(expr.op)
            return UnaryOpIR(op, operand)
        
        elif isinstance(expr, ast.Compare):
            # Handle comparison (simplify to binary op for now)
            left = self._convert_expr_to_ir(expr.left)
            if expr.ops and expr.comparators:
                op = self._cmpop_to_str(expr.ops[0])
                right = self._convert_expr_to_ir(expr.comparators[0])
                return BinOpIR(left, op, right)
        
        elif isinstance(expr, ast.BoolOp):
            # Boolean operation (and, or)
            op = 'and' if isinstance(expr.op, ast.And) else 'or'
            # Chain multiple operands as nested binary ops
            result = self._convert_expr_to_ir(expr.values[0])
            for val in expr.values[1:]:
                right = self._convert_expr_to_ir(val)
                result = BinOpIR(result, op, right)
            return result
        
        elif isinstance(expr, ast.Call):
            # Function call
            if isinstance(expr.func, ast.Name):
                func_name = expr.func.id
                args = [self._convert_expr_to_ir(arg) for arg in expr.args]
                return CallIR(func_name, args)
            elif isinstance(expr.func, ast.Attribute):
                # Method call (obj.method())
                obj = self._convert_expr_to_ir(expr.func.value)
                method_name = expr.func.attr
                args = [self._convert_expr_to_ir(arg) for arg in expr.args]
                return CallIR(method_name, args, is_method=True, obj=obj)
        
        elif isinstance(expr, ast.Attribute):
            # Member access
            obj = self._convert_expr_to_ir(expr.value)
            return AttributeIR(obj, expr.attr)
        
        elif isinstance(expr, ast.Subscript):
            # Subscript access
            obj = self._convert_expr_to_ir(expr.value)
            index = self._convert_expr_to_ir(expr.slice)
            return SubscriptIR(obj, index)
        
        # Return a placeholder for unsupported expressions
        # TODO: Add better error handling or warnings for unsupported expression types
        return ConstantIR(0, 'unknown')
    
    def _binop_to_str(self, op: ast.operator) -> str:
        """Convert AST binary operator to string"""
        op_map = {
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/',
            ast.FloorDiv: '//',
            ast.Mod: '%',
            ast.Pow: '**',
        }
        return op_map.get(type(op), '+')
    
    def _unaryop_to_str(self, op: ast.unaryop) -> str:
        """Convert AST unary operator to string"""
        op_map = {
            ast.UAdd: '+',
            ast.USub: '-',
            ast.Not: 'not',
        }
        return op_map.get(type(op), '+')
    
    def _cmpop_to_str(self, op: ast.cmpop) -> str:
        """Convert AST comparison operator to string"""
        op_map = {
            ast.Eq: '==',
            ast.NotEq: '!=',
            ast.Lt: '<',
            ast.LtE: '<=',
            ast.Gt: '>',
            ast.GtE: '>=',
        }
        return op_map.get(type(op), '==')
    
    def add_function(self, func: FunctionIR):
        """Add a function to the IR"""
        self.functions.append(func)
        
    def get_class_layout(self, class_name: str) -> Optional[ClassInfo]:
        """Get the memory layout for a class"""
        return self.classes.get(class_name)
