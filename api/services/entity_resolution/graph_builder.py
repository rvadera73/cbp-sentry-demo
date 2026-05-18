"""
Entity graph builder — constructs NetworkX graph from entities and relationships.

Builds directed graph with:
- 7 nodes: shipper, manufacturer, consignee, holding_company, vessel, forwarder, terminal
- Edges: OWNED_BY, DIRECTOR_SHARED, PRIOR_FILING, VESSEL_CARRIED, FREIGHT_FORWARDED_BY
- Metadata: risk_score, jurisdiction, confidence
"""

import logging
from typing import Dict, List
import networkx as nx

logger = logging.getLogger(__name__)


def build_entity_graph(
    entities: List[Dict],
    relationships: List[Dict]
) -> nx.DiGraph:
    """
    Build NetworkX directed graph from entities and relationships.

    Args:
        entities: List of entity dicts with id, name, type, etc.
        relationships: List of relationship dicts with source, target, type

    Returns:
        NetworkX DiGraph with nodes and edges
    """
    graph = nx.DiGraph()

    # Add nodes
    for entity in entities:
        entity_id = entity.get("entity_id", "")
        if not entity_id:
            continue

        graph.add_node(
            entity_id,
            label=entity.get("entity_name", ""),
            type=entity.get("entity_type", ""),
            country=entity.get("country", ""),
            jurisdiction=entity.get("jurisdiction", ""),
            risk_score=entity.get("risk_score", 0),
            confidence=entity.get("confidence", 0.0),
            senzing_record_id=entity.get("senzing_record_id", ""),
            metadata=entity.get("metadata", {})
        )

    # Add edges
    for relationship in relationships:
        source = relationship.get("source", "")
        target = relationship.get("target", "")
        rel_type = relationship.get("relationship_type", "")

        if not source or not target:
            continue

        graph.add_edge(
            source,
            target,
            relationship_type=rel_type,
            confidence=relationship.get("confidence", 0.0),
            evidence=relationship.get("evidence", [])
        )

    logger.info(
        f"Built entity graph: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges"
    )

    return graph


def get_graph_nodes(graph: nx.DiGraph) -> List[Dict]:
    """
    Convert graph nodes to serializable format.

    Args:
        graph: NetworkX DiGraph

    Returns:
        List of node dicts with id, label, type, properties
    """
    nodes = []
    for node_id, attrs in graph.nodes(data=True):
        nodes.append({
            "id": str(node_id),
            "label": attrs.get("label", ""),
            "type": attrs.get("type", ""),
            "properties": {
                "country": attrs.get("country", ""),
                "jurisdiction": attrs.get("jurisdiction", ""),
                "risk_score": attrs.get("risk_score", 0),
                "confidence": attrs.get("confidence", 0.0),
                "senzing_record_id": attrs.get("senzing_record_id", ""),
                "metadata": attrs.get("metadata", {})
            }
        })
    return nodes


def get_graph_edges(graph: nx.DiGraph) -> List[Dict]:
    """
    Convert graph edges to serializable format.

    Args:
        graph: NetworkX DiGraph

    Returns:
        List of edge dicts with source, target, relationship_type, properties
    """
    edges = []
    for source, target, attrs in graph.edges(data=True):
        edges.append({
            "source": str(source),
            "target": str(target),
            "relationship_type": attrs.get("relationship_type", ""),
            "properties": {
                "confidence": attrs.get("confidence", 0.0),
                "evidence": attrs.get("evidence", [])
            }
        })
    return edges


def get_subgraph(
    graph: nx.DiGraph,
    center_node: str,
    hops: int = 2
) -> nx.DiGraph:
    """
    Get subgraph around a center node.

    Args:
        graph: NetworkX DiGraph
        center_node: Center node ID
        hops: Number of hops (distance) to include

    Returns:
        Subgraph as DiGraph
    """
    if center_node not in graph:
        return nx.DiGraph()

    # Get nodes within hops distance
    subgraph_nodes = {center_node}

    for _ in range(hops):
        new_nodes = set()
        for node in subgraph_nodes:
            # Add successors and predecessors
            new_nodes.update(graph.successors(node))
            new_nodes.update(graph.predecessors(node))
        subgraph_nodes.update(new_nodes)

    return graph.subgraph(subgraph_nodes).copy()


def find_shortest_path(
    graph: nx.DiGraph,
    source: str,
    target: str
) -> List[str]:
    """
    Find shortest path between two nodes.

    Args:
        graph: NetworkX DiGraph
        source: Source node ID
        target: Target node ID

    Returns:
        List of node IDs in path (empty if no path)
    """
    try:
        return nx.shortest_path(graph, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def find_all_paths(
    graph: nx.DiGraph,
    source: str,
    target: str,
    max_length: int = 4
) -> List[List[str]]:
    """
    Find all paths between two nodes up to max length.

    Args:
        graph: NetworkX DiGraph
        source: Source node ID
        target: Target node ID
        max_length: Maximum path length

    Returns:
        List of paths (each path is list of node IDs)
    """
    try:
        return list(nx.all_simple_paths(graph, source, target, cutoff=max_length))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def calculate_centrality(graph: nx.DiGraph) -> Dict[str, float]:
    """
    Calculate centrality scores for all nodes.

    Args:
        graph: NetworkX DiGraph

    Returns:
        Dict mapping node ID to centrality score
    """
    try:
        return nx.betweenness_centrality(graph)
    except Exception as e:
        logger.warning(f"Centrality calculation failed: {e}")
        return {}
