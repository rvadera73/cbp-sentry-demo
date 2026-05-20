"""
CORD RAG Service — Automated CORD data management and entity investigation.

This service provides:
1. Automated CORD download (London, Moscow)
2. CORD data loading into Senzing
3. RAG agent for semantic entity queries
4. MCP service for programmatic access
"""

from .agent import CORDRAGAgent
from .cord_downloader import CORDDownloader

__all__ = [
    "CORDRAGAgent",
    "CORDDownloader"
]
