"""
Synthetic Training Data Generator for Risk Scoring Model Validation

Generates 5,000 realistic shipments with expected outcomes for model backtesting.
Patterns based on actual CBP enforcement history and trade finance anomalies.
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class SyntheticShipment:
    """Synthetic shipment with expected outcome for validation"""

    shipment_id: str
    origin_country: str
    destination_country: str
    shipper_name: str
    commodity_code: str
    commodity_name: str
    declared_value_usd: float
    declared_weight_kg: float
    element9_is_mismatch: bool
    element9_declared_country: str
    element9_actual_country: str
    h2_signals: List[str]
    shipper_age_months: int
    dwell_days: int
    vessel_name: str
    ad_cvd_applicable: bool
    ad_cvd_rate: float
    expected_outcome: str  # SEIZED | EXAMINED | CLEARED
    expected_risk_level: str  # HIGH | MEDIUM | LOW
    pattern_type: str  # Describes which pattern this follows

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SyntheticDataGenerator:
    """Generate training data for model validation"""

    # HIGH-RISK PATTERNS (30% of dataset = 1,500 shipments)
    HIGH_RISK_PATTERNS = {
        "origin_concealment_cn": {
            "origin_country": "CN",
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(3, 12),
            "element9_is_mismatch": True,
            "element9_declared_country": "VN",
            "element9_actual_country": "CN",
            "h2_signals": ["ISF_MISMATCH", "AIS_DWELL_ANOMALY"],
            "dwell_days": lambda: random.randint(7, 14),
            "declared_value_usd": lambda: random.randint(200000, 800000),
            "ad_cvd_rate": 250,
            "commodity_codes": ["8541", "8542", "2933"],  # Semiconductors, pharma
            "expected_outcome": "SEIZED",
            "expected_risk_level": "HIGH",
        },
        "tariff_evasion_vn": {
            "origin_country": "VN",
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(12, 36),
            "element9_is_mismatch": True,
            "element9_declared_country": "VN",
            "element9_actual_country": "CN",
            "h2_signals": ["ISF_MISMATCH"],
            "dwell_days": lambda: random.randint(5, 10),
            "declared_value_usd": lambda: random.randint(100000, 600000),
            "ad_cvd_rate": 150,
            "commodity_codes": ["7604", "7610", "7211"],  # Aluminum
            "expected_outcome": "EXAMINED",
            "expected_risk_level": "HIGH",
        },
        "forced_labor_my": {
            "origin_country": "MY",
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(6, 24),
            "element9_is_mismatch": False,
            "element9_declared_country": "MY",
            "element9_actual_country": "MY",
            "h2_signals": ["UFLPA_CONCERN"],
            "dwell_days": lambda: random.randint(3, 8),
            "declared_value_usd": lambda: random.randint(150000, 500000),
            "ad_cvd_rate": 40,
            "commodity_codes": ["8501", "8517", "2710"],  # Solar, semiconductors
            "expected_outcome": "EXAMINED",
            "expected_risk_level": "HIGH",
        },
    }

    # MEDIUM-RISK PATTERNS (50% of dataset = 2,500 shipments)
    MEDIUM_RISK_PATTERNS = {
        "new_shipper_established_commodity": {
            "origin_country": "VN",
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(12, 36),
            "element9_is_mismatch": False,
            "element9_declared_country": lambda: random.choice(["VN", "CN", "MY"]),
            "element9_actual_country": lambda: random.choice(["VN", "CN", "MY"]),
            "h2_signals": [],
            "dwell_days": lambda: random.randint(2, 5),
            "declared_value_usd": lambda: random.randint(80000, 400000),
            "ad_cvd_rate": 100,
            "commodity_codes": ["7604", "8483", "6203"],  # Normal goods
            "expected_outcome": "EXAMINED",
            "expected_risk_level": "MEDIUM",
        },
        "transshipment_legitimate": {
            "origin_country": "CN",
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(36, 120),
            "element9_is_mismatch": False,
            "element9_declared_country": "CN",
            "element9_actual_country": "CN",
            "h2_signals": [],
            "dwell_days": lambda: random.randint(2, 4),
            "declared_value_usd": lambda: random.randint(100000, 500000),
            "ad_cvd_rate": 25,
            "commodity_codes": ["6203", "6204", "6209"],  # Textiles (legitimate)
            "expected_outcome": "CLEARED",
            "expected_risk_level": "MEDIUM",
        },
        "unusual_commodity_established_party": {
            "origin_country": "MY",
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(48, 120),
            "element9_is_mismatch": False,
            "element9_declared_country": "MY",
            "element9_actual_country": "MY",
            "h2_signals": [],
            "dwell_days": lambda: random.randint(1, 3),
            "declared_value_usd": lambda: random.randint(50000, 300000),
            "ad_cvd_rate": 0,
            "commodity_codes": ["3923", "3926", "3915"],  # Plastic articles
            "expected_outcome": "CLEARED",
            "expected_risk_level": "MEDIUM",
        },
    }

    # LOW-RISK PATTERNS (20% of dataset = 1,000 shipments)
    LOW_RISK_PATTERNS = {
        "established_ca_exporter": {
            "origin_country": "CA",
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(60, 240),
            "element9_is_mismatch": False,
            "element9_declared_country": "CA",
            "element9_actual_country": "CA",
            "h2_signals": [],
            "dwell_days": lambda: random.randint(0, 2),
            "declared_value_usd": lambda: random.randint(100000, 600000),
            "ad_cvd_rate": 0,
            "commodity_codes": ["2710", "2715", "7208"],  # Oil, steel
            "expected_outcome": "CLEARED",
            "expected_risk_level": "LOW",
        },
        "established_usmca_compliant": {
            "origin_country": lambda: random.choice(["CA", "MX"]),
            "destination_country": "US",
            "shipper_age_months": lambda: random.randint(60, 200),
            "element9_is_mismatch": False,
            "element9_declared_country": lambda: random.choice(["CA", "MX"]),
            "element9_actual_country": lambda: random.choice(["CA", "MX"]),
            "h2_signals": [],
            "dwell_days": lambda: random.randint(0, 1),
            "declared_value_usd": lambda: random.randint(80000, 400000),
            "ad_cvd_rate": 0,
            "commodity_codes": ["8704", "8705", "3902"],  # Vehicles, plastics
            "expected_outcome": "CLEARED",
            "expected_risk_level": "LOW",
        },
    }

    COMMODITY_NAMES = {
        "8541": "Semiconductor Devices",
        "8542": "Electronic Circuits",
        "2933": "Pharmaceutical Compounds",
        "7604": "Aluminum Extrusions",
        "7610": "Aluminum Structures",
        "7211": "Steel Flat Products",
        "8501": "Electric Motors",
        "8517": "Telecom Equipment",
        "2710": "Petroleum Oil",
        "2715": "Petroleum Waste",
        "6203": "Men's Garments",
        "6204": "Women's Garments",
        "6209": "Textiles",
        "3923": "Plastic Articles",
        "3926": "Plastic Fixtures",
        "3915": "Plastic Waste",
        "7208": "Steel Products",
        "8704": "Trucks",
        "8705": "Commercial Vehicles",
        "3902": "Plastic Polymers",
    }

    VESSEL_NAMES = [
        "MSC ALICE",
        "MSC MAYA",
        "MSC GULSUN",
        "OOCL INTEGRITY",
        "OOCL HARMONY",
        "EVERGREEN CONTAINER SHIP",
        "COSCO SHIPPING",
        "MAERSK LINE",
    ]

    SHIPPER_TEMPLATES = {
        "CN": ["Guangdong", "Shanghai", "Shenzhen", "Beijing"],
        "VN": ["Greenfield", "Sunward", "Pacific", "Orient"],
        "MY": ["Petronas", "Sunway", "Sime Darby", "YTL"],
        "CA": ["Bombardier", "Magna", "Linamar", "Descartes"],
        "MX": ["Nemak", "Grupo Modelo", "Gruma", "Cemex"],
        "SG": ["Keppel", "DBS", "Singtel", "Temasek"],
    }

    def __init__(self, seed: int = 42):
        random.seed(seed)

    def generate_shipment(self, pattern_name: str, pattern_config: Dict) -> SyntheticShipment:
        """Generate single shipment from pattern"""

        # Resolve callables (lambdas)
        def resolve(val):
            return val() if callable(val) else val

        origin = resolve(pattern_config["origin_country"])
        destination = resolve(pattern_config["destination_country"])

        # Generate shipper name
        shipper_prefix = random.choice(self.SHIPPER_TEMPLATES.get(origin, ["Company"]))
        shipper_name = (
            f"{shipper_prefix} {random.choice(['Trading', 'Manufacturing', 'Import/Export', 'Logistics'])} Co., Ltd."
        )

        # Select commodity
        commodity_code = random.choice(pattern_config["commodity_codes"])
        commodity_name = self.COMMODITY_NAMES.get(commodity_code, "General Merchandise")

        # Generate shipment
        shipment = SyntheticShipment(
            shipment_id=f"SYNTH-{random.randint(100000, 999999)}",
            origin_country=origin,
            destination_country=destination,
            shipper_name=shipper_name,
            commodity_code=commodity_code,
            commodity_name=commodity_name,
            declared_value_usd=resolve(pattern_config["declared_value_usd"]),
            declared_weight_kg=resolve(pattern_config["declared_value_usd"]) / random.uniform(100, 1000),
            element9_is_mismatch=resolve(pattern_config["element9_is_mismatch"]),
            element9_declared_country=resolve(pattern_config["element9_declared_country"]),
            element9_actual_country=resolve(pattern_config["element9_actual_country"]),
            h2_signals=pattern_config["h2_signals"],
            shipper_age_months=resolve(pattern_config["shipper_age_months"]),
            dwell_days=resolve(pattern_config["dwell_days"]),
            vessel_name=random.choice(self.VESSEL_NAMES),
            ad_cvd_applicable=pattern_config["ad_cvd_rate"] > 0,
            ad_cvd_rate=pattern_config["ad_cvd_rate"],
            expected_outcome=pattern_config["expected_outcome"],
            expected_risk_level=pattern_config["expected_risk_level"],
            pattern_type=pattern_name,
        )

        return shipment

    def generate_dataset(self, total_count: int = 5000) -> List[SyntheticShipment]:
        """Generate full synthetic dataset with specified distribution"""

        dataset = []

        # Calculate distribution
        high_risk_count = int(total_count * 0.30)
        medium_risk_count = int(total_count * 0.50)
        low_risk_count = int(total_count * 0.20)

        print(f"Generating {total_count} synthetic shipments...")
        print(f"  HIGH_RISK: {high_risk_count} (30%)")
        print(f"  MEDIUM_RISK: {medium_risk_count} (50%)")
        print(f"  LOW_RISK: {low_risk_count} (20%)")

        # Generate high-risk
        for _ in range(high_risk_count):
            pattern_name = random.choice(list(self.HIGH_RISK_PATTERNS.keys()))
            pattern = self.HIGH_RISK_PATTERNS[pattern_name]
            dataset.append(self.generate_shipment(pattern_name, pattern))

        # Generate medium-risk
        for _ in range(medium_risk_count):
            pattern_name = random.choice(list(self.MEDIUM_RISK_PATTERNS.keys()))
            pattern = self.MEDIUM_RISK_PATTERNS[pattern_name]
            dataset.append(self.generate_shipment(pattern_name, pattern))

        # Generate low-risk
        for _ in range(low_risk_count):
            pattern_name = random.choice(list(self.LOW_RISK_PATTERNS.keys()))
            pattern = self.LOW_RISK_PATTERNS[pattern_name]
            dataset.append(self.generate_shipment(pattern_name, pattern))

        # Shuffle
        random.shuffle(dataset)

        return dataset

    def save_to_json(self, dataset: List[SyntheticShipment], filepath: str):
        """Save dataset to JSON for validation"""
        data = [s.to_dict() for s in dataset]
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(dataset)} shipments to {filepath}")

    def print_statistics(self, dataset: List[SyntheticShipment]):
        """Print dataset statistics"""
        print("\n" + "=" * 60)
        print("SYNTHETIC DATASET STATISTICS")
        print("=" * 60)

        by_outcome = {}
        by_level = {}
        by_pattern = {}

        for s in dataset:
            by_outcome[s.expected_outcome] = by_outcome.get(s.expected_outcome, 0) + 1
            by_level[s.expected_risk_level] = by_level.get(s.expected_risk_level, 0) + 1
            by_pattern[s.pattern_type] = by_pattern.get(s.pattern_type, 0) + 1

        print("\nBy Expected Outcome:")
        for outcome, count in sorted(by_outcome.items()):
            print(f"  {outcome}: {count} ({count/len(dataset)*100:.1f}%)")

        print("\nBy Risk Level:")
        for level, count in sorted(by_level.items()):
            print(f"  {level}: {count} ({count/len(dataset)*100:.1f}%)")

        print("\nBy Pattern Type:")
        for pattern, count in sorted(by_pattern.items()):
            print(f"  {pattern}: {count}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    # Generate and save
    generator = SyntheticDataGenerator()
    dataset = generator.generate_dataset(5000)
    generator.print_statistics(dataset)
    generator.save_to_json(dataset, "/home/rahulvadera/cbp-sentry/services/api/synthetic_dataset_5000.json")
