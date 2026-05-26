"""
Referral package API routes.

⚠️ DEPRECATION WARNING:
This module uses FIXTURE DATA only. For production entity graphs, use:
- GET /api/referral/{shipment_id}/entity-graph (Phase 2, in development)

The fixture endpoints will be removed in v2.0 (target: Q3 2026).
See ENTITY_GRAPH_OPTION3_STRATEGY.md for migration path.

Endpoints (DEPRECATED):
- GET /api/referral/{manifest_id} ← FIXTURE DATA
- GET /api/referral/{manifest_id}/summary ← FIXTURE DATA
- POST /api/referral/export-pdf ← FIXTURE DATA

New Endpoints (Phase 2+):
- GET /api/referral/{shipment_id}/entity-graph ← REAL DATA
"""

import logging
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel
from models.schemas import ReferralPackageResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from services.referral.cord_client import CORDClient
from services.referral.entity_graph_service import EntityGraphService
from services.isf.isf_service import ISFEnrichmentService
from services.isf.models import ISFEnrichmentRequest
from services.isf.vessel_tracker import VesselTrackerClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{manifest_id}", response_model=ReferralPackageResponse)
async def get_referral_package(manifest_id: str) -> ReferralPackageResponse:
    """
    ⚠️ DEPRECATED: Get referral package for a shipment.

    **This endpoint returns FIXTURE DATA only.**

    For production use, call: GET /api/referral/{shipment_id}/entity-graph
    (Coming in Phase 2 - uses real CORD entity resolution + ISF enrichment)

    Will be removed in v2.0 (target: Q3 2026).

    Args:
        manifest_id: Manifest identifier

    Returns:
        Complete referral package with all 14 sections (FIXTURE DATA)
    """
    logger.warning(
        f"⚠️ DEPRECATED: get_referral_package({manifest_id}) called with FIXTURE DATA. "
        f"Use GET /api/referral/{{shipment_id}}/entity-graph for real data."
    )

    try:
        # TODO: Load referral package from database using manifest_id
        # For now, return fixture for all cases (until real DB integration)
        if manifest_id and len(manifest_id) > 0:
            sections_data = {
                "shipment_id": {
                        "bill_id": "BL123456789",
                        "manifest_id": manifest_id,
                        "shipper": "Greenfield Industrial Trading Co., Ltd.",
                        "shipper_country": "VN",
                        "consignee": "SunPath Energy Distributors LLC",
                        "consignee_country": "US",
                        "hts_code": "7604.10.1000",
                        "hts_description": "Aluminum extrusions",
                        "declared_value_usd": 450000.0,
                        "total_weight_kg": 22500.0,
                        "weight_mt": 22.5,
                        "vessel_name": "MV Pacific Horizon",
                        "port_of_lading": "Guangzhou",
                        "port_of_discharge": "Los Angeles",
                        "eta": "2026-06-15"
                    },
                    "line_items": [
                        {
                            "sku": "GF-EXT-001",
                            "description": "Aluminum extrusion profile, 6063-T5",
                            "quantity_kg": 22500.0,
                            "hts_code": "7604.10.1000",
                            "weight_mt": 22.5,
                            "declared_value_usd": 450000.0,
                            "duty_rate": 0.0,
                            "estimated_duty_usd": 0.0
                        }
                    ],
                    "routing_history": [
                        {
                            "location": "Guangzhou",
                            "country": "CN",
                            "date": "2026-05-18",
                            "event": "Loaded on vessel",
                            "ais_anomaly": True,
                            "dwell_days": 11.2,
                            "baseline_days": 2.1,
                            "anomaly_ratio": 5.3
                        },
                        {
                            "location": "Los Angeles",
                            "country": "US",
                            "date": "2026-06-15",
                            "event": "ETA",
                            "ais_anomaly": False
                        }
                    ],
                    "parties": [
                        {
                            "role": "SHIPPER",
                            "name": "Greenfield Industrial Trading Co., Ltd.",
                            "country": "VN",
                            "senzing_id": 1001,
                            "risk_score": 65.0,
                            "confidence": 0.95
                        },
                        {
                            "role": "MANUFACTURER",
                            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                            "country": "CN",
                            "senzing_id": 1002,
                            "risk_score": 78.0,
                            "confidence": 0.98
                        },
                        {
                            "role": "CONSIGNEE",
                            "name": "SunPath Energy Distributors LLC",
                            "country": "US",
                            "senzing_id": 1003,
                            "risk_score": 42.0,
                            "confidence": 0.87
                        }
                    ],
                    "ownership_chain": [
                        {
                            "level": 1,
                            "entity": "Greenfield Industrial Trading Co., Ltd.",
                            "jurisdiction": "VN",
                            "relationship": "Direct shipper",
                            "confidence": 0.95
                        },
                        {
                            "level": 2,
                            "entity": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                            "jurisdiction": "CN",
                            "relationship": "Parent manufacturer",
                            "confidence": 0.98
                        },
                        {
                            "level": 3,
                            "entity": "Greenfield Global Metals Holdings Ltd.",
                            "jurisdiction": "HK",
                            "relationship": "Holding company",
                            "confidence": 0.92
                        }
                    ],
                    "import_pattern": [
                        {
                            "month": "2026-05",
                            "shipments": 1,
                            "weight_kg": 22500.0,
                            "declared_origin": "VN",
                            "unit_value": 20.0
                        }
                    ],
                    "trade_flow": {
                        "hts_code": "7604.10.1000",
                        "ad_cvd_status": "ACTIVE",
                        "china_rate": 374.15,
                        "vietnam_rate": 0.0,
                        "duty_evasion_incentive": "HIGH",
                        "trade_corridor_risk": "HIGH"
                    },
                    "document_review": [
                        {
                            "type": "ISF",
                            "filed_date": "2026-05-18",
                            "shipper_declared": "Greenfield Industrial Trading Co., Ltd.",
                            "origin_declared": "VN",
                            "element_9": "CN",
                            "status": "MISMATCH"
                        }
                    ],
                    "document_consistency": [
                        {
                            "issue": "ISF Element 9 mismatch",
                            "type": "CRITICAL",
                            "evidence": "Filed as CN, declared as VN"
                        }
                    ],
                    "manufacturing_verification": {
                        "true_manufacturer": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                        "factory_location": "Guangzhou, China",
                        "facility_confirmed": False,
                        "production_records": "Not provided",
                        "certificates": "Missing",
                        "prior_filings": 9
                    },
                    "risk_indicators": [
                        {
                            "indicator": "Shipper age",
                            "severity": "MEDIUM",
                            "evidence": "14 months old",
                            "confidence": 0.92
                        },
                        {
                            "indicator": "AIS dwell anomaly",
                            "severity": "HIGH",
                            "evidence": "11.2 days vs. 2.1-day baseline",
                            "confidence": 0.95
                        },
                        {
                            "indicator": "China parent company",
                            "severity": "HIGH",
                            "evidence": "Parent in AD/CVD jurisdiction",
                            "confidence": 0.98
                        }
                    ],
                    "score_breakdown": {
                        "total": 91,
                        "confidence_tier": "HIGH",
                        "components": [
                            {
                                "name": "Origin Doc Gap",
                                "tier": 4,
                                "score": 25,
                                "max": 25,
                                "percentage": 100.0,
                                "description": "Probable fraudulent origin documentation"
                            },
                            {
                                "name": "Commodity Sensitivity",
                                "tier": 3,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "AD/CVD-sensitive aluminum extrusions"
                            },
                            {
                                "name": "Routing Consistency",
                                "tier": 2,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "Anomalous port dwell time"
                            },
                            {
                                "name": "Party Profile Risk",
                                "tier": 1,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "China parent, Vietnam intermediary"
                            },
                            {
                                "name": "Historical Pattern",
                                "tier": 3,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "High-risk commodity with price below market"
                            },
                            {
                                "name": "Time Sensitivity",
                                "tier": 4,
                                "score": 11,
                                "max": 15,
                                "percentage": 73.3,
                                "description": "Time-critical shipment during high-scrutiny period"
                            }
                        ]
                    },
                    "what_if_scenarios": [
                        {
                            "scenario": "If shipper were 36+ months old",
                            "assumption": "Company age risk decreased",
                            "expected_score": 85,
                            "key_differences": "Party Profile Risk: 15 → 10 (-5 points)"
                        },
                        {
                            "scenario": "If no China parent company",
                            "assumption": "No direct AD/CVD connection",
                            "expected_score": 72,
                            "key_differences": "Origin Doc Gap: 25 → 15 (-10 points)"
                        }
                    ],
                    "data_sources": [
                        {
                            "name": "Senzing Entity Resolution",
                            "confidence": 0.95,
                            "data_element": "Party relationships"
                        },
                        {
                            "name": "ISF Manifest",
                            "confidence": 0.99,
                            "data_element": "Element 9, declared origin"
                        },
                        {
                            "name": "AIS Vessel Tracking",
                            "confidence": 0.99,
                            "data_element": "Port dwell times"
                        },
                        {
                            "name": "AD/CVD Orders",
                            "confidence": 1.0,
                            "data_element": "Commodity rate information"
                        }
                    ]
                }

            # Transform sections to UI-expected structure (section_3_X keys)
            transformed_sections = {
                "section_3_1_shipment_identification": sections_data["shipment_id"],
                "section_3_2_line_items": sections_data["line_items"],
                "section_3_3_routing_history": sections_data["routing_history"],
                "section_3_4_parties_and_roles": {"parties": sections_data["parties"]},
                "section_3_5_entity_ownership_chain": {"chain": sections_data["ownership_chain"]},
                "section_3_6_import_pattern": sections_data["import_pattern"],
                "section_3_7_trade_flow": sections_data["trade_flow"],
                "section_3_8_document_review": {"documents": sections_data["document_review"]},
                "section_3_9_document_consistency": sections_data["document_consistency"],
                "section_3_10_supplier_verification": sections_data["manufacturing_verification"],
                "section_3_11_risk_indicators": sections_data["risk_indicators"],
                "section_3_12_score_breakdown": sections_data["score_breakdown"],
                "section_3_13_what_if_scenarios": sections_data["what_if_scenarios"],
                "section_3_14_data_sources": sections_data["data_sources"],
            }

            return {
                "package_id": f"ref_{manifest_id}",
                "shipment_id": manifest_id,
                "confidence_level": "HIGH",
                "score": 91,
                "recommended_action": "EXAMINE",
                "sections": transformed_sections
            }

        # Default for unknown manifest
        raise HTTPException(status_code=404, detail=f"Referral package not found for {manifest_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Referral package lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{manifest_id}/summary")
async def get_referral_summary(manifest_id: str) -> Dict[str, Any]:
    """
    Get summary of referral package.

    Args:
        manifest_id: Manifest identifier

    Returns:
        Summary with key metrics
    """
    try:
        if manifest_id and len(manifest_id) > 0:
            return {
                "manifest_id": manifest_id,
                "score": 91,
                "confidence_tier": "HIGH",
                "recommended_action": "EXAMINE",
                "top_risks": [
                    "China parent company (manufacturer resolves to AD/CVD jurisdiction)",
                    "ISF Element 9 mismatch (CN filed, VN declared)",
                    "Anomalous port dwell (11.2d vs. 2.1d baseline)"
                ],
                "referral_justification": "High-confidence transshipment indicators warrant port examination and manufacturer verification."
            }

        raise HTTPException(status_code=404, detail=f"Referral summary not found for {manifest_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Referral summary lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PDFExportRequest(BaseModel):
    """Request model for PDF export"""
    case_id: str
    shipment_id: str
    risk_score: int
    recommendation: str
    shipper_name: str
    commodity_name: str
    origin_country: str
    destination_country: str
    shipment_narrative: str


@router.post("/export-pdf")
async def export_referral_pdf(request: PDFExportRequest) -> FileResponse:
    """
    Generate and export a CBP EAPA referral package PDF.

    Args:
        request: PDF export request with referral data

    Returns:
        PDF file as FileResponse
    """
    try:
        logger.info(f"Generating PDF for case: {request.case_id}")

        # Create PDF in memory
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#CCCCCC'),
            borderPadding=6
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            leading=12
        )

        # Build document content
        content = []

        # Header
        content.append(Paragraph("CBP EAPA REFERRAL PACKAGE", title_style))
        content.append(Paragraph("19 USC § 1516a — ENHANCED PENALTY ASSESSMENT", subtitle_style))
        content.append(Spacer(1, 0.2*inch))

        # Metadata table
        metadata = [
            ['Case ID:', request.case_id, 'Date:', datetime.now().strftime('%m/%d/%Y')],
            ['Risk Score:', f"{request.risk_score}/100", 'Status:', 'SUBMITTED'],
        ]
        metadata_table = Table(metadata, colWidths=[1.2*inch, 1.8*inch, 1.2*inch, 1.8*inch])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        content.append(metadata_table)
        content.append(Spacer(1, 0.3*inch))

        # Executive Summary
        content.append(Paragraph("EXECUTIVE SUMMARY & RECOMMENDATION", heading_style))
        content.append(Paragraph(f"<b>RECOMMENDATION: {request.recommendation}</b>", normal_style))
        content.append(Paragraph(f"Risk Score: {request.risk_score}/100 • {'CRITICAL' if request.risk_score >= 80 else 'ELEVATED'}", normal_style))
        content.append(Spacer(1, 0.1*inch))

        summary_text = f"Investigation of {request.shipper_name} shipment {request.shipment_id} reveals systematic trade compliance indicators. Multi-factor risk assessment scored {request.risk_score}/100 across 7 dimensions. Recommend {request.recommendation.lower()} per 19 USC § 1516a."
        content.append(Paragraph(summary_text, normal_style))
        content.append(Spacer(1, 0.2*inch))

        # Statutory Sections
        content.append(Paragraph("STATUTORY SECTIONS & EVIDENCE", heading_style))
        sections_text = f"""
        <b>Table 3-1:</b> Shipper {request.shipper_name} • Origin {request.origin_country} • Destination {request.destination_country}<br/>
        <b>Table 3-2:</b> Commodity {request.commodity_name}<br/>
        <b>Table 3-3 to 3-10:</b> Parties, Entity Chain, Trade Flow, Document Review, Manufacturing Verification<br/>
        <b>Table 3-11 to 3-14:</b> Risk Indicators, Score Breakdown, Scenarios, Data Sources
        """
        content.append(Paragraph(sections_text, normal_style))
        content.append(Spacer(1, 0.2*inch))

        # Officer Narrative
        content.append(Paragraph("OFFICER NARRATIVE & FINDINGS", heading_style))
        content.append(Paragraph(request.shipment_narrative or "(Officer narrative generated during investigation)", normal_style))
        content.append(Spacer(1, 0.2*inch))

        # Final Determination
        content.append(Paragraph("FINAL DETERMINATION", heading_style))
        content.append(Paragraph(f"<b>RECOMMENDATION: {request.recommendation}</b>", normal_style))
        final_text = f"This referral package includes all 14 statutory sections required for Import Safety Bureau review under 19 USC § 1516a. Evidence supports {request.recommendation.lower()} action. All supporting documentation, ML risk scoring methodology, and officer findings are included herein."
        content.append(Paragraph(final_text, normal_style))
        content.append(Spacer(1, 0.15*inch))
        content.append(Paragraph(
            f"Submitted: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')} | Risk Score: {request.risk_score}/100 | Case: {request.case_id}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#999999'))
        ))

        # Build PDF
        doc.build(content)

        # Reset buffer position
        pdf_buffer.seek(0)

        filename = f"CBP-EAPA-Referral-{request.case_id}-{datetime.now().strftime('%Y-%m-%d')}.pdf"
        logger.info(f"PDF generated successfully: {filename}")

        return FileResponse(
            pdf_buffer,
            media_type='application/pdf',
            filename=filename
        )

    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/{shipment_id}/entity-graph")
async def get_entity_graph(shipment_id: str) -> Dict[str, Any]:
    """
    Get entity relationship graph for a shipment with ISF enrichment + CORD resolution.

    This endpoint integrates:
    1. ISF enrichment (Element 9 analysis, vessel tracking, dwell anomalies)
    2. CORD entity resolution (3-level ownership chain via Senzing)
    3. Entity graph transformation (to Entity[] format for frontend visualization)

    Args:
        shipment_id: Shipment identifier (manifest_id)

    Returns:
        Entity graph with chain (Entity[]), data_sources, ofac_detected, risk_score, etc.
        Includes ISF warnings merged into shipper node.

    Raises:
        HTTPException 404: Shipment not found
        HTTPException 503: CORD or ISF service unavailable
        HTTPException 500: Internal processing error
    """
    logger.info(f"🔍 Entity graph request for shipment: {shipment_id}")

    try:
        # Step 1: Fetch shipment data
        # TODO: Load from database. For now, use fixture for greenfield demo.
        shipment_data = _get_shipment_data(shipment_id)
        if not shipment_data:
            raise HTTPException(
                status_code=404,
                detail=f"Shipment {shipment_id} not found"
            )

        logger.info(f"Loaded shipment: {shipment_data['shipper']} → {shipment_data['consignee']}")

        # Step 2: Enrich with ISF data (Element 9 analysis, vessel tracking)
        vessel_tracker = VesselTrackerClient()
        isf_service = ISFEnrichmentService(vessel_tracker)

        isf_request = ISFEnrichmentRequest(
            manifest_id=shipment_id,
            shipper_name=shipment_data["shipper"],
            shipper_country=shipment_data["shipper_country"],
            consignee_name=shipment_data["consignee"],
            consignee_country=shipment_data["consignee_country"],
            vessel_name=shipment_data.get("vessel_name"),
            imo=shipment_data.get("imo"),
            declared_origin=shipment_data.get("isf_stuffing_country"),
            hs_code=shipment_data.get("hts_code"),
        )

        isf_response = await isf_service.enrich_manifest(isf_request)
        logger.info(f"ISF enrichment complete: {isf_response.status}")

        if isf_response.status == "error":
            logger.warning(f"ISF enrichment warning: {isf_response.error_reason}")
            # Continue with CORD resolution; ISF data is optional

        isf_data = isf_response.isf_data if isf_response.isf_data else {}

        # Step 3: Resolve entity chain via CORD
        cord_client = CORDClient()

        # Prepare context dict with ISF findings for CORD
        context = {}
        if isf_data and hasattr(isf_data, 'element_9'):
            element_9 = isf_data.element_9
            context = {
                "element_9_mismatch": element_9.is_mismatch,
                "stuffing_country": element_9.actual_stuffing_country,
                "stuffing_port": element_9.port_of_loading,
                "dwell_anomaly": False,  # Would be set if dwell > threshold
                "new_shipper": False,  # Would check shipper age
                "declared_origin": element_9.declared_country,
            }

        cord_response = await cord_client.resolve_shipment_entities(
            shipper_name=shipment_data["shipper"],
            shipper_country=shipment_data["shipper_country"],
            consignee_name=shipment_data["consignee"],
            consignee_country=shipment_data["consignee_country"],
            context=context if context else None,
        )

        if cord_response is None:
            logger.warning(f"CORD resolution failed for {shipment_id}")
            raise HTTPException(
                status_code=503,
                detail="Entity resolution service (CORD) unavailable"
            )

        logger.info(f"CORD resolution success")

        # Step 4: Transform to Entity[] format
        entity_graph = EntityGraphService.transform_cord_to_entity_chain(cord_response)
        logger.info(f"Entity graph transformed: {len(entity_graph['chain'])} levels")

        # Step 5: Merge ISF warnings into graph
        if isf_data:
            entity_graph = EntityGraphService.add_isf_warnings(entity_graph, isf_data.dict())
            logger.info(f"ISF warnings merged into entity graph")

        # Step 6: Add processing metadata
        entity_graph["shipment_id"] = shipment_id
        entity_graph["processing_timestamp"] = datetime.utcnow().isoformat()

        logger.info(f"✅ Entity graph complete for {shipment_id}")
        return entity_graph

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity graph generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Entity graph generation failed: {str(e)}"
        )


def _get_shipment_data(shipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch shipment data from database or fixtures.

    TODO: Replace with actual database query once manifest storage is implemented.
    Currently returns Greenfield demo fixture for testing.

    Args:
        shipment_id: Manifest or shipment identifier

    Returns:
        Shipment data dict with shipper, consignee, vessel info, or None if not found
    """
    # Demo fixture for Greenfield case
    if shipment_id == "greenfield" or shipment_id.startswith("mani_"):
        return {
            "manifest_id": shipment_id,
            "shipper": "Greenfield Industrial Trading Co., Ltd.",
            "shipper_country": "VN",
            "consignee": "SunPath Energy Distributors LLC",
            "consignee_country": "US",
            "vessel_name": "MV Pacific Horizon",
            "imo": "9876543",  # Example IMO
            "port_of_lading": "Guangzhou",
            "port_of_discharge": "Los Angeles",
            "isf_stuffing_country": "CN",
            "hts_code": "7604.10.1000",
            "hts_description": "Aluminum extrusions",
            "total_declared_value_usd": 450000.0,
            "total_weight_kg": 22500.0,
        }

    return None
