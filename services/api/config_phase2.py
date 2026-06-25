"""
Phase 2 Configuration - Feature Flag & Precise Risk Engine Integration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Feature flag for gradual rollout
USE_PRECISE_RISK_MODEL = os.getenv('USE_PRECISE_RISK_MODEL', 'false').lower() == 'true'

# Precise Risk Engine Configuration
PRECISE_RISK_ENGINE_URL = os.getenv(
    'PRECISE_RISK_ENGINE_URL',
    'http://localhost:8004'
)
PRECISE_RISK_ENGINE_TIMEOUT = int(os.getenv('PRECISE_RISK_ENGINE_TIMEOUT', 5))

# Traffic ramping percentage (for monitoring)
TRAFFIC_PERCENTAGE = int(os.getenv('TRAFFIC_PERCENTAGE', 0))

# Logging
ENABLE_MODEL_COMPARISON_LOGGING = os.getenv('ENABLE_MODEL_COMPARISON_LOGGING', 'true').lower() == 'true'

print(f"""
╔═══════════════════════════════════════════════════════════╗
║          PHASE 2 CONFIGURATION LOADED                     ║
╚═══════════════════════════════════════════════════════════╝
USE_PRECISE_RISK_MODEL:      {USE_PRECISE_RISK_MODEL}
PRECISE_RISK_ENGINE_URL:     {PRECISE_RISK_ENGINE_URL}
PRECISE_RISK_ENGINE_TIMEOUT: {PRECISE_RISK_ENGINE_TIMEOUT}s
TRAFFIC_PERCENTAGE:          {TRAFFIC_PERCENTAGE}%
COMPARISON_LOGGING:          {ENABLE_MODEL_COMPARISON_LOGGING}
""")
