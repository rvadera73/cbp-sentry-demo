"""WSGI entry point for precise-risk-engine-api."""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from app import create_app

# Load environment variables
load_dotenv()

# Create Flask app
app = create_app(os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8004))
    app.run(host="0.0.0.0", port=port, debug=False)
