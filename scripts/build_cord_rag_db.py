#!/usr/bin/env python3
"""
Build CORD RAG Database from Senzing Ready Data Collections.

Downloads and processes 21M entity records from:
- CORD_LONDON (10M+ international entities)
- CORD_MOSCOW (6M+ Russian/CIS entities)
- CORD_LASVEGAS (5M+ US importers/consignees)

Creates indexed SQLite database at data/cord_rag.db for fast entity resolution.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional
import urllib.request
import gzip


CORD_COLLECTIONS = {
    "london": {
        "url": "https://senzing-public.s3.amazonaws.com/collections/open-source-collection-london.jsonl.gz",
        "file": "cord_data/london-cord-latest.jsonl.gz",
        "data_source": "CORD_LONDON",
    },
    "moscow": {
        "url": "https://senzing-public.s3.amazonaws.com/collections/open-source-collection-moscow.jsonl.gz",
        "file": "cord_data/moscow-cord-latest.jsonl.gz",
        "data_source": "CORD_MOSCOW",
    },
    "las_vegas": {
        "url": "https://senzing-public.s3.amazonaws.com/collections/open-source-collection-lasvegas.jsonl.gz",
        "file": "cord_data/lasvegas-cord-latest.jsonl.gz",
        "data_source": "CORD_LASVEGAS",
    },
}

DB_PATH = Path("data/cord_rag.db")
CORD_DATA_DIR = Path("cord_data")


def download_cord_collection(collection_name: str, collection_config: dict, skip_if_exists: bool = True) -> Optional[Path]:
    """Download CORD collection if not already present."""
    file_path = Path(collection_config["file"])

    if skip_if_exists and file_path.exists():
        print(f"✅ {collection_name.upper()} already downloaded: {file_path}")
        return file_path

    print(f"📥 Downloading {collection_name.upper()} CORD collection...")
    print(f"   URL: {collection_config['url']}")

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(collection_config["url"], str(file_path))
        print(f"✅ Downloaded: {file_path}")
        return file_path
    except Exception as e:
        print(f"❌ Failed to download {collection_name}: {e}")
        return None


def build_cord_rag_database():
    """Build indexed SQLite database from CORD JSONL files."""

    # Create database
    db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        print(f"⚠️  Database exists: {db_path}")
        response = input("Overwrite? (y/n): ").strip().lower()
        if response != "y":
            print("Aborted.")
            return False
        db_path.unlink()

    print(f"\n🏗️  Building CORD RAG database at {db_path}...")

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

    # Load CORD data
    total_records = 0

    for collection_name, collection_config in CORD_COLLECTIONS.items():
        # Download if needed
        file_path = download_cord_collection(collection_name, collection_config)
        if not file_path or not file_path.exists():
            print(f"⚠️  Skipping {collection_name} (file not found)")
            continue

        data_source = collection_config["data_source"]
        print(f"\n📦 Loading {data_source}...")

        # Parse JSONL (compressed or not)
        collection_records = 0
        try:
            if str(file_path).endswith(".gz"):
                file_obj = gzip.open(file_path, "rt", encoding="utf-8")
            else:
                file_obj = open(file_path, "r", encoding="utf-8")

            with file_obj:
                for line_num, line in enumerate(file_obj, 1):
                    if not line.strip():
                        continue

                    try:
                        record = json.loads(line)

                        # Extract fields (CORD schema varies slightly per collection)
                        entity_id = record.get("id") or record.get("entity_id") or f"{data_source}_{line_num}"
                        entity_name = record.get("name") or record.get("entity_name") or record.get("NAME") or ""
                        country = record.get("country") or record.get("COUNTRY") or ""
                        incorporation_date = record.get("incorporation_date") or record.get("date_founded") or ""
                        beneficial_owner = record.get("beneficial_owner") or record.get("BENEFICIAL_OWNER") or ""
                        parent_company = record.get("parent_company") or record.get("PARENT_COMPANY") or ""
                        parent_country = record.get("parent_country") or record.get("PARENT_COUNTRY") or ""
                        gleif_id = record.get("gleif_id") or record.get("GLEIF_ID") or ""

                        # Check sanctions status from embedded data
                        sanctions_status = "CLEAR"
                        if record.get("ofac_hit") or record.get("OFAC_HIT"):
                            sanctions_status = "OFAC_HIT"
                        elif record.get("opensanctions_hit") or record.get("OPENSANCTIONS_HIT"):
                            sanctions_status = "OPENSANCTIONS_HIT"

                        # Insert record
                        cur.execute("""
                            INSERT OR IGNORE INTO entities
                            (entity_id, entity_name, country, incorporation_date,
                             beneficial_owner, parent_company, parent_country,
                             data_source, gleif_id, sanctions_status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            entity_id,
                            entity_name,
                            country,
                            incorporation_date,
                            beneficial_owner,
                            parent_company,
                            parent_country,
                            data_source,
                            gleif_id,
                            sanctions_status,
                        ))

                        collection_records += 1
                        total_records += 1

                        # Batch commit every 10k records
                        if collection_records % 10000 == 0:
                            conn.commit()
                            print(f"  ✓ {collection_records:,} records processed...")

                    except json.JSONDecodeError as e:
                        print(f"  ⚠️  Line {line_num}: invalid JSON, skipping")
                        continue

        except Exception as e:
            print(f"❌ Error loading {collection_name}: {e}")
            continue

        conn.commit()
        print(f"✅ Loaded {collection_records:,} records from {data_source}")

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
    conn.close()

    print(f"\n✅ CORD RAG Database built successfully!")
    print(f"   Path: {db_path}")
    print(f"   Total records: {final_count:,}")
    print(f"   By source:")
    for source, count in by_source:
        print(f"     - {source}: {count:,}")

    return True


if __name__ == "__main__":
    print("=" * 70)
    print("CORD RAG Database Builder")
    print("=" * 70)

    success = build_cord_rag_database()
    sys.exit(0 if success else 1)
