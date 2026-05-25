"""
Horizon 2 API Adapters — Pre-Intelligence Data (AIS/vessel tracking, Port authorities)
"""

import logging
import json
from typing import Any, Dict
from datetime import datetime, timedelta
from .base_adapter import BaseAPIAdapter

logger = logging.getLogger(__name__)


class AISAdapter(BaseAPIAdapter):
    """AIS (Automatic Identification System) — vessel tracking, port dwell, routing anomalies"""

    def __init__(self):
        super().__init__("ais")
        import os

        self.vesselfinder_api_key = os.getenv("VESSELAPI_KEY", "")

    async def fetch_live(
        self, vessel_name: str = None, imo: str = None, mmsi: str = None, manifest_fields: Dict = None
    ) -> Dict[str, Any]:
        """
        Fetch AIS data with priority:
        1. Use manifest-stored fields (PRIMARY - no API call needed)
        2. Query VesselFinder API if imo provided and VESSELAPI_KEY set
        3. Fall back to fixture data
        """
        # Step 1: Prefer manifest-stored fields (dwell_days, ais_stuffing_country, port_calls already in DB)
        if manifest_fields and manifest_fields.get("dwell_days"):
            logger.info(
                f"Using manifest AIS data: dwell_days={manifest_fields.get('dwell_days')} days, stuffing={manifest_fields.get('ais_stuffing_country')}"
            )
            return self._build_from_manifest(manifest_fields)

        # Step 2: Query VesselFinder API if key is configured and imo provided
        if self.vesselfinder_api_key and imo:
            logger.info(f"Querying VesselFinder API for IMO {imo}...")
            try:
                live_data = await self._fetch_vesselfinder(imo)
                if live_data and live_data.get("found"):
                    return self.add_data_source_metadata(live_data)
            except Exception as e:
                logger.warning(f"VesselFinder API failed: {e}, falling back to fixture")

        # Step 3: Fall back to fixture
        logger.info("Using fixture AIS data")
        return self.fetch_fixture(vessel_name=vessel_name, imo=imo, mmsi=mmsi)

    async def _fetch_vesselfinder(self, imo: str) -> Dict[str, Any]:
        """Query VesselFinder API for vessel information."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.vesselfinder.com/api/public/v4/vessel/search"
                params = {"imo": imo, "apikey": self.vesselfinder_api_key}
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "found": True,
                            "name": data.get("vessel", {}).get("shipname", ""),
                            "imo": imo,
                            "mmsi": data.get("vessel", {}).get("mmsi", ""),
                            "current_port": data.get("position", {}).get("port", ""),
                            "current_position": {
                                "lat": data.get("position", {}).get("latitude"),
                                "lon": data.get("position", {}).get("longitude"),
                            },
                            "last_updated": data.get("position", {}).get("timestamp", ""),
                            "source": "VesselFinder API",
                        }
                    else:
                        logger.warning(f"VesselFinder returned {resp.status}")
                        return {"found": False}
        except Exception as e:
            logger.warning(f"VesselFinder API error: {e}")
            return {"found": False}

    def _build_from_manifest(self, manifest_fields: Dict) -> Dict[str, Any]:
        """Build AIS response from manifest-stored fields."""
        port_calls = manifest_fields.get("port_calls", [])
        if isinstance(port_calls, str):
            try:
                port_calls = json.loads(port_calls)
            except:
                port_calls = []

        return self.add_data_source_metadata(
            {
                "found": True,
                "source": "Manifest (ISF Element 9 + AIS archive)",
                "name": manifest_fields.get("vessel_name", ""),
                "imo": manifest_fields.get("vessel_imo", ""),
                "dwell_days": manifest_fields.get("dwell_days", 0),
                "ais_stuffing_country": manifest_fields.get("ais_stuffing_country", ""),
                "port_calls": port_calls,
                "baseline_dwell_days": 2.0,
                "dwell_anomaly_percentile": self._calculate_dwell_percentile(manifest_fields.get("dwell_days", 0), 2.0),
            }
        )

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
        if ratio > 5:
            return 99
        if ratio > 3:
            return 95
        if ratio > 2:
            return 80
        if ratio > 1.5:
            return 60
        return 40

    @staticmethod
    def _calculate_dwell_percentile(dwell_days: float, baseline_days: float) -> int:
        """Calculate dwell percentile from actual vs baseline days."""
        if baseline_days <= 0:
            return 50
        ratio = dwell_days / baseline_days
        return AISAdapter._calculate_percentile(ratio)


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
