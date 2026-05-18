"""
Database initialization and connection management
"""
import aiosqlite
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global database connection
_db_connection: Optional[aiosqlite.Connection] = None


async def init_db():
    """Initialize database and create schema"""
    global _db_connection
    
    from core.config import settings
    
    try:
        logger.info(f"Initializing database: {settings.database_url}")
        
        # SQLite for local development
        if "sqlite" in settings.database_url:
            db_path = settings.database_url.replace("sqlite:///", "")
            _db_connection = await aiosqlite.connect(db_path)
            await _db_connection.enable_load_extension(False)
            logger.info("SQLite database connected")
        else:
            logger.warning("Non-SQLite database URL provided; schema initialization deferred")
        
        # Create tables (placeholder)
        if _db_connection:
            await create_schema()
    
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def create_schema():
    """Create database schema"""
    if not _db_connection:
        return

    try:
        # Manifest table
        await _db_connection.execute("""
            CREATE TABLE IF NOT EXISTS manifests (
                id TEXT PRIMARY KEY,
                uploaded_at TIMESTAMP,
                shipper TEXT,
                consignee TEXT,
                hts_code TEXT,
                total_weight_kg REAL,
                total_value_usd REAL,
                row_count INTEGER,
                flag_suspicious BOOLEAN
            )
        """)

        # Manifest rows table
        await _db_connection.execute("""
            CREATE TABLE IF NOT EXISTS manifest_rows (
                id TEXT PRIMARY KEY,
                manifest_id TEXT REFERENCES manifests(id),
                shipper TEXT,
                consignee TEXT,
                hts_code TEXT,
                quantity_kg REAL,
                value_usd REAL,
                description TEXT,
                flag_suspicious BOOLEAN
            )
        """)

        # Legacy manifest_ingests table (for backward compatibility)
        await _db_connection.execute("""
            CREATE TABLE IF NOT EXISTS manifest_ingests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                record_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Records table
        await _db_connection.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT NOT NULL,
                record_number INTEGER,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manifest_id) REFERENCES manifest_ingests(manifest_id)
            )
        """)
        
        # Entity resolution results
        await _db_connection.execute("""
            CREATE TABLE IF NOT EXISTS entity_resolutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                entity_type TEXT,
                confidence REAL,
                resolved_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (record_id) REFERENCES records(id)
            )
        """)
        
        # Scores
        await _db_connection.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                risk_score REAL,
                threat_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entity_resolutions(id)
            )
        """)
        
        await _db_connection.commit()
        logger.info("Database schema initialized")
    
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        raise


async def get_db() -> aiosqlite.Connection:
    """Get database connection"""
    global _db_connection
    if _db_connection is None:
        raise RuntimeError("Database not initialized")
    return _db_connection


async def close_db():
    """Close database connection"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("Database connection closed")
