#!/usr/bin/env python3
"""
Build CORD RAG Database from individual source JSONL files.

Processes granular CORD source files (GLEIF, ICIJ, OFAC, etc.) organized by geography
and consolidates them into a unified SQLite RAG database with smart field extraction.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Set, Any
from collections import defaultdict

# Map source file patterns to CORD geography
SOURCE_TO_GEOGRAPHY = {
    "gleif-london": "CORD_LONDON",
    "gleif-moscow": "CORD_MOSCOW",
    "gleif-lasvegas": "CORD_LASVEGAS",
    "globaldata-london": "CORD_LONDON",
    "icij-london": "CORD_LONDON",
    "icij-moscow": "CORD_MOSCOW",
    "ofac-london": "CORD_LONDON",
    "ofac-moscow": "CORD_MOSCOW",
    "open_sanctions-london": "CORD_LONDON",
    "open_sanctions-moscow": "CORD_MOSCOW",
    "open_ownership-moscow": "CORD_MOSCOW",
    "open_ownership-lasvegas": "CORD_LASVEGAS",
    "nominodata_combined-lasvegas": "CORD_LASVEGAS",
    "nominodata_risk-moscow": "CORD_MOSCOW",
    "npi-lasvegas": "CORD_LASVEGAS",
    "ppp_loans_over_150k-lasvegas": "CORD_LASVEGAS",
    "us_labor_violations-lasvegas": "CORD_LASVEGAS",
}

DB_PATH = Path("data/cord_rag.db")
CORD_DATA_DIR = Path("cord-data")


def get_geography_from_filename(filename: str) -> str:
    """Determine CORD geography (LONDON, MOSCOW, LASVEGAS) from filename."""
    for pattern, geography in SOURCE_TO_GEOGRAPHY.items():
        if pattern in filename:
            return geography
    return None


def extract_entity_fields(record: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract entity fields from various CORD source formats.

    Handles:
    - GLEIF format: nested NAMES, ADDRESSES, DATES, IDENTIFIERS
    - ICIJ format: flat fields
    - OFAC format: flat fields
    - OpenSanctions format: nested structures
    """

    fields = {
        "entity_id": "",
        "entity_name": "",
        "country": "",
        "incorporation_date": "",
        "beneficial_owner": "",
        "parent_company": "",
        "parent_country": "",
        "gleif_id": "",
        "sanctions_status": "CLEAR",
    }

    # Handle GLEIF/nested format
    if "RECORD_ID" in record:
        fields["entity_id"] = record.get("RECORD_ID", "")

        # Extract name from nested NAMES array
        if "NAMES" in record and isinstance(record["NAMES"], list) and len(record["NAMES"]) > 0:
            fields["entity_name"] = record["NAMES"][0].get("NAME_ORG") or record["NAMES"][0].get("NAME")

        # Extract country from COUNTRIES array
        if "COUNTRIES" in record and isinstance(record["COUNTRIES"], list) and len(record["COUNTRIES"]) > 0:
            country_code = record["COUNTRIES"][0].get("REGISTRATION_COUNTRY", "")
            fields["country"] = country_code.upper() if country_code else ""

        # Extract registration date from DATES array
        if "DATES" in record and isinstance(record["DATES"], list) and len(record["DATES"]) > 0:
            fields["incorporation_date"] = record["DATES"][0].get("REGISTRATION_DATE", "")

        # Extract LEI from IDENTIFIERS
        if "IDENTIFIERS" in record and isinstance(record["IDENTIFIERS"], list):
            for identifier in record["IDENTIFIERS"]:
                if identifier.get("LEI_NUMBER"):
                    fields["gleif_id"] = identifier.get("LEI_NUMBER")
                    break

        # Check for sanctions in DATA_SOURCE or URL
        if "open_sanctions" in record.get("URL", "").lower():
            fields["sanctions_status"] = "OPENSANCTIONS_HIT"

    # Handle flat format (ICIJ, OFAC, etc.)
    else:
        # Try common field names
        fields["entity_id"] = (
            record.get("id") or
            record.get("ID") or
            record.get("entity_id") or
            record.get("RECORD_ID") or
            ""
        )

        fields["entity_name"] = (
            record.get("name") or
            record.get("NAME") or
            record.get("entity_name") or
            record.get("company_name") or
            record.get("display_name") or
            ""
        )

        fields["country"] = (
            record.get("country") or
            record.get("COUNTRY") or
            record.get("jurisdiction") or
            record.get("jurisdiction_code") or
            ""
        )

        fields["incorporation_date"] = (
            record.get("incorporation_date") or
            record.get("date_founded") or
            record.get("founded_date") or
            record.get("REGISTRATION_DATE") or
            ""
        )

        fields["beneficial_owner"] = (
            record.get("beneficial_owner") or
            record.get("BENEFICIAL_OWNER") or
            record.get("officer") or
            ""
        )

        fields["parent_company"] = (
            record.get("parent_company") or
            record.get("PARENT_COMPANY") or
            record.get("parent") or
            ""
        )

        fields["gleif_id"] = (
            record.get("gleif_id") or
            record.get("lei") or
            record.get("LEI_NUMBER") or
            ""
        )

        # Check sanctions flags
        if record.get("ofac_hit") or record.get("OFAC_HIT") or record.get("is_sanctioned"):
            fields["sanctions_status"] = "OFAC_HIT"
        elif record.get("opensanctions_hit") or record.get("OPENSANCTIONS_HIT"):
            fields["sanctions_status"] = "OPENSANCTIONS_HIT"

    return fields


def build_cord_rag_database():
    """Build indexed SQLite database from individual CORD source files."""

    # Create database
    db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        print(f"⚠️  Database exists: {db_path}")
        print("   Removing old database...")
        db_path.unlink()

    print(f"\n🏗️  Building CORD RAG database from source files...")
    print(f"   Source: {CORD_DATA_DIR}")
    print(f"   Database: {db_path}\n")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Create schema
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY,
            entity_name TEXT NOT NULL,
            country TEXT,
            incorporation_date TEXT,
            beneficial_owner TEXT,
            parent_company TEXT,
            parent_country TEXT,
            data_source TEXT,
            gleif_id TEXT,
            sanctions_status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes
    print("📑 Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_name_country ON entities(entity_name, country)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_beneficial_owner ON entities(beneficial_owner)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_parent_company ON entities(parent_company, parent_country)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_source ON entities(data_source)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sanctions ON entities(sanctions_status)")
    conn.commit()

    # Find all JSONL files
    jsonl_files = list(CORD_DATA_DIR.glob("*.jsonl"))
    if not jsonl_files:
        print(f"❌ No JSONL files found in {CORD_DATA_DIR}")
        return False

    print(f"📊 Found {len(jsonl_files)} source files\n")

    # Group files by geography
    files_by_geography: Dict[str, list] = defaultdict(list)
    for file_path in jsonl_files:
        filename = file_path.name
        geography = get_geography_from_filename(filename)
        if geography:
            files_by_geography[geography].append(file_path)
            print(f"   ✓ {filename:50s} → {geography}")
        else:
            print(f"   ⚠️  {filename:50s} → UNKNOWN (skipping)")

    print()

    # Process files by geography
    total_records = 0
    processed_entities: Set[str] = set()

    for geography in ["CORD_LONDON", "CORD_MOSCOW", "CORD_LASVEGAS"]:
        if geography not in files_by_geography:
            print(f"⚠️  No files for {geography}, skipping")
            continue

        print(f"📦 Processing {geography}...")
        geography_records = 0
        geography_skipped = 0

        for file_path in sorted(files_by_geography[geography]):
            collection_records = 0

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():
                            continue

                        try:
                            record = json.loads(line)

                            # Extract fields intelligently
                            fields = extract_entity_fields(record)

                            entity_id = fields["entity_id"]
                            entity_name = fields["entity_name"]

                            # Skip invalid records
                            if not entity_id or not entity_name:
                                geography_skipped += 1
                                continue

                            # Skip if already processed (deduplication)
                            if entity_id in processed_entities:
                                continue

                            # Insert record
                            cur.execute(
                                """
                                INSERT OR IGNORE INTO entities
                                (entity_id, entity_name, country, incorporation_date,
                                 beneficial_owner, parent_company, parent_country,
                                 data_source, gleif_id, sanctions_status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    entity_id,
                                    entity_name,
                                    fields["country"],
                                    fields["incorporation_date"],
                                    fields["beneficial_owner"],
                                    fields["parent_company"],
                                    fields["parent_country"],
                                    geography,
                                    fields["gleif_id"],
                                    fields["sanctions_status"],
                                ),
                            )

                            processed_entities.add(entity_id)
                            collection_records += 1
                            geography_records += 1
                            total_records += 1

                            # Batch commit every 10k records
                            if collection_records % 10000 == 0:
                                conn.commit()
                                print(f"  ✓ {file_path.name:45s}: {geography_records:,} entities loaded")

                        except (json.JSONDecodeError, KeyError, TypeError) as e:
                            continue

            except Exception as e:
                print(f"  ⚠️  Error processing {file_path.name}: {e}")
                continue

        conn.commit()
        print(f"✅ {geography:20s}: {geography_records:,} unique entities loaded\n")

    # Final commit
    conn.commit()
    conn.close()

    # Verify database
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM entities")
    final_count = cur.fetchone()[0]

    cur.execute("SELECT data_source, COUNT(*) as count FROM entities GROUP BY data_source")
    by_source = cur.fetchall()

    cur.execute("SELECT sanctions_status, COUNT(*) as count FROM entities WHERE sanctions_status != 'CLEAR' GROUP BY sanctions_status")
    sanctions_hits = cur.fetchall()

    conn.close()

    print("=" * 70)
    print("✅ CORD RAG Database built successfully!")
    print("=" * 70)
    print(f"Database path: {db_path}")
    print(f"Total unique entities: {final_count:,}")
    print(f"\nDistribution by CORD geography:")
    for source, count in by_source:
        print(f"  - {source:20s}: {count:,}")

    if sanctions_hits:
        print(f"\nSanctions hits:")
        for status, count in sanctions_hits:
            print(f"  - {status:20s}: {count:,}")

    print("\n" + "=" * 70)
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("CORD RAG Database Builder (from source files)")
    print("=" * 70)

    success = build_cord_rag_database()
    sys.exit(0 if success else 1)
