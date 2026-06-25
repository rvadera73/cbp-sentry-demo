#!/usr/bin/env python3
"""
CBP Sentry: Verify Risk Scoring Infrastructure Setup

This script verifies that all components of Phase 1 are correctly configured.

Usage:
    python3 scripts/verify_risk_scoring_setup.py \
        --postgres-url postgresql://user:pass@host:5432/cbp_sentry \
        --redis-url redis://localhost:6379
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Import dependencies
try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


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


class Verifier:
    def __init__(self, postgres_url: str, redis_url: str = None):
        self.postgres_url = postgres_url
        self.redis_url = redis_url or "redis://localhost:6379"
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'summary': {}
        }

    def run_all_checks(self):
        """Run all verification checks"""
        print("\n" + "="*70)
        print("CBP SENTRY: RISK SCORING INFRASTRUCTURE VERIFICATION")
        print("="*70)

        # PostgreSQL checks
        print("\n" + Colors.info("PostgreSQL Checks"))
        self._check_postgres_schema()
        self._check_tables()
        self._check_cbp_domain()
        self._check_features()
        self._check_rules()
        self._check_indexes()

        # Redis checks
        print("\n" + Colors.info("Redis Checks"))
        self._check_redis_connection()

        # GCP checks
        print("\n" + Colors.info("GCP Checks"))
        self._check_gcp_bucket()

        # File checks
        print("\n" + Colors.info("File Checks"))
        self._check_sql_scripts()

        # Summary
        self._print_summary()

    def _check_postgres_schema(self):
        """Verify PostgreSQL schema exists"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT EXISTS(SELECT 1 FROM information_schema.schemata
                WHERE schema_name = 'risk_scoring')
            """)
            exists = cursor.fetchone()[0]

            status = "PASS" if exists else "FAIL"
            self.results['checks']['postgres_schema'] = status

            if exists:
                print(Colors.success("PostgreSQL schema 'risk_scoring' exists"))
            else:
                print(Colors.error("PostgreSQL schema 'risk_scoring' NOT found"))

            cursor.close()
            conn.close()

        except Exception as e:
            print(Colors.error(f"PostgreSQL connection failed: {e}"))
            self.results['checks']['postgres_schema'] = "ERROR"

    def _check_tables(self):
        """Verify all 12 tables exist"""
        expected_tables = [
            'domains',
            'scorecards',
            'features_cbp',
            'rule_parameters',
            'rule_change_events',
            'model_scores',
            'feedback',
            'model_training_runs',
            'drift_alerts',
            'model_versions',
            'model_inference_cache',
            'model_performance_metrics'
        ]

        try:
            conn = psycopg2.connect(self.postgres_url)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'risk_scoring' ORDER BY table_name
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]

            missing = set(expected_tables) - set(existing_tables)
            status = "PASS" if len(missing) == 0 else "FAIL"
            self.results['checks']['tables'] = {
                'status': status,
                'total': len(existing_tables),
                'expected': len(expected_tables),
                'missing': list(missing) if missing else []
            }

            print(Colors.success(f"Tables: {len(existing_tables)}/{len(expected_tables)} found"))

            if missing:
                for table in missing:
                    print(Colors.warning(f"  Missing: {table}"))

            cursor.close()
            conn.close()

        except Exception as e:
            print(Colors.error(f"Table check failed: {e}"))
            self.results['checks']['tables'] = "ERROR"

    def _check_cbp_domain(self):
        """Verify CBP domain is registered"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT domain_id, name, description FROM risk_scoring.domains
                WHERE name = 'cbp_illegal_transshipment'
            """)
            result = cursor.fetchone()

            status = "PASS" if result else "FAIL"
            self.results['checks']['cbp_domain'] = status

            if result:
                domain_id, name, description = result
                print(Colors.success(f"CBP Domain registered (ID: {domain_id})"))
                print(f"  Name: {name}")
                print(f"  Description: {description[:80]}...")
            else:
                print(Colors.error("CBP Domain NOT registered"))

            cursor.close()
            conn.close()

        except Exception as e:
            print(Colors.error(f"CBP domain check failed: {e}"))
            self.results['checks']['cbp_domain'] = "ERROR"

    def _check_features(self):
        """Verify CBP features are configured"""
        expected_features = [
            'shipper_sanction_risk',
            'destination_risk',
            'entity_history',
            'shipment_pattern_anomaly',
            'product_risk',
            'routing_anomaly',
            'regulatory_flag_history'
        ]

        try:
            conn = psycopg2.connect(self.postgres_url)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM risk_scoring.features_cbp ORDER BY name
            """)
            existing_features = [row[0] for row in cursor.fetchall()]

            missing = set(expected_features) - set(existing_features)
            status = "PASS" if len(missing) == 0 else "FAIL"
            self.results['checks']['features'] = {
                'status': status,
                'total': len(existing_features),
                'expected': len(expected_features),
                'missing': list(missing) if missing else []
            }

            print(Colors.success(f"Features: {len(existing_features)}/{len(expected_features)} found"))

            if missing:
                for feature in missing:
                    print(Colors.warning(f"  Missing: {feature}"))

            cursor.close()
            conn.close()

        except Exception as e:
            print(Colors.error(f"Features check failed: {e}"))
            self.results['checks']['features'] = "ERROR"

    def _check_rules(self):
        """Verify rules are configured"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            cursor = conn.cursor()

            # Count rule parameters
            cursor.execute("SELECT COUNT(*) FROM risk_scoring.rule_parameters")
            rule_params_count = cursor.fetchone()[0]

            # Check for all 8 rules
            cursor.execute("""
                SELECT DISTINCT rule_id FROM risk_scoring.rule_parameters
                ORDER BY rule_id
            """)
            configured_rules = [row[0] for row in cursor.fetchall()]

            status = "PASS" if len(configured_rules) >= 8 else "WARN"
            self.results['checks']['rules'] = {
                'status': status,
                'parameters_count': rule_params_count,
                'configured_rules': len(configured_rules)
            }

            print(Colors.success(f"Rules: {len(configured_rules)} rules configured ({rule_params_count} parameters)"))

            cursor.close()
            conn.close()

        except Exception as e:
            print(Colors.error(f"Rules check failed: {e}"))
            self.results['checks']['rules'] = "ERROR"

    def _check_indexes(self):
        """Verify indexes are created"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM pg_indexes
                WHERE schemaname = 'risk_scoring'
            """)
            index_count = cursor.fetchone()[0]

            status = "PASS" if index_count > 20 else "WARN"
            self.results['checks']['indexes'] = {
                'status': status,
                'total': index_count
            }

            print(Colors.success(f"Indexes: {index_count} indexes created"))

            cursor.close()
            conn.close()

        except Exception as e:
            print(Colors.error(f"Indexes check failed: {e}"))
            self.results['checks']['indexes'] = "ERROR"

    def _check_redis_connection(self):
        """Verify Redis connection"""
        if not REDIS_AVAILABLE:
            print(Colors.warning("Redis check skipped (redis-py not installed)"))
            self.results['checks']['redis'] = "SKIPPED"
            return

        try:
            r = redis.from_url(self.redis_url, decode_responses=True)
            r.ping()

            # Check cache config
            ttl = r.get('cache:config:ttl_seconds')
            status = "PASS" if ttl else "WARN"
            self.results['checks']['redis'] = status

            print(Colors.success("Redis connection verified"))
            if ttl:
                print(f"  TTL: {ttl} seconds ({int(ttl)/86400:.1f} days)")

        except Exception as e:
            print(Colors.warning(f"Redis connection failed: {e}"))
            self.results['checks']['redis'] = "WARN"

    def _check_gcp_bucket(self):
        """Verify GCP bucket exists"""
        try:
            import subprocess
            result = subprocess.run(
                ['gsutil', 'ls', '-r', 'gs://cbp-sentry-models/'],
                capture_output=True,
                timeout=10
            )

            status = "PASS" if result.returncode == 0 else "WARN"
            self.results['checks']['gcp_bucket'] = status

            if result.returncode == 0:
                print(Colors.success("GCP bucket gs://cbp-sentry-models exists"))
            else:
                print(Colors.warning("GCP bucket check skipped or failed"))

        except Exception as e:
            print(Colors.warning(f"GCP bucket check skipped: {e}"))
            self.results['checks']['gcp_bucket'] = "SKIPPED"

    def _check_sql_scripts(self):
        """Verify SQL scripts exist"""
        scripts = [
            'sql/01-risk_scoring-schema.sql',
            'sql/02-cbp-domain-init.sql'
        ]

        script_dir = Path(__file__).parent
        missing = []

        for script in scripts:
            script_path = script_dir / script
            if not script_path.exists():
                missing.append(script)

        status = "PASS" if not missing else "FAIL"
        self.results['checks']['sql_scripts'] = {
            'status': status,
            'found': len(scripts) - len(missing),
            'total': len(scripts),
            'missing': missing
        }

        print(Colors.success(f"SQL Scripts: {len(scripts) - len(missing)}/{len(scripts)} found"))

        if missing:
            for script in missing:
                print(Colors.error(f"  Missing: {script}"))

    def _print_summary(self):
        """Print verification summary"""
        print("\n" + "="*70)
        print("VERIFICATION SUMMARY")
        print("="*70)

        passed = sum(1 for check in self.results['checks'].values() if check == "PASS")
        failed = sum(1 for check in self.results['checks'].values() if check == "FAIL")
        warnings = sum(1 for check in self.results['checks'].values() if check in ["WARN", "SKIPPED"])

        print(Colors.success(f"Passed: {passed}"))
        print(Colors.warning(f"Warnings/Skipped: {warnings}"))
        if failed > 0:
            print(Colors.error(f"Failed: {failed}"))

        # Overall status
        if failed == 0 and passed >= 6:
            print("\n" + Colors.success("Infrastructure setup VERIFIED"))
            return 0
        elif failed == 0:
            print("\n" + Colors.warning("Infrastructure setup PARTIALLY VERIFIED"))
            return 1
        else:
            print("\n" + Colors.error("Infrastructure setup VERIFICATION FAILED"))
            return 2

    def save_report(self, output_file: str):
        """Save verification report"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(Colors.success(f"Report saved to {output_file}"))


def main():
    parser = argparse.ArgumentParser(
        description="Verify CBP Sentry Risk Scoring Infrastructure"
    )
    parser.add_argument(
        '--postgres-url',
        default=os.getenv('DATABASE_URL'),
        help='PostgreSQL connection URL'
    )
    parser.add_argument(
        '--redis-url',
        default=os.getenv('REDIS_URL'),
        help='Redis connection URL'
    )
    parser.add_argument(
        '--output-json',
        default='/tmp/verify_result.json',
        help='Output file for verification results'
    )

    args = parser.parse_args()

    if not args.postgres_url:
        print(Colors.error("ERROR: PostgreSQL URL required"))
        sys.exit(1)

    verifier = Verifier(args.postgres_url, args.redis_url)
    verifier.run_all_checks()
    verifier.save_report(args.output_json)

    return verifier._print_summary()


if __name__ == '__main__':
    sys.exit(main())
