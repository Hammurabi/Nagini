"""
Nagini C Backend
Generates C code and compiles to native machine code using gcc/clang.
Future versions will support direct LLVM IR generation.
"""

import sys
from typing import Dict, Optional
from .ir import NaginiIR, FunctionIR
from .parser import ClassInfo, FieldInfo


class LLVMBackend:
    """
    C backend for Nagini compiler (LLVM backend planned for future).
    Generates C code and compiles to native machine code using gcc/clang.
    """
    
    def __init__(self, ir: NaginiIR):
        self.ir = ir
        self.output_code = []
        
    def generate(self) -> str:
        """
        Generate target code (C for initial implementation).
        Returns the generated C code as a string.
        """
        self.output_code = []
        
        # Generate headers
        self._gen_headers()
        
        # Generate class structs
        for class_name, class_info in self.ir.classes.items():
            self._gen_class_struct(class_info)
        
        # Generate functions
        for func in self.ir.functions:
            self._gen_function(func)
        
        return '\n'.join(self.output_code)
    
    def _gen_headers(self):
        """Generate necessary C headers"""
        self.output_code.append('#include <stdio.h>')
        self.output_code.append('#include <stdlib.h>')
        self.output_code.append('#include <stdint.h>')
        self.output_code.append('')
        
    def _gen_class_struct(self, class_info: ClassInfo):
        """Generate C struct for a Nagini class"""
        self.output_code.append(f'/* Class: {class_info.name} */')
        self.output_code.append(f'/* malloc_strategy: {class_info.malloc_strategy} */')
        self.output_code.append(f'/* layout: {class_info.layout} */')
        self.output_code.append(f'/* paradigm: {class_info.paradigm} */')
        
        self.output_code.append(f'typedef struct {{')
        
        # Add object header for object paradigm
        if class_info.paradigm == 'object':
            self.output_code.append('    /* Object Header */')
            self.output_code.append('    uint64_t type_id;')
            self.output_code.append('    uint32_t alloc_type;')
            self.output_code.append('    uint32_t ref_count;')
            self.output_code.append('    void* parent_ptr;')
            self.output_code.append('')
        
        # Add fields
        if class_info.fields:
            self.output_code.append('    /* Fields */')
            for field in class_info.fields:
                c_type = self._map_type_to_c(field.type_name)
                self.output_code.append(f'    {c_type} {field.name};')
        
        self.output_code.append(f'}} {class_info.name};')
        self.output_code.append('')
        
    def _gen_function(self, func: FunctionIR):
        """Generate C function"""
        if func.name == 'main':
            self.output_code.append('int main() {')
            for stmt in func.body:
                # Simple statement translation
                if stmt.startswith('print(') and stmt.endswith(')'):
                    # Extract string from print statement
                    msg = stmt[6:-1]  # Remove 'print(' and ')'
                    self.output_code.append(f'    printf({msg});')
                    self.output_code.append(f'    printf("\\n");')
                else:
                    # For other statements, output as-is
                    self.output_code.append(f'    /* TODO: {stmt} */')
            self.output_code.append('    return 0;')
            self.output_code.append('}')
        else:
            # Handle other functions
            return_type = self._map_type_to_c(func.return_type)
            params_str = ', '.join([f'{self._map_type_to_c(t)} {n}' for n, t in func.params])
            self.output_code.append(f'{return_type} {func.name}({params_str}) {{')
            for stmt in func.body:
                self.output_code.append(f'    {stmt}')
            self.output_code.append('}')
        self.output_code.append('')
    
    def _map_type_to_c(self, nagini_type: str) -> str:
        """Map Nagini types to C types"""
        type_map = {
            'int': 'int64_t',
            'float': 'double',
            'bool': 'uint8_t',
            'str': 'char*',
            'void': 'void',
        }
        return type_map.get(nagini_type, 'void*')
    
    def compile_to_executable(self, output_path: str, c_code: str) -> bool:
        """
        Compile generated C code to executable using gcc/clang.
        
        Args:
            output_path: Path to output executable
            c_code: Generated C code
            
        Returns:
            True if compilation successful, False otherwise
        """
        import tempfile
        import subprocess
        import os
        
        # Write C code to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(c_code)
            c_file = f.name
        
        try:
            # Try to compile with gcc (or clang as fallback)
            compilers = ['gcc', 'clang', 'cc']
            for compiler in compilers:
                try:
                    result = subprocess.run(
                        [compiler, c_file, '-o', output_path],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return True
                    else:
                        print(f"Compilation error with {compiler}:")
                        print(result.stderr)
                except FileNotFoundError:
                    continue
            
            print("No C compiler found. Please install gcc or clang.")
            return False
            
        finally:
            # Clean up temporary file
            if os.path.exists(c_file):
                os.unlink(c_file)
