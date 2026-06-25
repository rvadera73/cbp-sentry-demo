"""Services for precise-risk-engine-api."""
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy

cache = Cache()
db = SQLAlchemy()

__all__ = ["cache", "db"]
