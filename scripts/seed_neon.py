#!/usr/bin/env python3

#######################################################################
# CBP Sentry - Direct Neon PostgreSQL Seeding Script
# Extracts data from local SQLite and imports into Neon staging
# Usage: python3 scripts/seed_neon.py <NEON_DATABASE_URL>
#######################################################################

import sys
import os
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any

# Try to import psycopg2 for PostgreSQL connection
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    print("⚠ psycopg2 not installed. Install with: pip install psycopg2-binary")


class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'

    @staticmethod
    def info(msg: str) -> str:
        return f"{Colors.BLUE}→{Colors.NC} {msg}"

    @staticmethod
    def success(msg: str) -> str:
        return f"{Colors.GREEN}✓{Colors.NC} {msg}"

    @staticmethod
    def error(msg: str) -> str:
        return f"{Colors.RED}✗{Colors.NC} {msg}"

    @staticmethod
    def warning(msg: str) -> str:
        return f"{Colors.YELLOW}⚠{Colors.NC} {msg}"


def get_local_shipments() -> List[Dict[str, Any]]:
    """Extract shipments from local SQLite database"""
    db_path = Path(__file__).parent.parent / "data" / "cbp_sentry.db"

    if not db_path.exists():
        # Try in Docker container
        db_path = Path("/app/data/cbp_sentry.db")
        if not db_path.exists():
            raise FileNotFoundError(
                f"SQLite database not found at {db_path}\n"
                "Run ./scripts/local_startup.sh first to create local database"
            )

    print(Colors.info(f"Connecting to local SQLite: {db_path}"))

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query all shipments
    cursor.execute("SELECT * FROM shipments ORDER BY id")
    rows = cursor.fetchall()

    shipments = [dict(row) for row in rows]
    print(Colors.success(f"Extracted {len(shipments)} shipments from local SQLite"))

    conn.close()
    return shipments


def seed_neon_database(database_url: str, shipments: List[Dict[str, Any]]) -> bool:
    """Import shipments into Neon PostgreSQL"""

    if not HAS_PSYCOPG2:
        print(Colors.error("psycopg2 is required for direct Neon import"))
        print("Install with: pip install psycopg2-binary")
        return False

    print(Colors.info(f"Connecting to Neon PostgreSQL..."))

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print(Colors.success("Connected to Neon"))

        # Check if table exists, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id TEXT PRIMARY KEY,
                manifest_id TEXT NOT NULL,
                shipper_name TEXT NOT NULL,
                consignee_name TEXT NOT NULL,
                origin_country TEXT NOT NULL,
                destination_country TEXT NOT NULL,
                hs_code TEXT,
                declared_value_usd REAL,
                declared_weight_kg REAL,
                description TEXT,
                vessel_name TEXT,
                status TEXT DEFAULT 'received',
                risk_score REAL,
                risk_delta REAL DEFAULT 0,
                h1_score REAL,
                h2_score REAL,
                h1_h2_score REAL,
                last_polled_at TIMESTAMP,
                ofac_screened_at TIMESTAMP,
                ofac_match BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        print(Colors.success("Table 'shipments' ready (created or exists)"))

        # Check for existing data
        cursor.execute("SELECT COUNT(*) FROM shipments")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            response = input(
                Colors.warning(
                    f"Table already contains {existing_count} records. "
                    "Clear and reimport? (y/n): "
                )
            )
            if response.lower() == 'y':
                cursor.execute("TRUNCATE TABLE shipments")
                print(Colors.info("Cleared existing data"))
            else:
                print(Colors.warning("Keeping existing data, skipping import"))
                conn.commit()
                conn.close()
                return True

        # Import shipments in batches
        print(Colors.info(f"Importing {len(shipments)} shipments..."))

        batch_size = 100
        for i in range(0, len(shipments), batch_size):
            batch = shipments[i : i + batch_size]

            for shipment in batch:
                try:
                    cursor.execute("""
                        INSERT INTO shipments (
                            id, manifest_id, shipper_name, consignee_name,
                            origin_country, destination_country, hs_code,
                            declared_value_usd, declared_weight_kg, description,
                            vessel_name, status, risk_score, risk_delta,
                            h1_score, h2_score, h1_h2_score, last_polled_at,
                            ofac_screened_at, ofac_match, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        shipment.get('id'),
                        shipment.get('manifest_id'),
                        shipment.get('shipper_name'),
                        shipment.get('consignee_name'),
                        shipment.get('origin_country'),
                        shipment.get('destination_country'),
                        shipment.get('hs_code'),
                        shipment.get('declared_value_usd'),
                        shipment.get('declared_weight_kg'),
                        shipment.get('description'),
                        shipment.get('vessel_name'),
                        shipment.get('status', 'received'),
                        shipment.get('risk_score'),
                        shipment.get('risk_delta', 0),
                        shipment.get('h1_score'),
                        shipment.get('h2_score'),
                        shipment.get('h1_h2_score'),
                        shipment.get('last_polled_at'),
                        shipment.get('ofac_screened_at'),
                        shipment.get('ofac_match', False),
                        shipment.get('created_at'),
                        shipment.get('updated_at'),
                    )
                    )
                except Exception as e:
                    print(Colors.error(f"Failed to insert {shipment.get('id')}: {e}"))
                    conn.rollback()
                    return False

            # Commit batch
            conn.commit()
            progress = min(i + batch_size, len(shipments))
            print(Colors.info(f"Imported {progress}/{len(shipments)} records"))

        # Verify import
        cursor.execute("SELECT COUNT(*) FROM shipments")
        final_count = cursor.fetchone()[0]

        # Risk distribution
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN risk_score >= 70 THEN 1 END) as high_risk,
                COUNT(CASE WHEN risk_score >= 50 AND risk_score < 70 THEN 1 END) as medium_risk,
                COUNT(CASE WHEN risk_score < 50 THEN 1 END) as low_risk
            FROM shipments
        """)
        distribution = cursor.fetchone()

        conn.close()

        print("")
        print(Colors.success(f"Import complete!"))
        print(f"  Total records: {final_count}")
        print(f"  High risk (>=70): {distribution[0]}")
        print(f"  Medium risk (50-70): {distribution[1]}")
        print(f"  Low risk (<50): {distribution[2]}")

        return True

    except psycopg2.Error as e:
        print(Colors.error(f"PostgreSQL error: {e}"))
        return False
    except Exception as e:
        print(Colors.error(f"Error: {e}"))
        return False


def main():
    """Main entry point"""
    print("")
    print(f"{Colors.BLUE}╔══════════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.BLUE}║ CBP Sentry - Neon PostgreSQL Direct Seeding              ║{Colors.NC}")
    print(f"{Colors.BLUE}╚══════════════════════════════════════════════════════════╝{Colors.NC}")
    print("")

    # Get Neon database URL
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        if len(sys.argv) > 1:
            database_url = sys.argv[1]
        else:
            database_url = input(
                Colors.info("Enter Neon DATABASE_URL: ")
            )

    if not database_url:
        print(Colors.error("DATABASE_URL is required"))
        sys.exit(1)

    # Validate URL format
    if not database_url.startswith('postgresql://'):
        print(Colors.error("Invalid PostgreSQL URL format"))
        print("Expected: postgresql://user:password@host/dbname?sslmode=require")
        sys.exit(1)

    try:
        # Extract shipments from local SQLite
        shipments = get_local_shipments()

        if not shipments:
            print(Colors.warning("No shipments found in local database"))
            sys.exit(1)

        # Import into Neon
        success = seed_neon_database(database_url, shipments)

        if success:
            print("")
            print(f"{Colors.GREEN}✓ Neon staging database is now seeded and ready!{Colors.NC}")
            print("")
            print("Next steps:")
            print("  1. Verify: SELECT COUNT(*) FROM shipments;")
            print("  2. Deploy: git push origin main (triggers Cloud Run)")
            print("  3. Test: Visit https://sentry-ui-<HASH>.us-central1.run.app")
            print("")
            sys.exit(0)
        else:
            print(Colors.error("Import failed"))
            sys.exit(1)

    except FileNotFoundError as e:
        print(Colors.error(str(e)))
        sys.exit(1)
    except Exception as e:
        print(Colors.error(f"Unexpected error: {e}"))
        sys.exit(1)


if __name__ == '__main__':
    main()
