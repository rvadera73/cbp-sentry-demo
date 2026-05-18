"""Root conftest for pytest — sets up PYTHONPATH"""
import sys
from pathlib import Path

# Add api/ to sys.path so imports like "from main import app" work
api_path = Path(__file__).parent / "api"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))
