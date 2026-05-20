"""
CORD Loader — Loads Senzing Ready Data Collections into the entity resolution system.

Senzing CORDs (Collections Of Relatable Data) are free datasets containing real
corporate records, GLEIF data, OFAC sanctions, and other registries.

This loader:
1. Accepts CORD CSV files (from https://senzing.com/senzing-ready-data-collections-cord/)
2. Transforms to Senzing JSON format
3. Loads into Senzing for entity resolution
4. Provides reference data for CBP case investigations

Usage:
    python cord_loader.py --cord-csv las-vegas-cord.csv --data-source CORD_LAS_VEGAS
"""

import csv
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CORDLoader:
    """Loads CORD data into Senzing."""

    # Map CORD CSV columns to Senzing JSON fields
    COLUMN_MAPPING = {
        # Standard fields (CORD CSV → Senzing JSON)
        'name': 'NAME_FULL',
        'company_name': 'NAME_FULL',
        'legal_name': 'NAME_FULL',
        'organization_name': 'NAME_FULL',

        'country_code': 'COUNTRY_CODE',
        'country': 'COUNTRY_CODE',
        'registration_country': 'COUNTRY_CODE',

        'address': 'ADDR_FULL',
        'street_address': 'ADDR_FULL',
        'address_line_1': 'ADDR_FULL',

        'phone': 'PHONE_NUMBER',
        'phone_number': 'PHONE_NUMBER',
        'telephone': 'PHONE_NUMBER',

        'email': 'EMAIL_ADDRESS',
        'email_address': 'EMAIL_ADDRESS',

        'registration_number': 'REGISTRATION_NUMBER',
        'company_registration': 'REGISTRATION_NUMBER',
        'gleif_lei': 'GLEIF_LEI',
        'lei': 'GLEIF_LEI',

        'directors': 'DIRECTORS',
        'director_names': 'DIRECTORS',
        'beneficial_owners': 'BENEFICIAL_OWNERS',
        'shareholders': 'SHAREHOLDERS',

        'incorporation_date': 'DATE_INCORPORATED',
        'registration_date': 'DATE_INCORPORATED',
        'founded': 'DATE_INCORPORATED',

        'business_type': 'BUSINESS_TYPE',
        'industry': 'BUSINESS_TYPE',
        'sic_code': 'INDUSTRY_CODE',
        'nace_code': 'INDUSTRY_CODE',

        'financial_status': 'FINANCIAL_STATUS',
        'status': 'FINANCIAL_STATUS',
        'active': 'FINANCIAL_STATUS',

        'sanctions_list': 'SANCTIONS_LIST',
        'ofac_match': 'OFAC_MATCH',
        'pep_status': 'PEP_STATUS',
        'politically_exposed_person': 'PEP_STATUS',
    }

    def __init__(self, senzing_url: str = "http://localhost:8250"):
        """
        Initialize CORD loader.

        Args:
            senzing_url: Senzing service base URL
        """
        self.senzing_url = senzing_url.rstrip('/')
        self.records_loaded = 0
        self.errors = 0

    def load_cord_csv(
        self,
        csv_path: str,
        data_source: str = "CORD_REFERENCE",
        dry_run: bool = False
    ) -> Dict:
        """
        Load CORD CSV file into Senzing.

        Args:
            csv_path: Path to CORD CSV file
            data_source: Senzing DATA_SOURCE identifier
            dry_run: If True, don't actually load, just validate

        Returns:
            Dict with loading statistics
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CORD CSV not found: {csv_path}")

        logger.info(f"Loading CORD CSV: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, 1):
                try:
                    senzing_record = self._transform_cord_row(row, data_source)

                    if dry_run:
                        logger.debug(f"Row {row_num}: {senzing_record}")
                    else:
                        self._load_senzing_record(senzing_record)

                    self.records_loaded += 1

                    if row_num % 100 == 0:
                        logger.info(f"Processed {row_num} records...")

                except Exception as e:
                    logger.error(f"Error processing row {row_num}: {e}")
                    self.errors += 1

        result = {
            "source": data_source,
            "records_loaded": self.records_loaded,
            "errors": self.errors,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"CORD load complete: {result}")
        return result

    def _transform_cord_row(self, row: Dict, data_source: str) -> Dict:
        """
        Transform CORD CSV row to Senzing JSON record.

        Args:
            row: CSV row dict
            data_source: Senzing DATA_SOURCE identifier

        Returns:
            Senzing JSON record
        """
        senzing_record = {
            "DATA_SOURCE": data_source,
            "RECORD_ID": row.get('id') or row.get('record_id') or f"cord_{self.records_loaded}"
        }

        # Map CSV columns to Senzing fields
        for csv_col, senzing_field in self.COLUMN_MAPPING.items():
            if csv_col in row and row[csv_col]:
                value = row[csv_col].strip()
                if value:
                    senzing_record[senzing_field] = value

        # Ensure required fields
        if 'NAME_FULL' not in senzing_record:
            raise ValueError(f"Row missing required 'name' field: {row}")

        return senzing_record

    def _load_senzing_record(self, record: Dict) -> str:
        """
        Load a record into Senzing via REST API.

        Args:
            record: Senzing JSON record

        Returns:
            Senzing record_id
        """
        try:
            url = f"{self.senzing_url}/load-record"
            response = requests.post(url, json=record, timeout=30)
            response.raise_for_status()

            result = response.json()
            record_id = result.get('RECORD_ID', record.get('RECORD_ID'))

            logger.debug(f"Loaded record: {record_id}")
            return record_id

        except requests.exceptions.ConnectionError:
            logger.warning(f"Senzing service unavailable at {self.senzing_url}")
            return record.get('RECORD_ID', 'unknown')
        except Exception as e:
            logger.error(f"Failed to load record: {e}")
            raise

    def load_cord_json(self, json_path: str, data_source: str = "CORD_REFERENCE") -> Dict:
        """
        Load CORD from JSON lines format.

        Args:
            json_path: Path to CORD JSONL file
            data_source: Senzing DATA_SOURCE identifier

        Returns:
            Dict with loading statistics
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"CORD JSON not found: {json_path}")

        logger.info(f"Loading CORD JSON: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line)
                    record['DATA_SOURCE'] = data_source

                    self._load_senzing_record(record)
                    self.records_loaded += 1

                    if line_num % 100 == 0:
                        logger.info(f"Processed {line_num} records...")

                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    self.errors += 1

        result = {
            "source": data_source,
            "records_loaded": self.records_loaded,
            "errors": self.errors,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"CORD load complete: {result}")
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Load Senzing CORD data for entity resolution"
    )
    parser.add_argument(
        '--cord-csv',
        help='Path to CORD CSV file'
    )
    parser.add_argument(
        '--cord-json',
        help='Path to CORD JSONL file'
    )
    parser.add_argument(
        '--data-source',
        default='CORD_REFERENCE',
        help='Senzing DATA_SOURCE identifier'
    )
    parser.add_argument(
        '--senzing-url',
        default='http://localhost:8250',
        help='Senzing service URL'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate without loading'
    )

    args = parser.parse_args()

    loader = CORDLoader(senzing_url=args.senzing_url)

    if args.cord_csv:
        result = loader.load_cord_csv(args.cord_csv, args.data_source, args.dry_run)
    elif args.cord_json:
        result = loader.load_cord_json(args.cord_json, args.data_source)
    else:
        parser.print_help()
        return

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
