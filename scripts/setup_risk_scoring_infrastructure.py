#!/usr/bin/env python3
"""
CBP Sentry: Risk Scoring Infrastructure Setup (Phase 1)

This script initializes:
1. PostgreSQL risk_scoring schema and 12 tables
2. GCP Cloud Storage bucket (gs://cbp-sentry-models)
3. Redis cache for inference results
4. CBP domain configuration

Usage:
    python3 scripts/setup_risk_scoring_infrastructure.py \
        --postgres-url postgresql://user:pass@host:5432/cbp_sentry \
        --gcp-project cbp-sentry \
        --redis-host localhost:6379

Environment Variables:
    DATABASE_URL - PostgreSQL connection string
    GCP_PROJECT_ID - GCP project ID
    REDIS_URL - Redis connection string (redis://host:port)
"""

import os
import sys
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import subprocess

# Try to import dependencies
try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)

try:
    import redis
except ImportError:
    print("WARNING: redis-py not installed. Install with: pip install redis")
    REDIS_AVAILABLE = False
else:
    REDIS_AVAILABLE = True

try:
    from google.cloud import storage
    from google.oauth2 import service_account
except ImportError:
    print("WARNING: google-cloud-storage not installed. Install with: pip install google-cloud-storage")
    GCP_AVAILABLE = False
else:
    GCP_AVAILABLE = True


# ============================================================================
# Logging Configuration
# ============================================================================

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


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PostgreSQL Schema Setup
# ============================================================================

class PostgresSetup:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.cursor = None

    def connect(self) -> bool:
        """Establish PostgreSQL connection"""
        try:
            print(Colors.info("Connecting to PostgreSQL..."))
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor()
            print(Colors.success("Connected to PostgreSQL"))
            return True
        except Exception as e:
            print(Colors.error(f"PostgreSQL connection failed: {e}"))
            return False

    def load_and_execute_sql(self, sql_file: str) -> Tuple[bool, str]:
        """Load and execute SQL script"""
        try:
            script_path = Path(__file__).parent / "sql" / sql_file
            if not script_path.exists():
                return False, f"SQL file not found: {script_path}"

            print(Colors.info(f"Executing {sql_file}..."))

            with open(script_path, 'r') as f:
                sql_content = f.read()

            # Split by statement and execute
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            for i, statement in enumerate(statements, 1):
                if not statement.startswith('--'):
                    try:
                        self.cursor.execute(statement)
                    except psycopg2.Error as e:
                        # Continue on duplicate/conflict errors
                        if 'duplicate' not in str(e).lower() and 'conflict' not in str(e).lower():
                            return False, f"SQL error at statement {i}: {e}"

            self.conn.commit()
            print(Colors.success(f"Executed {sql_file}"))
            return True, ""

        except Exception as e:
            return False, str(e)

    def get_table_count(self) -> int:
        """Count tables in risk_scoring schema"""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'risk_scoring'
            """)
            count = self.cursor.fetchone()[0]
            return count
        except Exception as e:
            print(Colors.warning(f"Could not count tables: {e}"))
            return 0

    def get_schema_status(self) -> Dict:
        """Get comprehensive schema status"""
        try:
            status = {}

            # Check if schema exists
            self.cursor.execute("""
                SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'risk_scoring')
            """)
            status['schema_exists'] = self.cursor.fetchone()[0]

            # Count tables
            self.cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'risk_scoring'
            """)
            status['table_count'] = self.cursor.fetchone()[0]

            # List tables
            self.cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'risk_scoring' ORDER BY table_name
            """)
            status['tables'] = [row[0] for row in self.cursor.fetchall()]

            # Check CBP domain
            self.cursor.execute("""
                SELECT COUNT(*) FROM risk_scoring.domains WHERE name = 'cbp_illegal_transshipment'
            """)
            status['cbp_domain_registered'] = self.cursor.fetchone()[0] > 0

            # Count features
            self.cursor.execute("SELECT COUNT(*) FROM risk_scoring.features_cbp")
            status['feature_count'] = self.cursor.fetchone()[0]

            # Count rules
            self.cursor.execute("SELECT COUNT(*) FROM risk_scoring.rule_parameters")
            status['rule_parameter_count'] = self.cursor.fetchone()[0]

            return status
        except Exception as e:
            print(Colors.warning(f"Could not get schema status: {e}"))
            return {}

    def close(self):
        """Close PostgreSQL connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print(Colors.success("PostgreSQL connection closed"))


# ============================================================================
# GCP Cloud Storage Setup
# ============================================================================

class GCPSetup:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = None

    def connect(self) -> bool:
        """Initialize GCP Storage client"""
        if not GCP_AVAILABLE:
            print(Colors.warning("google-cloud-storage not available; skipping GCP setup"))
            return False

        try:
            print(Colors.info("Initializing GCP Storage client..."))
            self.client = storage.Client(project=self.project_id)
            print(Colors.success("GCP Storage client initialized"))
            return True
        except Exception as e:
            print(Colors.warning(f"GCP initialization failed: {e}"))
            return False

    def create_bucket(self, bucket_name: str) -> bool:
        """Create GCP Cloud Storage bucket"""
        if not self.client:
            return False

        try:
            print(Colors.info(f"Creating/checking bucket {bucket_name}..."))
            bucket = self.client.bucket(bucket_name)

            if bucket.exists():
                print(Colors.success(f"Bucket {bucket_name} already exists"))
                return True

            bucket = self.client.create_bucket(bucket_name, location='us-central1')
            print(Colors.success(f"Created bucket {bucket_name}"))
            return True

        except Exception as e:
            print(Colors.warning(f"Bucket creation failed: {e}"))
            return False

    def create_paths(self, bucket_name: str) -> List[str]:
        """Create directory structure in bucket"""
        if not self.client:
            return []

        paths_created = []
        paths = [
            'cbp/xgboost/',
            'cbp/isolation_forest/',
            'cbp/shap_explainer/',
            'cbp/training_data/',
            'cbp/evaluation_results/'
        ]

        try:
            bucket = self.client.bucket(bucket_name)

            for path in paths:
                # Create a placeholder object to represent the path
                blob = bucket.blob(path + '.gitkeep')
                blob.upload_from_string("")
                paths_created.append(f"gs://{bucket_name}/{path}")
                print(Colors.success(f"Created path gs://{bucket_name}/{path}"))

        except Exception as e:
            print(Colors.warning(f"Path creation failed: {e}"))

        return paths_created

    def get_bucket_path(self) -> str:
        """Return bucket path"""
        return "gs://cbp-sentry-models"


# ============================================================================
# Redis Setup
# ============================================================================

class RedisSetup:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.client = None

    def connect(self) -> bool:
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            print(Colors.warning("redis-py not available; skipping Redis setup"))
            return False

        try:
            print(Colors.info(f"Connecting to Redis at {self.redis_url}..."))
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            print(Colors.success("Connected to Redis"))
            return True
        except Exception as e:
            print(Colors.warning(f"Redis connection failed: {e}"))
            return False

    def set_cache_config(self) -> bool:
        """Set cache configuration and test key"""
        if not self.client:
            return False

        try:
            print(Colors.info("Setting cache configuration..."))

            # Set TTL configuration (7 days = 604800 seconds)
            ttl_seconds = 7 * 24 * 60 * 60
            config = {
                'ttl_seconds': str(ttl_seconds),
                'key_prefix': 'risk_score:cbp:',
                'initialized_at': datetime.now().isoformat()
            }

            for key, value in config.items():
                self.client.set(f"cache:config:{key}", value)

            # Test key
            test_key = "risk_score:cbp:test_entity_001"
            test_value = json.dumps({'score': 0.75, 'confidence': 0.92})
            self.client.setex(test_key, ttl_seconds, test_value)

            print(Colors.success("Cache configuration set"))
            return True

        except Exception as e:
            print(Colors.warning(f"Cache configuration failed: {e}"))
            return False

    def test_connection(self) -> bool:
        """Test Redis connection"""
        if not self.client:
            return False

        try:
            result = self.client.ping()
            if result:
                print(Colors.success("Redis connection verified"))
                return True
            return False
        except Exception as e:
            print(Colors.warning(f"Redis test failed: {e}"))
            return False


# ============================================================================
# Main Setup Orchestration
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="CBP Sentry Risk Scoring Infrastructure Setup (Phase 1)"
    )
    parser.add_argument(
        '--postgres-url',
        default=os.getenv('DATABASE_URL'),
        help='PostgreSQL connection URL'
    )
    parser.add_argument(
        '--gcp-project',
        default=os.getenv('GCP_PROJECT_ID', 'cbp-sentry'),
        help='GCP project ID'
    )
    parser.add_argument(
        '--redis-url',
        default=os.getenv('REDIS_URL'),
        help='Redis connection URL'
    )
    parser.add_argument(
        '--output-json',
        default='/tmp/setup_result.json',
        help='Output file for setup results'
    )

    args = parser.parse_args()

    # Validate required arguments
    if not args.postgres_url:
        print(Colors.error("ERROR: PostgreSQL URL required (--postgres-url or DATABASE_URL env var)"))
        sys.exit(1)

    # Initialize result tracking
    result = {
        'timestamp': datetime.now().isoformat(),
        'schema_created': False,
        'tables_count': 0,
        'gcp_bucket_path': None,
        'redis_connected': False,
        'initial_configs_loaded': False,
        'sql_script_path': str(Path(__file__).parent / 'sql'),
        'issues': []
    }

    try:
        # ====================================================================
        # 1. PostgreSQL Setup
        # ====================================================================
        print("\n" + "="*70)
        print("PHASE 1: PostgreSQL Schema Setup")
        print("="*70)

        pg = PostgresSetup(args.postgres_url)
        if not pg.connect():
            result['issues'].append('PostgreSQL connection failed')
            raise Exception("Could not connect to PostgreSQL")

        # Execute schema creation
        success, error = pg.load_and_execute_sql('01-risk_scoring-schema.sql')
        if success:
            result['schema_created'] = True
            result['tables_count'] = pg.get_table_count()
            print(Colors.success(f"Schema created with {result['tables_count']} tables"))
        else:
            result['issues'].append(f"Schema creation failed: {error}")

        # Execute CBP domain initialization
        success, error = pg.load_and_execute_sql('02-cbp-domain-init.sql')
        if success:
            result['initial_configs_loaded'] = True
            status = pg.get_schema_status()
            print(Colors.success(f"CBP domain registered with {status.get('feature_count', 0)} features"))
        else:
            result['issues'].append(f"CBP domain initialization failed: {error}")

        pg.close()

        # ====================================================================
        # 2. GCP Setup
        # ====================================================================
        print("\n" + "="*70)
        print("PHASE 2: GCP Cloud Storage Setup")
        print("="*70)

        gcp = GCPSetup(args.gcp_project)
        if gcp.connect():
            if gcp.create_bucket('cbp-sentry-models'):
                paths = gcp.create_paths('cbp-sentry-models')
                result['gcp_bucket_path'] = 'gs://cbp-sentry-models'
                if not paths:
                    result['issues'].append("GCP paths not created but bucket exists")
            else:
                result['issues'].append("GCP bucket creation failed")
        else:
            result['issues'].append("GCP not available (google-cloud-storage not installed)")

        # ====================================================================
        # 3. Redis Setup
        # ====================================================================
        print("\n" + "="*70)
        print("PHASE 3: Redis Cache Setup")
        print("="*70)

        redis_setup = RedisSetup(args.redis_url)
        if redis_setup.connect():
            if redis_setup.test_connection():
                if redis_setup.set_cache_config():
                    result['redis_connected'] = True
                    print(Colors.success("Redis cache configured (7-day TTL)"))
                else:
                    result['issues'].append("Redis cache configuration failed")
            else:
                result['issues'].append("Redis connection test failed")
        else:
            result['issues'].append("Redis not available (redis-py not installed or connection failed)")

        # ====================================================================
        # Summary
        # ====================================================================
        print("\n" + "="*70)
        print("SETUP SUMMARY")
        print("="*70)

        print(Colors.info(f"Schema Created: {result['schema_created']}"))
        print(Colors.info(f"Tables Created: {result['tables_count']}/12"))
        print(Colors.info(f"GCP Bucket: {result['gcp_bucket_path']}"))
        print(Colors.info(f"Redis Connected: {result['redis_connected']}"))
        print(Colors.info(f"CBP Domain Configured: {result['initial_configs_loaded']}"))
        print(Colors.info(f"SQL Scripts: {result['sql_script_path']}"))

        if result['issues']:
            print(Colors.warning("Issues encountered:"))
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print(Colors.success("All infrastructure setup completed successfully"))

        # ====================================================================
        # Output Results
        # ====================================================================
        with open(args.output_json, 'w') as f:
            json.dump(result, f, indent=2)
        print(Colors.success(f"Results saved to {args.output_json}"))

        # Exit code based on success
        success_count = sum([
            result['schema_created'],
            result['gcp_bucket_path'] is not None,
            result['redis_connected'],
            result['initial_configs_loaded']
        ])

        if success_count >= 3:
            print(Colors.success("Infrastructure setup completed (Phase 1 ready)"))
            return 0
        else:
            print(Colors.warning("Infrastructure setup partially completed; review issues above"))
            return 1

    except Exception as e:
        print(Colors.error(f"Setup failed: {e}"))
        result['issues'].append(str(e))
        with open(args.output_json, 'w') as f:
            json.dump(result, f, indent=2)
        return 1


if __name__ == '__main__':
    sys.exit(main())
