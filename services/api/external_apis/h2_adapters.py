"""
Horizon 2 API Adapters — Pre-Intelligence Data (AIS/vessel tracking, Port authorities)
"""
import logging
from typing import Any, Dict
from datetime import datetime, timedelta
from .base_adapter import BaseAPIAdapter

logger = logging.getLogger(__name__)


class AISAdapter(BaseAPIAdapter):
    """AIS (Automatic Identification System) — vessel tracking, port dwell, routing anomalies"""

    def __init__(self):
        super().__init__("ais")

    async def fetch_live(self, vessel_name: str = None, imo: str = None, mmsi: str = None) -> Dict[str, Any]:
        """Fetch AIS data from MarineTraffic or AIS Hub"""
        # MarineTraffic API: https://help.marinetraffic.com/hc/en-us/articles/203990828
        # Free tier available but limited
        # AIS Hub: https://www.aishub.net/ (free access)

        logger.warning("AIS live API requires paid subscription - using fixture mode")
        return self.fetch_fixture(vessel_name=vessel_name, imo=imo, mmsi=mmsi)

    def fetch_fixture(self, vessel_name: str = None, imo: str = None, mmsi: str = None) -> Dict[str, Any]:
        """Return fixture AIS/vessel data with dwell anomalies"""
        vessels = {
            "pacific_horizon": {
                "name": "MV Pacific Horizon",
                "imo": "9876543",
                "mmsi": "577123456",
                "current_port": "Guangzhou",
                "current_position": {"lat": 22.3193, "lon": 113.9431},
                "last_port": "Da Nang",
                "port_dwell_days": 11.2,  # 5.3x baseline (2.1 days)
                "baseline_dwell_days": 2.1,
                "dwell_anomaly_percentile": 99,
                "port_sequence": ["Shanghai", "Da Nang", "Guangzhou", "Singapore"],
                "routing_flag": "UNUSUAL_DWELL",
                "ais_gaps": 2,  # Number of AIS signal gaps (transponder off)
                "est_arrival_port_of_discharge": "2025-06-01T14:30:00Z",
            },
        }

        # Match by vessel name
        for key, vessel in vessels.items():
            if vessel_name and vessel_name.lower() in vessel["name"].lower():
                return self.add_data_source_metadata(vessel)
            elif imo and vessel["imo"] == imo:
                return self.add_data_source_metadata(vessel)
            elif mmsi and vessel["mmsi"] == mmsi:
                return self.add_data_source_metadata(vessel)

        return self.add_data_source_metadata({"found": False, "error": "Vessel not found"})

    async def get_dwell_anomaly(self, vessel_name: str, port: str, dwell_days: float) -> Dict[str, Any]:
        """Calculate dwell time anomaly for a specific port"""
        # Baselines by port
        port_baselines = {
            "guangzhou": 2.1,
            "da nang": 1.8,
            "shanghai": 1.5,
            "singapore": 1.2,
        }

        baseline = port_baselines.get(port.lower(), 2.0)
        anomaly_ratio = dwell_days / baseline if baseline > 0 else 1.0

        return {
            "vessel": vessel_name,
            "port": port,
            "dwell_days": dwell_days,
            "baseline_days": baseline,
            "anomaly_ratio": round(anomaly_ratio, 1),
            "percentile": self._calculate_percentile(anomaly_ratio),
            "flag": "AIS_DWELL_ANOMALY" if anomaly_ratio > 3.0 else None,
        }

    @staticmethod
    def _calculate_percentile(ratio: float) -> int:
        """Convert dwell ratio to percentile (rough estimate)"""
        if ratio > 5: return 99
        if ratio > 3: return 95
        if ratio > 2: return 80
        if ratio > 1.5: return 60
        return 40


class PortAuthorityAdapter(BaseAPIAdapter):
    """Port Authority APIs — vessel arrivals, cargo manifests, container movements"""

    def __init__(self):
        super().__init__("port_authority")

    async def fetch_live(self, port_code: str, vessel_name: str) -> Dict[str, Any]:
        """Fetch port data from US Port Authority APIs (LA, LB, NY, etc.)"""
        # Port Authority APIs vary by port
        # Los Angeles/Long Beach: https://www.polb.com/
        # NY/NJ: https://www.panynj.gov/

        logger.warning("Port Authority APIs require authorization - using fixture mode")
        return self.fetch_fixture(port_code=port_code, vessel_name=vessel_name)

    def fetch_fixture(self, port_code: str, vessel_name: str) -> Dict[str, Any]:
        """Return fixture port activity data"""
        port_calls = {
            ("guangzhou", "pacific_horizon"): {
                "port_code": "CNGZ",
                "vessel_name": "MV Pacific Horizon",
                "arrival_date": "2025-05-12T08:30:00Z",
                "departure_date": "2025-05-23T14:00:00Z",
                "berth": "Terminal 1, Pier 3",
                "containers_loaded": 450,
                "containers_discharged": 120,
                "container_dwell_average_days": 4.2,
                "cargo_handling_rate_containers_per_hour": 35,
            },
            ("da_nang", "pacific_horizon"): {
                "port_code": "VNDAD",
                "vessel_name": "MV Pacific Horizon",
                "arrival_date": "2025-05-10T16:00:00Z",
                "departure_date": "2025-05-12T08:30:00Z",
                "berth": "Terminal A",
                "containers_loaded": 280,
                "containers_discharged": 60,
            },
        }

        # Normalize port code and vessel name for lookup
        key = (port_code.lower(), vessel_name.lower())
        for (lookup_port, lookup_vessel), data in port_calls.items():
            if lookup_port in port_code.lower() and lookup_vessel in vessel_name.lower():
                return self.add_data_source_metadata(data)

        return self.add_data_source_metadata({"found": False, "error": "Port call not found"})

    async def get_isf_stuffing_location(self, manifest_id: str, container_number: str) -> Dict[str, Any]:
        """Infer container stuffing location from port data and AIS"""
        # ISF Element 9: Location where cargo was actually stuffed
        # Compare with declared origin

        fixture_mapping = {
            "MFN-2025-0001": {
                "declared_origin": "VN",
                "actual_stuffing_location": "CN",  # Guangzhou
                "confidence": 0.98,
                "evidence": ["AIS dwell in Guangzhou", "Port manifests show loading from Guangzhou", "Vessel routing"],
                "flag": "ISF_MISMATCH",
            },
        }

        manifest_data = fixture_mapping.get(manifest_id)
        if manifest_data:
            return self.add_data_source_metadata(manifest_data)

        return self.add_data_source_metadata({"found": False})
