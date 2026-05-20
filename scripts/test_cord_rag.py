#!/usr/bin/env python3
"""
Test CORD RAG Database implementation.

Tests entity resolution, beneficial owner tracing, and sanctions screening.
Run this after building the CORD RAG database.
"""

import asyncio
import sys
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services"))

from entity_resolution.cord_rag import CORDRagDatabase


async def test_cord_rag():
    """Test CORD RAG functionality."""

    db_path = Path(__file__).parent.parent / "data" / "cord_rag.db"

    if not db_path.exists():
        print(f"❌ CORD RAG database not found at {db_path}")
        print(f"Run: python3 scripts/build_cord_rag_db.py")
        return False

    print("=" * 70)
    print("CORD RAG Database Test")
    print("=" * 70)

    cord_rag = CORDRagDatabase(str(db_path))

    # Get stats
    print("\n📊 Database Statistics")
    stats = await cord_rag.get_stats()
    print(f"   Total records: {stats['total_records']:,}")
    for source, count in stats['by_source'].items():
        print(f"   - {source}: {count:,}")
    if stats['sanctions_hits']:
        print(f"   Sanctions hits: {stats['sanctions_hits']}")

    # Test entity resolution
    print("\n🔍 Entity Resolution Tests")

    test_cases = [
        ("Greenfield Industrial Trading Co., Ltd.", "VN", "Expected: Found (CORD_LONDON)"),
        ("Solaria Manufacturing Sdn. Bhd.", "MY", "Expected: Found (CORD_LONDON)"),
        ("SunPath Energy Distributors LLC", "US", "Expected: Found (CORD_LASVEGAS)"),
        ("Nonexistent Corp XYZ", "ZZ", "Expected: Not found"),
    ]

    for entity_name, country, note in test_cases:
        result = await cord_rag.resolve_entity(entity_name, country)
        status = "✅ FOUND" if result["found"] else "❌ NOT FOUND"
        print(f"\n   {status}")
        print(f"   Query: {entity_name} ({country})")
        print(f"   {note}")
        if result["found"]:
            print(f"   Match type: {result['match_type']}")
            print(f"   Confidence: {result['confidence']:.0%}")
            print(f"   Source: {result['data_source']}")
            if result["entity_id"]:
                print(f"   ID: {result['entity_id']}")

    # Test beneficial owner tracing
    print("\n🔗 Beneficial Owner Tracing")

    trace_cases = [
        ("Greenfield Industrial Trading Co., Ltd.", "VN"),
        ("Solaria Manufacturing Sdn. Bhd.", "MY"),
    ]

    for entity_name, country in trace_cases:
        chain = await cord_rag.trace_beneficial_owner(entity_name, country, depth=3)
        print(f"\n   Chain for {entity_name} ({country})")
        if chain:
            for i, entity in enumerate(chain):
                indent = "   " * (i + 1)
                print(f"{indent}├─ {entity['entity_name']} ({entity['country']})")
                if entity["beneficial_owner"]:
                    print(f"{indent}│  Owner: {entity['beneficial_owner']}")
                print(f"{indent}│  Source: {entity['data_source']}")
        else:
            print(f"   No chain found")

    # Test sanctions screening
    print("\n⚖️  Sanctions Screening")

    sanctions_cases = [
        ("Greenfield Industrial Trading Co., Ltd.", "VN", "Expected: Clear"),
        ("Solaria Manufacturing Sdn. Bhd.", "MY", "Expected: Clear"),
    ]

    for entity_name, country, note in sanctions_cases:
        result = await cord_rag.search_sanctions(entity_name, country)
        print(f"\n   Query: {entity_name} ({country})")
        print(f"   {note}")
        print(f"   Status: {result['status']}")
        print(f"   Confidence: {result['confidence']:.0%}")

    print("\n" + "=" * 70)
    print("✅ CORD RAG Tests Complete")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = asyncio.run(test_cord_rag())
    sys.exit(0 if success else 1)
