#!/usr/bin/env python
"""Check conftest.py for syntax errors"""
import sys
import py_compile

try:
    py_compile.compile('/home/rahulvadera/cbp-sentry/api/tests/conftest.py', doraise=True)
    print("✓ conftest.py has valid Python syntax")
except py_compile.PyCompileError as e:
    print(f"✗ conftest.py has syntax errors:")
    print(e)
    sys.exit(1)

# Try to import it
sys.path.insert(0, '/home/rahulvadera/cbp-sentry/api')
sys.path.insert(0, '/home/rahulvadera/cbp-sentry/api/tests')

try:
    import conftest
    print("✓ conftest.py can be imported")
except Exception as e:
    print(f"✗ conftest.py import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check fixtures exist
try:
    assert hasattr(conftest, 'greenfield_entities'), "greenfield_entities fixture missing"
    assert hasattr(conftest, 'mock_senzing'), "mock_senzing fixture missing"
    assert hasattr(conftest, 'mock_neo4j'), "mock_neo4j fixture missing"
    print("✓ All required fixtures exist")
except AssertionError as e:
    print(f"✗ {e}")
    sys.exit(1)

print("\n✓ conftest.py is valid")
