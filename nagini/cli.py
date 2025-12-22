#!/usr/bin/env python3
"""
Nagini Compiler CLI
Command-line interface for the Nagini programming language compiler.
"""

import sys
import argparse
from pathlib import Path
from nagini.compiler import NaginiParser, NaginiIR, LLVMBackend


def compile_file(input_file: str, output_file: str = None, emit_c: bool = False, verbose: bool = False):
    """
    Compile a Nagini source file to an executable.
    
    Args:
        input_file: Path to input .nag file
        output_file: Path to output executable (default: same name as input)
        emit_c: If True, output the generated C code instead of compiling
        verbose: Print verbose compilation information
    """
    # Read source file
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
    
    # Phase 1: Parse
    if verbose:
        print("Phase 1: Parsing AST...")
    parser = NaginiParser()
    classes, functions = parser.parse(source_code)
    
    if verbose:
        print(f"  Found {len(classes)} class(es)")
        for name, info in classes.items():
            print(f"    - {name}: {len(info.fields)} field(s), {info.malloc_strategy}/{info.paradigm}")
        print(f"  Found {len(functions)} function(s)")
        for name, info in functions.items():
            print(f"    - {name}: {len(info.params)} param(s), returns {info.return_type}")
    
    # Phase 2: Generate IR
    if verbose:
        print("Phase 2: Generating IR...")
    ir = NaginiIR(classes, functions)
    ir.generate()
    
    # Phase 3: Backend code generation
    if verbose:
        print("Phase 3: Generating C code...")
    backend = LLVMBackend(ir)
    c_code = backend.generate()
    
    # Determine output path
    if output_file is None:
        output_file = Path(input_file).stem
    
    # If emit_c flag is set, write C code and exit
    if emit_c:
        c_output = f"{output_file}.c"
        with open(c_output, 'w') as f:
            f.write(c_code)
        print(f"Generated C code written to: {c_output}")
        return 0
    
    # Phase 4: Compile to executable
    if verbose:
        print(f"Phase 4: Compiling to executable: {output_file}...")
    
    success = backend.compile_to_executable(output_file, c_code)
    
    if success:
        print(f"Successfully compiled to: {output_file}")
        if verbose:
            print("\nGenerated C code:")
            print("=" * 60)
            print(c_code)
            print("=" * 60)
        return 0
    else:
        print("Compilation failed.")
        print("\nGenerated C code:")
        print("=" * 60)
        print(c_code)
        print("=" * 60)
        return 1


def main():
    """Main CLI entry point"""
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
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Compile command
    compile_parser = subparsers.add_parser('compile', help='Compile a Nagini source file')
    compile_parser.add_argument('input', help='Input .nag file')
    compile_parser.add_argument('-o', '--output', help='Output file name')
    compile_parser.add_argument('--emit-c', action='store_true', help='Emit C code instead of compiling')
    compile_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == 'compile':
        return compile_file(args.input, args.output, args.emit_c, args.verbose)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
