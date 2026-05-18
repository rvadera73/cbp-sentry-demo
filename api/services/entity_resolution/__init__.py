"""Entity resolution service module"""

from .senzing_client import SenzingClient
from .service import EntityResolutionService
from .loader import load_manifest_entities
from .graph_builder import build_entity_graph
from .neo4j_sync import sync_to_neo4j

__all__ = [
    "SenzingClient",
    "EntityResolutionService",
    "load_manifest_entities",
    "build_entity_graph",
    "sync_to_neo4j"
]
