#!/bin/bash
cd /home/rahulvadera/cbp-sentry
python -m pytest api/tests/test_entity_resolution.py -v --tb=short 2>&1
