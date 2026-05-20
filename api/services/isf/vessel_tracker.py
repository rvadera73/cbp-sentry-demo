"""Vessel tracking client for VesselFinder API and AISStream WebSocket."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import aiohttp
from .models import VesselInfo, PortCall


class VesselTrackerClient:
    """Client for fetching vessel data from local archive first (RAG pattern), then VesselFinder API."""

    def __init__(self, vessel_archive_path: Optional[str] = None, vesselfinder_api_key: Optional[str] = None, aisstream_api_key: Optional[str] = None):
        """Initialize vessel tracker with RAG-first pattern.

        Args:
            vessel_archive_path: Path to local vessel archive database (default: data/vessel_archive.db)
            vesselfinder_api_key: Optional API key for VesselFinder (only if archive lookup fails)
            aisstream_api_key: Optional API key for AISStream WebSocket
        """
        self.vessel_archive_path = vessel_archive_path or "data/vessel_archive.db"
        self.vesselfinder_api_key = vesselfinder_api_key
        self.aisstream_api_key = aisstream_api_key
        self.vesselfinder_base_url = "https://api.vesselfinder.com/api/public/v4"
        self.aisstream_url = "wss://stream.aisstream.io/v0/stream"
        self.vessel_cache: Dict[str, tuple[VesselInfo, datetime]] = {}
        self.cache_ttl_hours = 24

        print(f"✅ VesselTrackerClient initialized with RAG-first pattern")
        print(f"   Archive: {self.vessel_archive_path}")
        print(f"   API fallback: {'Enabled' if vesselfinder_api_key else 'Disabled (use archive only)'}")

    async def get_vessel_info(self, imo: str) -> Optional[VesselInfo]:
        """Fetch vessel information by IMO — RAG-first pattern.

        Order:
        1. Check in-memory cache (fast, TTL 24h)
        2. Query local vessel archive (RAG, no API calls)
        3. Call VesselFinder API (if key configured + archive miss)
        4. Archive API response (for future RAG queries)
        5. Fall back to fixture data
        """
        # Step 1: Check in-memory cache (24h TTL)
        if imo in self.vessel_cache:
            vessel_info, cached_time = self.vessel_cache[imo]
            if datetime.utcnow() - cached_time < timedelta(hours=self.cache_ttl_hours):
                print(f"✅ {imo}: Found in memory cache")
                return vessel_info

        # Step 2: Query local vessel archive (RAG search - no API call)
        vessel_from_archive = self._query_vessel_archive(imo)
        if vessel_from_archive:
            print(f"✅ {imo}: Found in local archive (RAG lookup)")
            self.vessel_cache[imo] = (vessel_from_archive, datetime.utcnow())
            return vessel_from_archive

        # Step 3: Fall back to VesselFinder API if archive miss
        if not self.vesselfinder_api_key:
            print(f"ℹ️  {imo}: Not in archive, API key not configured. Using fixture data.")
            return self._get_fixture_vessel(imo)

        print(f"🔄 {imo}: Not in archive, querying VesselFinder API...")
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.vesselfinder_base_url}/vessel/search"
                params = {"imo": imo, "apikey": self.vesselfinder_api_key}
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        vessel_info = self._parse_vessel_info(data)
                        if vessel_info:
                            # Step 4: Archive API response for future RAG queries
                            self._archive_vessel(vessel_info)
                            self.vessel_cache[imo] = (vessel_info, datetime.utcnow())
                            print(f"✅ {imo}: Retrieved from API, archived for future lookups")
                            return vessel_info
                    else:
                        print(f"⚠️  {imo}: API returned {resp.status}. Using fixture.")
                        return self._get_fixture_vessel(imo)
        except Exception as e:
            print(f"⚠️  {imo}: API error: {e}. Using fixture.")
            return self._get_fixture_vessel(imo)

    async def get_vessel_position(self, imo: str) -> Optional[Dict]:
        """Get current position of vessel by IMO."""
        if not self.vesselfinder_api_key:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.vesselfinder_base_url}/vessel/position"
                params = {
                    "imo": imo,
                    "apikey": self.vesselfinder_api_key
                }
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"Error fetching vessel position for IMO {imo}: {e}")

        return None

    async def get_port_calls(self, imo: str, limit: int = 20) -> List[PortCall]:
        """Fetch port call history for a vessel — RAG-first pattern.

        Order:
        1. Query local archive (RAG - no API calls)
        2. Call VesselFinder API (if key configured + archive miss)
        3. Archive API response (for future queries)
        4. Fall back to fixture
        """
        # Step 1: Try local archive first (RAG pattern)
        archive_port_calls = self._query_port_calls_archive(imo, limit)
        if archive_port_calls:
            print(f"✅ {imo}: Found {len(archive_port_calls)} port calls in archive (RAG lookup)")
            return archive_port_calls

        # Step 2: Fall back to API if available
        if not self.vesselfinder_api_key:
            print(f"ℹ️  {imo}: Port calls not in archive, API key not configured. Using fixture.")
            fixture_vessel = self._get_fixture_vessel(imo)
            return fixture_vessel.port_calls if fixture_vessel else []

        print(f"🔄 {imo}: Port calls not in archive, querying VesselFinder API...")
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.vesselfinder_base_url}/vessel/portcalls"
                params = {"imo": imo, "limit": limit, "apikey": self.vesselfinder_api_key}
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        port_calls = self._parse_port_calls(data)
                        # Step 3: Archive API response
                        for port_call in port_calls:
                            self._archive_port_call(imo, port_call)
                        print(f"✅ {imo}: Retrieved {len(port_calls)} port calls from API, archived.")
                        return port_calls
                    else:
                        print(f"⚠️  {imo}: API returned {resp.status}. Using fixture.")
                        fixture_vessel = self._get_fixture_vessel(imo)
                        return fixture_vessel.port_calls if fixture_vessel else []
        except Exception as e:
            print(f"⚠️  {imo}: API error: {e}. Using fixture.")
            fixture_vessel = self._get_fixture_vessel(imo)
            return fixture_vessel.port_calls if fixture_vessel else []

    async def get_recent_dwell_time(self, imo: str, origin_port: str) -> Optional[int]:
        """Calculate recent dwell time at origin port."""
        port_calls = await self.get_port_calls(imo, limit=50)

        for i, call in enumerate(port_calls):
            if call.port_code.upper() == origin_port.upper():
                if call.departure_date and call.arrival_date:
                    dwell = (call.departure_date - call.arrival_date).days
                    return dwell

        return None

    def _parse_vessel_info(self, response: Dict) -> Optional[VesselInfo]:
        """Parse VesselFinder API response into VesselInfo."""
        if not response or "data" not in response:
            return None

        vessel_data = response.get("data", {})
        if not vessel_data:
            return None

        # Extract first result if multiple
        if isinstance(vessel_data, list) and len(vessel_data) > 0:
            vessel_data = vessel_data[0]

        try:
            vessel_info = VesselInfo(
                imo=vessel_data.get("imo", ""),
                mmsi=vessel_data.get("mmsi"),
                vessel_name=vessel_data.get("name", ""),
                flag_country=vessel_data.get("flagCountry", ""),
                vessel_type=vessel_data.get("type", ""),
                length_m=vessel_data.get("length"),
                beam_m=vessel_data.get("beam"),
                capacity_teu=vessel_data.get("teu"),
                built_year=vessel_data.get("yearBuilt"),
            )
            return vessel_info
        except Exception as e:
            print(f"Error parsing vessel info: {e}")
            return None

    def _parse_port_calls(self, response: Dict) -> List[PortCall]:
        """Parse VesselFinder port calls response."""
        port_calls = []

        if not response or "data" not in response:
            return port_calls

        calls_data = response.get("data", [])
        if not isinstance(calls_data, list):
            calls_data = [calls_data]

        for call in calls_data:
            try:
                arrival = None
                departure = None
                if call.get("arrival"):
                    arrival = datetime.fromisoformat(call["arrival"].replace("Z", "+00:00"))
                if call.get("departure"):
                    departure = datetime.fromisoformat(call["departure"].replace("Z", "+00:00"))

                dwell_days = None
                if arrival and departure:
                    dwell_days = (departure - arrival).days

                port_call = PortCall(
                    port_code=call.get("port", ""),
                    port_name=call.get("portName", ""),
                    country=call.get("country", ""),
                    arrival_date=arrival,
                    departure_date=departure,
                    dwell_days=dwell_days,
                    latitude=call.get("latitude"),
                    longitude=call.get("longitude"),
                )
                port_calls.append(port_call)
            except Exception as e:
                print(f"Error parsing port call: {e}")
                continue

        return port_calls

    def _query_vessel_archive(self, imo: str) -> Optional[VesselInfo]:
        """Query local vessel archive for IMO (RAG pattern - no API calls).

        This searches the local SQLite database for vessel data that was
        previously downloaded or cached from VesselFinder API.
        """
        try:
            # Try to import and use vessel_archive if available
            from .vessel_archive import VesselArchiveDB

            archive = VesselArchiveDB(self.vessel_archive_path)
            vessel_data = archive.get_vessel(imo)

            if vessel_data:
                # Convert from archive format to VesselInfo
                vessel_info = VesselInfo(
                    imo=vessel_data.get("imo"),
                    mmsi=vessel_data.get("mmsi"),
                    vessel_name=vessel_data.get("vessel_name"),
                    flag_country=vessel_data.get("flag_country"),
                    vessel_type=vessel_data.get("vessel_type"),
                    capacity_teu=vessel_data.get("capacity_teu"),
                    built_year=vessel_data.get("built_year"),
                )
                # Also get port calls
                port_calls = archive.get_port_calls(imo)
                if port_calls:
                    vessel_info.port_calls = port_calls

                return vessel_info
        except Exception as e:
            # Archive not available or error querying - continue to API
            pass

        return None

    def _query_port_calls_archive(self, imo: str, limit: int) -> Optional[List[PortCall]]:
        """Query local archive for port calls (RAG pattern)."""
        try:
            from .vessel_archive import VesselArchiveDB

            archive = VesselArchiveDB(self.vessel_archive_path)
            port_calls = archive.get_port_calls(imo)
            return port_calls[:limit] if port_calls else None
        except Exception:
            return None

    def _archive_port_call(self, imo: str, port_call: PortCall) -> None:
        """Archive a single port call to local database."""
        try:
            from .vessel_archive import VesselArchiveDB

            archive = VesselArchiveDB(self.vessel_archive_path)
            archive.archive_port_call(imo, port_call)
        except Exception:
            pass  # Silent fail - archiving is optional

    def _archive_vessel(self, vessel_info: VesselInfo) -> None:
        """Archive vessel data to local database for future RAG queries."""
        try:
            from .vessel_archive import VesselArchiveDB

            archive = VesselArchiveDB(self.vessel_archive_path)
            archive.archive_vessel(vessel_info)
            if vessel_info.port_calls:
                for port_call in vessel_info.port_calls:
                    archive.archive_port_call(vessel_info.imo, port_call)
            print(f"💾 {vessel_info.imo}: Archived {len(vessel_info.port_calls or [])} port calls")
        except Exception as e:
            print(f"⚠️  Error archiving vessel {vessel_info.imo}: {e}")

    def _get_fixture_vessel(self, imo: str) -> Optional[VesselInfo]:
        """Return fixture vessel data for known test cases."""
        fixtures = {
            "9710399": VesselInfo(
                imo="9710399",
                mmsi="215378120",
                vessel_name="MV Pacific Horizon",
                flag_country="PA",
                vessel_type="Container Ship",
                capacity_teu=8063,
                built_year=2013,
                port_calls=[
                    PortCall(
                        port_code="CNSHA",
                        port_name="Shanghai",
                        country="CN",
                        arrival_date=datetime(2026, 4, 15, 10, 0),
                        departure_date=datetime(2026, 4, 26, 14, 0),
                        dwell_days=11
                    ),
                    PortCall(
                        port_code="SGSIN",
                        port_name="Singapore",
                        country="SG",
                        arrival_date=datetime(2026, 5, 2, 8, 0),
                        departure_date=datetime(2026, 5, 4, 16, 0),
                        dwell_days=2
                    ),
                    PortCall(
                        port_code="USNYC",
                        port_name="Newark",
                        country="US",
                        arrival_date=datetime(2026, 5, 18, 12, 0),
                        departure_date=None,
                        dwell_days=None
                    )
                ]
            ),
            "9387456": VesselInfo(  # Solaria Solar Express
                imo="9387456",
                vessel_name="MV Solar Express",
                flag_country="SG",
                vessel_type="Container Ship",
                capacity_teu=5800,
                port_calls=[
                    PortCall(
                        port_code="MYKL",
                        port_name="Kuala Lumpur",
                        country="MY",
                        arrival_date=datetime(2026, 5, 5, 10, 0),
                        departure_date=datetime(2026, 5, 11, 14, 0),
                        dwell_days=6  # 6 days vs 2.3 baseline = 2.6x > 2.5x threshold
                    ),
                    PortCall(
                        port_code="USLA",
                        port_name="Los Angeles",
                        country="US",
                        arrival_date=datetime(2026, 5, 20, 8, 0),
                        departure_date=None,
                        dwell_days=None
                    )
                ]
            ),
            "9658424": VesselInfo(
                imo="9658424",
                vessel_name="MV Eastern Promise",
                flag_country="SG",
                vessel_type="Container Ship",
                capacity_teu=6700
            ),
            "9642187": VesselInfo(
                imo="9642187",
                vessel_name="MV Hanoi Star",
                flag_country="PH",
                vessel_type="Container Ship",
                capacity_teu=5500,
                port_calls=[
                    PortCall(
                        port_code="VNSGN",
                        port_name="Ho Chi Minh City",
                        country="VN",
                        arrival_date=datetime(2026, 5, 1, 10, 0),
                        departure_date=datetime(2026, 5, 4, 14, 0),
                        dwell_days=3  # 3 days = normal, within baseline
                    ),
                    PortCall(
                        port_code="USNYC",
                        port_name="Newark",
                        country="US",
                        arrival_date=datetime(2026, 5, 15, 8, 0),
                        departure_date=None,
                        dwell_days=None
                    )
                ]
            ),
            "9845921": VesselInfo(  # Singapore Direct
                imo="9845921",
                vessel_name="MV Singapore Link",
                flag_country="SG",
                vessel_type="Container Ship",
                capacity_teu=5000,
                port_calls=[
                    PortCall(
                        port_code="SGSIN",
                        port_name="Singapore",
                        country="SG",
                        arrival_date=datetime(2026, 5, 3, 10, 0),
                        departure_date=datetime(2026, 5, 4, 16, 0),
                        dwell_days=1  # Very short dwell
                    ),
                    PortCall(
                        port_code="USLB",
                        port_name="Long Beach",
                        country="US",
                        arrival_date=datetime(2026, 5, 16, 12, 0),
                        departure_date=None,
                        dwell_days=None
                    )
                ]
            ),
        }

        return fixtures.get(imo)

    def clear_cache(self):
        """Clear vessel cache."""
        self.vessel_cache.clear()

    async def health_check(self) -> Dict[str, any]:
        """Check API health status."""
        status = {
            "vesselfinder_available": False,
            "aisstream_available": False,
            "cache_entries": len(self.vessel_cache),
        }

        if self.vesselfinder_api_key:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.vesselfinder_base_url}/vessel/search"
                    params = {"imo": "9999999", "apikey": self.vesselfinder_api_key}
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        status["vesselfinder_available"] = resp.status in [200, 400]
            except Exception:
                pass

        return status
