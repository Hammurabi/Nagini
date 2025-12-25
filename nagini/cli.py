#!/usr/bin/env python3
"""
Nagini Compiler Command-Line Interface (CLI)

This module provides the user-facing command-line interface for the Nagini compiler.
It orchestrates the entire compilation pipeline:

Pipeline Overview:
    1. Parse: Read source code and create AST (parser.py)
    2. Generate IR: Transform AST to intermediate representation (ir.py)
    3. Generate Code: Produce C code from IR (backend.py)
    4. Compile: Use gcc/clang to create native executable

Usage:
    nagini compile hello.nag              # Compile to executable
    nagini compile hello.nag -v           # Verbose output
    nagini compile hello.nag --emit-c     # Output C code only
    nagini compile hello.nag -o myapp     # Specify output name

The CLI handles file I/O, error reporting, and optional verbose output to help
users understand what the compiler is doing at each phase.
"""

import sys
import argparse
from pathlib import Path
from nagini.compiler import NaginiParser, NaginiIR, LLVMBackend


def compile_file(input_file: str, output_file: str = None, emit_c: bool = False, verbose: bool = False):
    """
    Compile a Nagini source file to an executable.
    
    This is the main compilation function that orchestrates all four phases
    of the compilation pipeline. Each phase transforms the code into a
    different representation until we reach native machine code.
    
    Args:
        input_file: Path to input .nag file
        output_file: Path to output executable (default: same name as input without extension)
        emit_c: If True, output the generated C code instead of compiling to executable
        verbose: Print detailed information about each compilation phase
        
    Returns:
        0 on success, 1 on failure
    """
    # ========== Read Source File ==========
    # First, load the Nagini source code from disk
    try:
        with open(input_file, 'r') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return 1
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1
    
    if verbose:
        print(f"Compiling {input_file}...")
    
    # ========== Phase 1: Parse AST ==========
    # Use Python's AST parser to extract class and function definitions
    if verbose:
        print("Phase 1: Parsing AST...")
    parser = NaginiParser()
    classes, functions, top_level_stmts = parser.parse(source_code)
    
    if verbose:
        print(f"  Found {len(classes)} class(es)")
        for name, info in classes.items():
            print(f"    - {name}: {len(info.fields)} field(s), {info.malloc_strategy}/{info.paradigm}")
        print(f"  Found {len(functions)} function(s)")
        for name, info in functions.items():
            print(f"    - {name}: {len(info.params)} param(s), returns {info.return_type}")
        print(f"  Found {len(top_level_stmts)} top-level statement(s)")
    
    # ========== Phase 2: Generate IR ==========
    # Transform parsed structures into intermediate representation
    if verbose:
        print("Phase 2: Generating IR...")
    ir = NaginiIR(classes, functions, top_level_stmts)
    ir.generate()
    
    # ========== Phase 3: Backend Code Generation ==========
    # Generate C code from the IR
    if verbose:
        print("Phase 3: Generating C code...")
    backend = LLVMBackend(ir)
    c_code = backend.generate()
    
    # Determine output path (default to input filename without extension)
    if output_file is None:
        output_file = Path(input_file).stem
    
    # If emit_c flag is set, write C code to file and exit
    # This is useful for debugging or examining generated code
    if emit_c:
        c_output = f"{output_file}.c"
        with open(c_output, 'w') as f:
            f.write(c_code)
        print(f"Generated C code written to: {c_output}")
        return 0
    
    # ========== Phase 4: Compile to Native Executable ==========
    # Use system C compiler (gcc/clang) to create executable
    if verbose:
        print(f"Phase 4: Compiling to executable: {output_file}...")
    
    success = backend.compile_to_executable(output_file, c_code)
    
    if success:
        print(f"Successfully compiled to: {output_file}")
        if verbose:
            # Show generated C code in verbose mode
            print("\nGenerated C code:")
            print("=" * 60)
            print(c_code)
            print("=" * 60)
        return 0
    else:
        # Compilation failed - show C code to help debug
        print("Compilation failed.")
        print("\nGenerated C code:")
        print("=" * 60)
        print(c_code)
        print("=" * 60)
        return 1


def main():
    """
    Main CLI entry point.
    
    Sets up argument parsing and dispatches to appropriate command handlers.
    Currently supports the 'compile' command with various options.
    """
    parser = argparse.ArgumentParser(
        description='Nagini Programming Language Compiler v0.2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nagini compile hello.nag              # Compile to executable
  nagini compile hello.nag -o program   # Specify output name
  nagini compile hello.nag --emit-c     # Output C code only
  nagini compile hello.nag -v           # Verbose output
        """
    )
    
    # Create subparsers for different commands (currently only 'compile')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # ===== Compile Command =====
    compile_parser = subparsers.add_parser('compile', help='Compile a Nagini source file')
    compile_parser.add_argument('input', help='Input .nag file')
    compile_parser.add_argument('-o', '--output', help='Output file name (default: same as input without extension)')
    compile_parser.add_argument('--emit-c', action='store_true', help='Emit C code instead of compiling to executable')
    compile_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed compilation information')
    
    # Parse command-line arguments
    args = parser.parse_args()
    
    # If no command specified, show help
    if args.command is None:
        parser.print_help()
        return 0
    
    # Dispatch to appropriate command handler
    if args.command == 'compile':
        return compile_file(args.input, args.output, args.emit_c, args.verbose)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
