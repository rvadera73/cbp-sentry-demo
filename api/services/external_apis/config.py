"""
External API configuration — toggle between live and fixture modes
"""
import os
from typing import Literal

# API Mode: 'live' uses real APIs, 'fixture' uses mock data
API_MODE = os.getenv("API_MODE", "live").lower()  # Default to live

# Individual API toggles (can override global mode)
API_SETTINGS = {
    "opencorporates": {
        "mode": os.getenv("OPENCORPORATES_MODE", API_MODE),
        "api_key": os.getenv("OPENCORPORATES_API_KEY"),  # Get from .env
        "enabled": os.getenv("OPENCORPORATES_ENABLED", "true").lower() == "true",
    },
    "comtrade": {
        "mode": os.getenv("COMTRADE_MODE", API_MODE),
        "enabled": os.getenv("COMTRADE_ENABLED", "true").lower() == "true",
    },
    "itc_tariffs": {
        "mode": os.getenv("ITC_MODE", API_MODE),
        "enabled": os.getenv("ITC_ENABLED", "true").lower() == "true",
    },
    "ais": {
        "mode": os.getenv("AIS_MODE", API_MODE),
        "api_key": os.getenv("AIS_API_KEY"),  # MarineTraffic or AIS Hub key
        "enabled": os.getenv("AIS_ENABLED", "true").lower() == "true",
    },
    "port_authority": {
        "mode": os.getenv("PORT_API_MODE", API_MODE),
        "enabled": os.getenv("PORT_API_ENABLED", "true").lower() == "true",
    },
}


def get_api_mode(api_name: str) -> Literal["live", "fixture"]:
    """Get the mode (live or fixture) for a specific API"""
    settings = API_SETTINGS.get(api_name, {})
    mode = settings.get("mode", "live")
    return mode if mode in ["live", "fixture"] else "live"


def is_api_enabled(api_name: str) -> bool:
    """Check if an API is enabled"""
    settings = API_SETTINGS.get(api_name, {})
    return settings.get("enabled", False)


def get_api_key(api_name: str) -> str | None:
    """Get API key for a service"""
    settings = API_SETTINGS.get(api_name, {})
    return settings.get("api_key")
