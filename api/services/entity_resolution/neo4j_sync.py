"""
Neo4j sync — syncs entity graph to Neo4j database.

Creates Entity nodes and relationships with properties:
- node properties: entity_name, jurisdiction, risk_score, confidence
- relationship properties: relationship_type, confidence, evidence_fields
"""

import logging
from typing import Dict, List, Optional
import networkx as nx

logger = logging.getLogger(__name__)


def sync_to_neo4j(
    graph: nx.DiGraph,
    session=None
) -> Dict:
    """
    Sync entity graph to Neo4j.

    Args:
        graph: NetworkX DiGraph
        session: Neo4j session (optional)

    Returns:
        Dict with sync_status, nodes_created, relationships_created
    """
    if not session:
        logger.warning("No Neo4j session provided; skipping sync")
        return {
            "sync_status": "skipped",
            "nodes_created": 0,
            "relationships_created": 0
        }

    try:
        nodes_created = 0
        relationships_created = 0

        # Create nodes
        for node_id, attrs in graph.nodes(data=True):
            nodes_created += _create_node(session, node_id, attrs)

        # Create relationships
        for source, target, attrs in graph.edges(data=True):
            relationships_created += _create_relationship(
                session,
                source,
                target,
                attrs
            )

        logger.info(
            f"Neo4j sync complete: {nodes_created} nodes, "
            f"{relationships_created} relationships"
        )

        return {
            "sync_status": "success",
            "nodes_created": nodes_created,
            "relationships_created": relationships_created
        }

    except Exception as e:
        logger.error(f"Neo4j sync failed: {e}")
        return {
            "sync_status": "failed",
            "error": str(e),
            "nodes_created": 0,
            "relationships_created": 0
        }


def _create_node(session, node_id: str, attrs: Dict) -> int:
    """
    Create Entity node in Neo4j.

    Args:
        session: Neo4j session
        node_id: Node ID
        attrs: Node attributes

    Returns:
        Number of nodes created (1 or 0)
    """
    try:
        query = """
        MERGE (e:Entity {id: $id})
        SET e.name = $name,
            e.type = $type,
            e.country = $country,
            e.jurisdiction = $jurisdiction,
            e.risk_score = $risk_score,
            e.confidence = $confidence,
            e.senzing_record_id = $senzing_record_id,
            e.created_at = datetime()
        RETURN count(e)
        """

        params = {
            "id": str(node_id),
            "name": attrs.get("label", ""),
            "type": attrs.get("type", ""),
            "country": attrs.get("country", ""),
            "jurisdiction": attrs.get("jurisdiction", ""),
            "risk_score": float(attrs.get("risk_score", 0)),
            "confidence": float(attrs.get("confidence", 0.0)),
            "senzing_record_id": attrs.get("senzing_record_id", "")
        }

        result = session.run(query, params)
        if result and hasattr(result, "summary"):
            return result.summary.counters.nodes_created
        return 0

    except Exception as e:
        logger.error(f"Failed to create node {node_id}: {e}")
        return 0


def _create_relationship(
    session,
    source: str,
    target: str,
    attrs: Dict
) -> int:
    """
    Create relationship in Neo4j.

    Args:
        session: Neo4j session
        source: Source node ID
        target: Target node ID
        attrs: Relationship attributes

    Returns:
        Number of relationships created (1 or 0)
    """
    try:
        rel_type = attrs.get("relationship_type", "RELATED_TO").upper()

        query = f"""
        MATCH (a:Entity {{id: $source}})
        MATCH (b:Entity {{id: $target}})
        CREATE (a)-[r:{rel_type} {{
            confidence: $confidence,
            evidence: $evidence,
            created_at: datetime()
        }}]->(b)
        RETURN count(r)
        """

        params = {
            "source": str(source),
            "target": str(target),
            "confidence": float(attrs.get("confidence", 0.0)),
            "evidence": attrs.get("evidence", [])
        }

        result = session.run(query, params)
        if result and hasattr(result, "summary"):
            return result.summary.counters.relationships_created
        return 0

    except Exception as e:
        logger.error(f"Failed to create relationship {source}->{target}: {e}")
        return 0


def query_entity_by_id(session, entity_id: str) -> Optional[Dict]:
    """
    Query entity from Neo4j by ID.

    Args:
        session: Neo4j session
        entity_id: Entity ID

    Returns:
        Entity dict or None
    """
    try:
        query = """
        MATCH (e:Entity {id: $id})
        RETURN e
        LIMIT 1
        """

        result = session.run(query, {"id": entity_id})
        record = result.single()

        if record:
            node = record["e"]
            return {
                "id": node["id"],
                "name": node.get("name", ""),
                "type": node.get("type", ""),
                "country": node.get("country", ""),
                "jurisdiction": node.get("jurisdiction", ""),
                "risk_score": node.get("risk_score", 0),
                "confidence": node.get("confidence", 0.0)
            }
        return None

    except Exception as e:
        logger.error(f"Query failed for entity {entity_id}: {e}")
        return None


def query_related_entities(session, entity_id: str, depth: int = 1) -> List[Dict]:
    """
    Query entities related to a given entity in Neo4j.

    Args:
        session: Neo4j session
        entity_id: Center entity ID
        depth: Relationship depth (1-3)

    Returns:
        List of related entity dicts
    """
    try:
        query = f"""
        MATCH (e:Entity {{id: $id}})-[*1..{depth}]-(related:Entity)
        RETURN DISTINCT related
        """

        result = session.run(query, {"id": entity_id})
        related = []

        for record in result:
            node = record["related"]
            related.append({
                "id": node["id"],
                "name": node.get("name", ""),
                "type": node.get("type", ""),
                "country": node.get("country", ""),
                "risk_score": node.get("risk_score", 0)
            })

        return related

    except Exception as e:
        logger.error(f"Related entities query failed: {e}")
        return []


def query_shortest_path(
    session,
    source_id: str,
    target_id: str
) -> Optional[List[Dict]]:
    """
    Query shortest path between two entities in Neo4j.

    Args:
        session: Neo4j session
        source_id: Source entity ID
        target_id: Target entity ID

    Returns:
        List of node dicts along path, or None if no path
    """
    try:
        query = """
        MATCH p = shortestPath((source:Entity {id: $source})-[*]-(target:Entity {id: $target}))
        RETURN [node IN nodes(p) | {id: node.id, name: node.name, type: node.type}] as path
        """

        result = session.run(query, {
            "source": source_id,
            "target": target_id
        })

        record = result.single()
        if record:
            return record["path"]
        return None

    except Exception as e:
        logger.error(f"Shortest path query failed: {e}")
        return None


def query_by_risk_score(
    session,
    min_score: float = 50,
    max_score: float = 100
) -> List[Dict]:
    """
    Query entities by risk score range in Neo4j.

    Args:
        session: Neo4j session
        min_score: Minimum risk score
        max_score: Maximum risk score

    Returns:
        List of entity dicts
    """
    try:
        query = """
        MATCH (e:Entity)
        WHERE e.risk_score >= $min AND e.risk_score <= $max
        RETURN e
        ORDER BY e.risk_score DESC
        """

        result = session.run(query, {"min": min_score, "max": max_score})
        entities = []

        for record in result:
            node = record["e"]
            entities.append({
                "id": node["id"],
                "name": node.get("name", ""),
                "type": node.get("type", ""),
                "country": node.get("country", ""),
                "risk_score": node.get("risk_score", 0),
                "confidence": node.get("confidence", 0.0)
            })

        return entities

    except Exception as e:
        logger.error(f"Risk score query failed: {e}")
        return []
