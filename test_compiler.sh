#!/bin/bash
# Test script for Nagini compiler
# Runs all examples and verifies output

set -euo pipefail

echo "========================================"
echo "Nagini Compiler Test Suite"
echo "========================================"
echo ""

# Test 1: Basic hello world
echo "Test 1: Basic Hello World"
echo "---"
python3 -m nagini.cli compile nagini/examples/hello.nag -o test_hello
./test_hello
echo "✓ Passed"
echo ""

# Test 2: Hello world with class
echo "Test 2: Hello World with Class"
echo "---"
python3 -m nagini.cli compile nagini/examples/hello_class.nag -o test_hello_class -v
./test_hello_class
echo "✓ Passed"
echo ""

# Test 3: Memory management example
echo "Test 3: Memory Management Example"
echo "---"
python3 -m nagini.cli compile nagini/examples/memory_example.nag -o test_memory -v
./test_memory
echo "✓ Passed"
echo ""

# Test 4: Emit C code only
echo "Test 4: Emit C Code"
echo "---"
python3 -m nagini.cli compile nagini/examples/hello.nag --emit-c -o test_emit
if [ -f "test_emit.c" ]; then
    echo "✓ C code generated successfully"
    echo "---"
    cat test_emit.c
    echo "---"
else
    echo "✗ Failed to generate C code"
    exit 1
fi
echo ""

# Cleanup
echo "Cleaning up test artifacts..."
rm -f test_hello test_hello_class test_memory test_emit.c

echo ""
echo "========================================"
echo "All tests passed! ✓"
echo "========================================"
