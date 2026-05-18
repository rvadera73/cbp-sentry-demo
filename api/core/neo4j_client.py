"""Neo4j database client and initialization"""

from neo4j import AsyncDriver, AsyncSession
from neo4j import aio
import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)

_neo4j_driver: Optional[AsyncDriver] = None

async def init_neo4j():
    """Initialize Neo4j connection"""
    global _neo4j_driver
    try:
        if settings.neo4j_uri is None:
            logger.warning("NEO4J_URI not set — Neo4j features will be disabled")
            return

        _neo4j_driver = aio.AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password) if settings.neo4j_user else None,
        )

        # Test connection
        async with _neo4j_driver.session() as session:
            await session.run("RETURN 1")

        logger.info(f"Neo4j connected: {settings.neo4j_uri}")
    except Exception as e:
        logger.warning(f"Failed to initialize Neo4j: {e}")
        _neo4j_driver = None

def get_neo4j_driver() -> Optional[AsyncDriver]:
    """Get the Neo4j driver instance"""
    return _neo4j_driver

async def neo4j_available() -> bool:
    """Check if Neo4j is available"""
    return _neo4j_driver is not None

async def create_graph_indices():
    """Create necessary Neo4j indices"""
    if not _neo4j_driver:
        return

    async with _neo4j_driver.session() as session:
        # Entity nodes
        await session.run("""
            CREATE INDEX entity_id IF NOT EXISTS
            FOR (n:Entity) ON (n.id)
        """)

        # Shipment nodes
        await session.run("""
            CREATE INDEX shipment_bill_id IF NOT EXISTS
            FOR (n:Shipment) ON (n.bill_id)
        """)

        # HTS nodes
        await session.run("""
            CREATE INDEX hts_code IF NOT EXISTS
            FOR (n:HTS) ON (n.code)
        """)

        logger.info("Neo4j indices created")
