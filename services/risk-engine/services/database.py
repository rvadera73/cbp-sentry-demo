"""Database service utilities for risk scoring."""
import logging
from sqlalchemy import text
from . import db

logger = logging.getLogger(__name__)


def test_connection():
    """Test database connection."""
    try:
        result = db.session.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def init_schema():
    """Initialize risk_scoring schema if it doesn't exist."""
    try:
        db.session.execute(text("""
            CREATE SCHEMA IF NOT EXISTS risk_scoring;
        """))
        db.session.commit()
        logger.info("risk_scoring schema initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize schema: {e}")
        db.session.rollback()
        return False


def create_all_tables():
    """Create all database tables."""
    try:
        db.create_all()
        logger.info("Database tables created")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False
