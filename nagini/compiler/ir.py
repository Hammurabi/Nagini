"""
Nagini Intermediate Representation (IR)
Provides an intermediate representation of the Nagini program for code generation.
"""

import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
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
    kwargs: Optional[Dict[str, ExprIR]] = None  # Keyword arguments
    is_method: bool = False
    obj: Optional[ExprIR] = None  # For method calls

@dataclass
class SetAttrIR(ExprIR):
    """Set attribute (obj.attr = value)"""
    obj: ExprIR
    attr: str
    value: ExprIR

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
class ConstructorCallIR(ExprIR):
    """Constructor call (ClassName(...))"""
    class_name: str
    args: List[ExprIR]
    kwargs: Optional[Dict[str, ExprIR]] = None


@dataclass
class LambdaIR(ExprIR):
    """Lambda expression"""
    params: List[tuple]  # (name, type)
    body: ExprIR  # Single expression for lambda body
    capture_vars: List[str] = None  # Variables captured from outer scope


@dataclass
class BoxIR(ExprIR):
    """Box a primitive value into an object (int -> Int, float -> Double)"""
    expr: ExprIR
    target_type: str  # 'Int' or 'Double'


@dataclass
class UnboxIR(ExprIR):
    """Unbox an object to a primitive value (Int -> int, Double -> float)"""
    expr: ExprIR
    source_type: str  # 'Int' or 'Double'


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
    has_varargs: bool = False  # *args support
    varargs_name: Optional[str] = None  # Name of *args parameter
    has_kwargs: bool = False  # **kwargs support
    kwargs_name: Optional[str] = None  # Name of **kwargs parameter
    strict_params: List[str] = field(default_factory=list)  # List of parameter names with strict typing
    
    
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
    
    def __init__(self, classes: Dict[str, ClassInfo], functions: Dict[str, FunctionInfo], top_level_stmts: List[ast.stmt]):
        self.classes = classes
        self.parsed_functions = functions
        self.top_level_stmts = top_level_stmts
        self.functions: List[FunctionIR] = []
        self.main_body: List[StmtIR] = []
        self.const_count = 0
        self.consts = {}
        self.consts_dict = {}
        
        # Cache for converted methods to avoid double conversion
        self.method_ir_cache = {}

    def register_string_constant(self, value: str) -> str:
        """Register a string constant and return its unique name"""
        if value in self.consts_dict:
            return self.consts_dict[value]
        ident = self.const_count
        self.consts[ident] = (f'"{value}"', 'alloc_str')
        self.const_count += 1
        self.consts_dict[value] = ident
        return ident
    
    def register_int_constant(self, value: int) -> str:
        """Register an integer constant and return its unique name"""
        if value in self.consts_dict:
            return self.consts_dict[value]
        ident = self.const_count
        self.consts[ident] = (value, 'alloc_int')
        self.const_count += 1
        self.consts_dict[value] = ident
        return ident
    
    def register_float_constant(self, value: float) -> str:
        """Register a float constant and return its unique name"""
        if value in self.consts_dict:
            return self.consts_dict[value]
        ident = self.const_count
        self.consts[ident] = (value, 'alloc_float')
        self.const_count += 1
        self.consts_dict[value] = ident
        return ident
    
    def register_bytes_constant(self, value: bytes) -> str:
        """Register a bytes constant and return its unique name"""
        if value in self.consts_dict:
            return self.consts_dict[value]
        ident = self.const_count
        self.consts[ident] = (value, 'alloc_bytes')
        self.const_count += 1
        self.consts_dict[value] = ident
        return ident
    
    def register_bool_constant(self, value: int) -> str:
        """Register a boolean constant and return its unique name"""
        if value in self.consts_dict:
            return self.consts_dict[value]
        ident = self.const_count
        self.consts[ident] = (value, 'alloc_bool')
        self.const_count += 1
        self.consts_dict[value] = ident
        return ident
    
    def register_class_constant(self, class_info: ClassInfo):
        """Register a class constant"""
        if str(class_info) in self.consts_dict:
            return self.consts_dict[str(class_info)]
        class_name = class_info.name
        ident = self.const_count
        self.consts[ident] = class_info
        self.const_count += 1
        class_info.class_id = ident
        self.consts_dict[str(class_info)] = ident
        return ident

    # def register_method_constant(self, method_info: FunctionInfo) -> str:
    #     """Register a method constant"""
    #     method_name = method_info.name
    #     ident = self.const_count
    #     self.consts[ident] = method_info
    #     self.const_count += 1
    #     method_info.method_id = ident
    #     return ident
    
    def generate(self) -> 'NaginiIR':
        """Generate IR from parsed classes and functions"""
        # Convert class methods to IR first (to register all constants)
        for class_name, class_info in self.classes.items():
            self.classes[class_name].name_id = self.register_string_constant(class_name)
            self.register_class_constant(class_info)
            for method_info in class_info.methods:
                method_info.name_id = self.register_string_constant(method_info.name)
                # Convert method to IR to register any constants used
                method_ir = self._convert_function_to_ir(method_info)
                # Cache the method IR for later use by backend
                cache_key = (class_name, method_info.name, method_info.line_no)
                self.method_ir_cache[cache_key] = method_ir
        
        # Convert parsed functions to IR
        for func_name, func_info in self.parsed_functions.items():
            func_ir = self._convert_function_to_ir(func_info)
            self.functions.append(func_ir)
        
        # Check if there's already a main function defined
        has_main = any(f.name == 'main' for f in self.functions)
        
        # If no main function exists, create one from top-level statements
        if not has_main:
            if self.top_level_stmts:
                # Convert top-level statements to IR
                main_body_ir = []
                for stmt in self.top_level_stmts:
                    # Check for 'if __name__ == "__main__"' pattern
                    if self._is_name_main_check(stmt):
                        # Extract the body of the if statement
                        if isinstance(stmt, ast.If):
                            for body_stmt in stmt.body:
                                stmt_ir = self._convert_stmt_to_ir(body_stmt)
                                if stmt_ir:
                                    main_body_ir.append(stmt_ir)
                    else:
                        stmt_ir = self._convert_stmt_to_ir(stmt)
                        if stmt_ir:
                            main_body_ir.append(stmt_ir)
                
                # Create a synthetic main function
                main_func = FunctionIR(
                    name='main',
                    params=[],
                    return_type='void',
                    body=main_body_ir,
                    has_varargs=False,
                    varargs_name=None,
                    has_kwargs=False,
                    kwargs_name=None,
                    strict_params=[]
                )
                self.functions.append(main_func)
            else:
                raise RuntimeError("No 'main' function or top-level statements found in the program.")
        
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
            body=body_ir,
            has_varargs=func_info.has_varargs,
            varargs_name=func_info.varargs_name,
            has_kwargs=func_info.has_kwargs,
            kwargs_name=func_info.kwargs_name,
            strict_params=func_info.strict_params  # No need for 'or []' anymore
        )
    
    def _is_name_main_check(self, stmt: ast.stmt) -> bool:
        """Check if statement is 'if __name__ == "__main__"' pattern"""
        if not isinstance(stmt, ast.If):
            return False
        
        # Check for comparison: __name__ == "__main__"
        if isinstance(stmt.test, ast.Compare):
            left = stmt.test.left
            if isinstance(left, ast.Name) and left.id == '__name__':
                if stmt.test.ops and stmt.test.comparators:
                    if isinstance(stmt.test.ops[0], ast.Eq):
                        right = stmt.test.comparators[0]
                        if isinstance(right, ast.Constant) and right.value == "__main__":
                            return True
        return False
    
    def _convert_stmt_to_ir(self, stmt: ast.stmt) -> Optional[StmtIR]:
        """Convert an AST statement to IR"""
        if isinstance(stmt, ast.Assign):
            # Simple assignment (only single target for now)
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                target = stmt.targets[0].id
                value = self._convert_expr_to_ir(stmt.value)
                return AssignIR(target, value)
            else:
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        tgt = target.id
                        val = self._convert_expr_to_ir(stmt.value)
                        return AssignIR(tgt, val)
                    elif isinstance(target, ast.Tuple):
                        raise NotImplementedError("Tuple unpacking in assignments is not supported yet.")
                    elif isinstance(target, ast.Attribute):
                        # Attribute assignment (e.g., obj.attr = value)
                        obj_ir = self._convert_expr_to_ir(target.value)
                        attr_name = self.register_string_constant(target.attr)
                        value_ir = self._convert_expr_to_ir(stmt.value)
                        return SetAttrIR(obj_ir, attr_name, value_ir)
        
        elif isinstance(stmt, ast.AnnAssign):
            # Annotated assignment (e.g., x: int = 5)
            if isinstance(stmt.target, ast.Name):
                target = stmt.target.id
                value = self._convert_expr_to_ir(stmt.value) if stmt.value else ConstantIR(self.register_int_constant(0), 'int')
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
                value = self.register_int_constant(value)
            elif isinstance(value, float):
                type_name = 'float'
                value = self.register_float_constant(value)
            elif isinstance(value, bool):
                type_name = 'bool'
                value = self.register_bool_constant(int(value))
            elif isinstance(value, str):
                type_name = 'str'
                value = self.register_string_constant(value)
            elif isinstance(value, bytes):
                type_name = 'bytes'
                value = self.register_bytes_constant(value)
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
            # Function call or constructor call
            if isinstance(expr.func, ast.Name):
                func_name = expr.func.id
                args = [self._convert_expr_to_ir(arg) for arg in expr.args]
                
                # Extract keyword arguments
                kwargs = {}
                for keyword in expr.keywords:
                    if keyword.arg:  # Named keyword argument
                        kwargs[keyword.arg] = self._convert_expr_to_ir(keyword.value)
                
                # Check if it's a constructor call (capitalized name suggests class)
                if func_name[0].isupper() and func_name in self.classes:
                    # Constructor call
                    return ConstructorCallIR(func_name, args, kwargs if kwargs else None)
                else:
                    # Regular function call
                    return CallIR(func_name, args, kwargs if kwargs else None)
            elif isinstance(expr.func, ast.Attribute):
                # Method call (obj.method())
                obj = self._convert_expr_to_ir(expr.func.value)
                method_name = expr.func.attr
                args = [self._convert_expr_to_ir(arg) for arg in expr.args]
                
                # Extract keyword arguments
                kwargs = {}
                for keyword in expr.keywords:
                    if keyword.arg:
                        kwargs[keyword.arg] = self._convert_expr_to_ir(keyword.value)
                
                return CallIR(method_name, args, kwargs if kwargs else None, is_method=True, obj=obj)
        
        elif isinstance(expr, ast.Lambda):
            # Lambda expression
            params = []
            for arg in expr.args.args:
                param_name = arg.arg
                param_type = None
                if arg.annotation:
                    param_type = self._extract_type_name(arg.annotation)
                params.append((param_name, param_type))
            
            # Convert lambda body (single expression)
            body_expr = self._convert_expr_to_ir(expr.body)
            
            # TODO: Detect captured variables from outer scope
            # For now, we'll leave capture_vars as None
            return LambdaIR(params, body_expr, None)
        
        elif isinstance(expr, ast.Attribute):
            # Member access
            obj = self._convert_expr_to_ir(expr.value)
            # Attribute names need to be string constants for NgGetMember
            attr_idx = self.register_string_constant(expr.attr)
            return AttributeIR(obj, attr_idx)
        
        elif isinstance(expr, ast.Subscript):
            # Subscript access
            obj = self._convert_expr_to_ir(expr.value)
            index = self._convert_expr_to_ir(expr.slice)
            return SubscriptIR(obj, index)
        
        # Return a placeholder for unsupported expressions
        # TODO: Add better error handling or warnings for unsupported expression types
        raise NotImplementedError(f"Expression type {type(expr)} not supported in IR conversion.")
    
    def _extract_type_name(self, annotation) -> str:
        """Extract type name from annotation (helper for lambda)"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        return 'unknown'
    
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
