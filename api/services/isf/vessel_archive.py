"""Vessel data archival system for building historical intelligence dataset."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
from pathlib import Path
import aiosqlite
from .models import VesselInfo, VesselDataArchive, Element9Data, ISFData


class VesselArchiveDB:
    """SQLite-based archival database for vessel and ISF data."""

    def __init__(self, db_path: str = "/data/vessel_archive.db"):
        """Initialize archive database."""
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Initialize database schema."""
        self.db = await aiosqlite.connect(self.db_path)
        await self._create_schema()

    async def _create_schema(self):
        """Create archival tables."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        # Vessels table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS vessels (
                imo TEXT PRIMARY KEY,
                vessel_name TEXT NOT NULL,
                flag_country TEXT,
                vessel_type TEXT,
                length_m REAL,
                beam_m REAL,
                capacity_teu INTEGER,
                capacity_tonnes INTEGER,
                built_year INTEGER,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Port calls table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS port_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imo TEXT NOT NULL,
                port_code TEXT NOT NULL,
                port_name TEXT,
                country TEXT,
                arrival_date TIMESTAMP,
                departure_date TIMESTAMP,
                dwell_days INTEGER,
                latitude REAL,
                longitude REAL,
                recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (imo) REFERENCES vessels(imo)
            )
        """)

        # ISF filings table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS isf_filings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manifest_id TEXT UNIQUE,
                shipper_name TEXT,
                shipper_country TEXT,
                consignee_name TEXT,
                consignee_country TEXT,
                vessel_imo TEXT,
                vessel_name TEXT,
                element9_declared TEXT,
                element9_actual TEXT,
                element9_mismatch BOOLEAN,
                element9_risk_level TEXT,
                filing_date TIMESTAMP,
                recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_quality_score REAL,
                FOREIGN KEY (vessel_imo) REFERENCES vessels(imo)
            )
        """)

        # Dwell time patterns table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS dwell_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imo TEXT NOT NULL,
                port_code TEXT NOT NULL,
                avg_dwell_days REAL,
                min_dwell_days INTEGER,
                max_dwell_days INTEGER,
                sample_count INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (imo) REFERENCES vessels(imo)
            )
        """)

        # Routing patterns table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS routing_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imo TEXT NOT NULL,
                from_port TEXT NOT NULL,
                to_port TEXT NOT NULL,
                frequency INTEGER,
                avg_transit_days REAL,
                last_observed TIMESTAMP,
                FOREIGN KEY (imo) REFERENCES vessels(imo)
            )
        """)

        # Anomalies table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imo TEXT NOT NULL,
                anomaly_type TEXT,
                severity TEXT,
                description TEXT,
                detected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolution_status TEXT DEFAULT 'OPEN',
                FOREIGN KEY (imo) REFERENCES vessels(imo)
            )
        """)

        await self.db.commit()

    async def archive_vessel(self, vessel: VesselInfo):
        """Archive vessel data."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        metadata = json.dumps({
            "mmsi": vessel.mmsi,
            "last_position": vessel.last_position
        })

        await self.db.execute("""
            INSERT OR REPLACE INTO vessels
            (imo, vessel_name, flag_country, vessel_type, length_m, beam_m,
             capacity_teu, capacity_tonnes, built_year, last_updated, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vessel.imo, vessel.vessel_name, vessel.flag_country,
            vessel.vessel_type, vessel.length_m, vessel.beam_m,
            vessel.capacity_teu, vessel.capacity_metric_tonnes,
            vessel.built_year, datetime.utcnow(), metadata
        ))

        # Archive port calls
        for port_call in vessel.port_calls:
            await self.db.execute("""
                INSERT INTO port_calls
                (imo, port_code, port_name, country, arrival_date, departure_date,
                 dwell_days, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vessel.imo, port_call.port_code, port_call.port_name,
                port_call.country, port_call.arrival_date, port_call.departure_date,
                port_call.dwell_days, port_call.latitude, port_call.longitude
            ))

        await self.db.commit()

    async def archive_isf_filing(self, isf_data: ISFData):
        """Archive ISF filing with Element 9 analysis."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        vessel_imo = isf_data.vessel.imo if isf_data.vessel else isf_data.imo

        await self.db.execute("""
            INSERT OR REPLACE INTO isf_filings
            (manifest_id, shipper_name, shipper_country, consignee_name,
             consignee_country, vessel_imo, vessel_name,
             element9_declared, element9_actual, element9_mismatch,
             element9_risk_level, filing_date, data_quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            isf_data.manifest_id, isf_data.shipper_name, isf_data.shipper_country,
            isf_data.consignee_name, isf_data.consignee_country, vessel_imo,
            isf_data.vessel_name, isf_data.element_9.declared_country,
            isf_data.element_9.actual_stuffing_country, isf_data.element_9.is_mismatch,
            isf_data.element_9.risk_level, isf_data.filing_date,
            isf_data.data_completeness_pct
        ))

        await self.db.commit()

    async def get_vessel_dwell_history(self, imo: str, port: str, days: int = 90) -> List[Dict]:
        """Get dwell time history for vessel at specific port."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        cursor = await self.db.execute("""
            SELECT dwell_days, arrival_date, departure_date
            FROM port_calls
            WHERE imo = ? AND port_code = ? AND departure_date > ?
            ORDER BY departure_date DESC
        """, (imo, port, cutoff_date))

        rows = await cursor.fetchall()
        return [
            {
                "dwell_days": row[0],
                "arrival_date": row[1],
                "departure_date": row[2]
            }
            for row in rows
        ]

    async def get_vessel_routing_patterns(self, imo: str) -> List[Dict]:
        """Get common routing patterns for vessel."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        cursor = await self.db.execute("""
            SELECT from_port, to_port, frequency, avg_transit_days
            FROM routing_patterns
            WHERE imo = ?
            ORDER BY frequency DESC
        """, (imo,))

        rows = await cursor.fetchall()
        return [
            {
                "from_port": row[0],
                "to_port": row[1],
                "frequency": row[2],
                "avg_transit_days": row[3]
            }
            for row in rows
        ]

    async def detect_anomalies(self, imo: str, vessel: VesselInfo) -> List[str]:
        """Detect anomalies based on historical patterns."""
        anomalies = []

        if not self.db:
            raise RuntimeError("Database not initialized")

        # Check for unusual dwell patterns
        for port_call in vessel.port_calls[:3]:
            if port_call.dwell_days and port_call.dwell_days > 14:
                # Fetch historical average
                cursor = await self.db.execute("""
                    SELECT AVG(dwell_days) FROM port_calls
                    WHERE imo = ? AND port_code = ?
                """, (imo, port_call.port_code))

                result = await cursor.fetchone()
                if result and result[0]:
                    avg_dwell = result[0]
                    if port_call.dwell_days > avg_dwell * 3:
                        anomalies.append(
                            f"Unusual dwell at {port_call.port_code}: "
                            f"{port_call.dwell_days}d vs avg {avg_dwell:.1f}d"
                        )

        # Check for route deviation
        if len(vessel.port_calls) > 1:
            cursor = await self.db.execute("""
                SELECT COUNT(*) as freq FROM routing_patterns
                WHERE imo = ? AND from_port = ? AND to_port = ?
            """, (imo, vessel.port_calls[0].port_code, vessel.port_calls[1].port_code))

            result = await cursor.fetchone()
            if result and result[0] == 0:
                anomalies.append(
                    f"Unusual route: {vessel.port_calls[0].port_code} → "
                    f"{vessel.port_calls[1].port_code}"
                )

        return anomalies

    async def get_summary_stats(self) -> Dict:
        """Get archive summary statistics."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        stats = {}

        # Total vessels
        cursor = await self.db.execute("SELECT COUNT(*) FROM vessels")
        stats["total_vessels"] = (await cursor.fetchone())[0]

        # Total port calls
        cursor = await self.db.execute("SELECT COUNT(*) FROM port_calls")
        stats["total_port_calls"] = (await cursor.fetchone())[0]

        # Total ISF filings
        cursor = await self.db.execute("SELECT COUNT(*) FROM isf_filings")
        stats["total_isf_filings"] = (await cursor.fetchone())[0]

        # Total anomalies detected
        cursor = await self.db.execute("SELECT COUNT(*) FROM anomalies WHERE resolution_status = 'OPEN'")
        stats["open_anomalies"] = (await cursor.fetchone())[0]

        # High-risk Element 9 mismatches
        cursor = await self.db.execute("""
            SELECT COUNT(*) FROM isf_filings
            WHERE element9_mismatch = TRUE AND element9_risk_level = 'HIGH'
        """)
        stats["high_risk_mismatches"] = (await cursor.fetchone())[0]

        return stats

    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()


class VesselIntelligenceBuilder:
    """Build intelligence products from archived vessel data."""

    def __init__(self, archive_db: VesselArchiveDB):
        """Initialize intelligence builder."""
        self.archive_db = archive_db

    async def get_vessel_risk_profile(self, imo: str) -> Dict:
        """Build risk profile for vessel based on historical data."""
        vessel_cursor = await self.archive_db.db.execute("""
            SELECT vessel_name, flag_country, vessel_type FROM vessels WHERE imo = ?
        """, (imo,))
        vessel_row = await vessel_cursor.fetchone()

        if not vessel_row:
            return {"status": "not_found"}

        # Anomalies
        anomaly_cursor = await self.archive_db.db.execute("""
            SELECT COUNT(*) FROM anomalies WHERE imo = ? AND resolution_status = 'OPEN'
        """, (imo,))
        anomaly_count = (await anomaly_cursor.fetchone())[0]

        # ISF mismatches
        mismatch_cursor = await self.archive_db.db.execute("""
            SELECT COUNT(*) FROM isf_filings
            WHERE vessel_imo = ? AND element9_mismatch = TRUE
        """, (imo,))
        mismatch_count = (await mismatch_cursor.fetchone())[0]

        return {
            "imo": imo,
            "vessel_name": vessel_row[0],
            "flag_country": vessel_row[1],
            "vessel_type": vessel_row[2],
            "open_anomalies": anomaly_count,
            "element9_mismatches": mismatch_count,
            "risk_level": "HIGH" if (anomaly_count > 2 or mismatch_count > 3) else "MEDIUM" if (anomaly_count > 0 or mismatch_count > 0) else "LOW",
        }

    async def get_corridor_intelligence(self, origin: str, destination: str) -> Dict:
        """Analyze patterns for origin → destination corridor."""
        cursor = await self.archive_db.db.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN element9_mismatch THEN 1 END) as mismatches,
                   AVG(data_quality_score) as avg_quality
            FROM isf_filings
            WHERE shipper_country = ? AND consignee_country = ?
        """, (origin, destination))

        result = await cursor.fetchone()
        if not result or result[0] == 0:
            return {"status": "no_data"}

        return {
            "corridor": f"{origin} → {destination}",
            "total_filings": result[0],
            "mismatches": result[1],
            "mismatch_rate": result[1] / result[0] if result[0] > 0 else 0,
            "avg_data_quality": result[2],
        }

    async def export_intelligence_report(self, output_path: str):
        """Export archival intelligence as JSON report."""
        stats = await self.archive_db.get_summary_stats()

        report = {
            "generated": datetime.utcnow().isoformat(),
            "summary": stats,
            "export_path": output_path
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        return report
