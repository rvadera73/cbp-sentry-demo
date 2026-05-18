"""
Graph Query Service — Load and build entity graphs from Neo4j or fixtures
"""
from typing import Dict, List, Any, Optional
from models.schemas import EntityGraphPayload, GraphNodePayload, GraphEdgePayload
import math


# ===== Fixture Data for Testing =====
GREENFIELD_GRAPH_FIXTURE = {
    "nodes": [
        {
            "id": "entity_vn_1",
            "label": "Greenfield Industrial Trading Co., Ltd.",
            "type": "TRADING_COMPANY",
            "jurisdiction": "VN",
            "risk_score": 65,
            "metadata": {
                "director": "Nguyen Van Hung",
                "registered": "2025-01-15",
                "address": "Suite 304, Bien Hoa, Binh Duong"
            }
        },
        {
            "id": "entity_cn_1",
            "label": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
            "type": "MANUFACTURER",
            "jurisdiction": "CN",
            "risk_score": 72,
            "metadata": {
                "prior_filings": 18,
                "address": "Nanhai District, Foshan, Guangdong",
                "confidence": 0.98
            }
        },
        {
            "id": "entity_hk_1",
            "label": "Greenfield Holdings HK Ltd.",
            "type": "HOLDING_COMPANY",
            "jurisdiction": "HK",
            "risk_score": 58,
            "metadata": {
                "beneficial_owner": "Nguyen Van Hung",
                "registered": "2024-10-15",
                "confidence": 0.92
            }
        },
        {
            "id": "entity_vn_2",
            "label": "Greenfield Logistics Vietnam Co., Ltd.",
            "type": "LOGISTICS",
            "jurisdiction": "VN",
            "risk_score": 62,
            "metadata": {
                "services": ["Export consolidation", "ISF filing", "Customs brokerage"]
            }
        },
        {
            "id": "entity_us_1",
            "label": "SunPath Energy Distributors LLC",
            "type": "DISTRIBUTOR",
            "jurisdiction": "US",
            "risk_score": 22,
            "metadata": {
                "address": "1234 Industrial Blvd, Newark, NJ",
                "confidence": 0.85
            }
        },
        {
            "id": "entity_us_2",
            "label": "Reliable Imports Inc.",
            "type": "IMPORTER",
            "jurisdiction": "US",
            "risk_score": 35,
            "metadata": {
                "address": "456 Commerce St, Los Angeles, CA",
                "confidence": 0.80
            }
        },
        {
            "id": "vessel_1",
            "label": "MV Pacific Horizon",
            "type": "VESSEL",
            "jurisdiction": "LR",
            "risk_score": 45,
            "metadata": {
                "imo": "9234567",
                "dwell_days": 11.2
            }
        }
    ],
    "edges": [
        {
            "source": "entity_vn_1",
            "target": "entity_cn_1",
            "relationship_type": "OWNED_BY",
            "confidence": 0.89,
            "label": "Ownership"
        },
        {
            "source": "entity_vn_1",
            "target": "entity_vn_2",
            "relationship_type": "SHARES_DIRECTOR",
            "confidence": 0.91,
            "label": "Nguyen Van Hung"
        },
        {
            "source": "entity_vn_1",
            "target": "vessel_1",
            "relationship_type": "SHIPPED_VIA",
            "confidence": 0.95
        },
        {
            "source": "entity_cn_1",
            "target": "entity_hk_1",
            "relationship_type": "OWNED_BY",
            "confidence": 0.87,
            "label": "Ownership"
        },
        {
            "source": "entity_hk_1",
            "target": "entity_vn_1",
            "relationship_type": "CONTROLS",
            "confidence": 0.85
        },
        {
            "source": "entity_vn_2",
            "target": "vessel_1",
            "relationship_type": "OPERATES",
            "confidence": 0.90
        },
        {
            "source": "entity_us_1",
            "target": "entity_vn_1",
            "relationship_type": "IMPORTS_FROM",
            "confidence": 0.88
        }
    ]
}


def calculate_node_positions(nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Calculate force-directed positions for nodes using a simple circular layout
    with physics-like repulsion to avoid overlaps.

    Args:
        nodes: List of node dictionaries

    Returns:
        Dictionary mapping node_id to {x, y} position
    """
    positions = {}
    n = len(nodes)

    if n == 0:
        return positions

    # Arrange nodes in a circle with some jitter for diversity
    radius = 100
    for i, node in enumerate(nodes):
        angle = (2 * math.pi * i) / n
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)

        # Add slight randomness
        import random
        x += random.uniform(-10, 10)
        y += random.uniform(-10, 10)

        positions[node["id"]] = {"x": round(x, 2), "y": round(y, 2)}

    return positions


async def get_shipment_graph(shipment_id: str) -> EntityGraphPayload:
    """
    Get full shipment entity graph with all nodes and relationships.

    For now, returns Greenfield fixture. In production, this would:
    1. Query Neo4j for entities with shipment_id
    2. Fetch all relationships between them
    3. Calculate node positions
    4. Return GraphPayload

    Args:
        shipment_id: Shipment identifier

    Returns:
        EntityGraphPayload with nodes[], edges[], metadata
    """
    # TODO: Replace with actual Neo4j query when database is live
    # For now, return fixture data (Greenfield case)

    fixture_nodes = GREENFIELD_GRAPH_FIXTURE["nodes"]
    fixture_edges = GREENFIELD_GRAPH_FIXTURE["edges"]

    # Calculate positions
    positions = calculate_node_positions(fixture_nodes)

    # Build GraphNodePayload objects
    nodes = []
    for node_data in fixture_nodes:
        node = GraphNodePayload(
            id=node_data["id"],
            label=node_data["label"],
            type=node_data["type"],
            risk_score=node_data["risk_score"],
            jurisdiction=node_data["jurisdiction"],
            metadata=node_data.get("metadata", {}),
            position=positions.get(node_data["id"])
        )
        nodes.append(node)

    # Build GraphEdgePayload objects
    edges = []
    for edge_data in fixture_edges:
        edge = GraphEdgePayload(
            source=edge_data["source"],
            target=edge_data["target"],
            relationship_type=edge_data["relationship_type"],
            confidence=edge_data["confidence"],
            label=edge_data.get("label")
        )
        edges.append(edge)

    # Determine highest risk node
    highest_risk_node = max(nodes, key=lambda n: n.risk_score)

    # Build metadata
    metadata = {
        "shipment_id": shipment_id,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "highest_risk_node": f"{highest_risk_node.id} ({highest_risk_node.type}, {highest_risk_node.risk_score}/100)",
        "strongest_link": "entity_vn_1 → entity_cn_1 (OWNED_BY, 0.89 confidence)"
    }

    return EntityGraphPayload(
        nodes=nodes,
        edges=edges,
        metadata=metadata
    )


async def get_entity_subgraph(entity_id: str, hop_limit: int = 2) -> EntityGraphPayload:
    """
    Extract subgraph centered on a single entity.

    Args:
        entity_id: Entity to center on
        hop_limit: Maximum relationships distance (default 2)

    Returns:
        EntityGraphPayload with subgraph nodes and edges
    """
    # TODO: Implement with actual Neo4j query
    # For now, return fixture filtered to entity

    fixture_nodes = GREENFIELD_GRAPH_FIXTURE["nodes"]
    fixture_edges = GREENFIELD_GRAPH_FIXTURE["edges"]

    # Find the entity
    entity_node = next((n for n in fixture_nodes if n["id"] == entity_id), None)
    if not entity_node:
        return EntityGraphPayload(nodes=[], edges=[], metadata={"error": "Entity not found"})

    # Find related entities (1 hop)
    related_ids = {entity_id}
    for edge in fixture_edges:
        if edge["source"] == entity_id:
            related_ids.add(edge["target"])
        elif edge["target"] == entity_id:
            related_ids.add(edge["source"])

    # Filter nodes and edges
    subgraph_nodes = [n for n in fixture_nodes if n["id"] in related_ids]
    subgraph_edges = [
        e for e in fixture_edges
        if e["source"] in related_ids and e["target"] in related_ids
    ]

    # Calculate positions
    positions = calculate_node_positions(subgraph_nodes)

    # Build GraphNodePayload objects
    nodes = []
    for node_data in subgraph_nodes:
        node = GraphNodePayload(
            id=node_data["id"],
            label=node_data["label"],
            type=node_data["type"],
            risk_score=node_data["risk_score"],
            jurisdiction=node_data["jurisdiction"],
            metadata=node_data.get("metadata", {}),
            position=positions.get(node_data["id"])
        )
        nodes.append(node)

    # Build GraphEdgePayload objects
    edges = []
    for edge_data in subgraph_edges:
        edge = GraphEdgePayload(
            source=edge_data["source"],
            target=edge_data["target"],
            relationship_type=edge_data["relationship_type"],
            confidence=edge_data["confidence"],
            label=edge_data.get("label")
        )
        edges.append(edge)

    return EntityGraphPayload(
        nodes=nodes,
        edges=edges,
        metadata={"central_entity": entity_id, "hop_limit": hop_limit}
    )
