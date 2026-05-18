#!/usr/bin/env python
"""Run entity resolution tests"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest",
     "api/tests/test_entity_resolution.py",
     "-v", "--tb=short"],
    cwd="/home/rahulvadera/cbp-sentry"
)
sys.exit(result.returncode)
