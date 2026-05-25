"""Professional CBP EAPA Referral Package PDF Generator

Generates comprehensive, well-formatted referral package PDFs from shipment data.
Uses reportlab for professional formatting with proper error handling.
"""

import io
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

logger = logging.getLogger(__name__)


class CBPReferralPDFGenerator:
    """Generates professional CBP EAPA referral package PDFs."""

    # Design system colors matching UI
    COLOR_PRIMARY = "#005EA2"  # CBP Blue
    COLOR_DANGER = "#D83933"  # Red for critical
    COLOR_WARNING = "#FFBE2E"  # Yellow for medium
    COLOR_SUCCESS = "#07A41E"  # Green for low
    COLOR_NEUTRAL = "#F7F9FC"  # Light background
    COLOR_DARK = "#0B1F33"  # Dark text
    COLOR_HEADER_BG = "#E8F0F8"  # Light blue for headers

    # Margins and sizing
    PAGE_WIDTH = letter[0]
    PAGE_HEIGHT = letter[1]
    MARGIN = 0.5 * inch
    CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

    def __init__(self):
        self.styles = self._create_styles()

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create all paragraph styles for consistent formatting."""
        base_styles = getSampleStyleSheet()
        styles = {}

        # Cover page title
        styles["cover_title"] = ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor(self.COLOR_PRIMARY),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        # Section headings
        styles["section_heading"] = ParagraphStyle(
            "SectionHeading",
            parent=base_styles["Heading2"],
            fontSize=11,
            textColor=colors.HexColor(self.COLOR_PRIMARY),
            spaceAfter=8,
            spaceBefore=8,
            fontName="Helvetica-Bold",
            borderColor=colors.HexColor(self.COLOR_PRIMARY),
            borderWidth=2,
            borderPadding=4,
        )

        # Table headings
        styles["table_heading"] = ParagraphStyle(
            "TableHeading",
            parent=base_styles["Heading3"],
            fontSize=9,
            textColor=colors.HexColor(self.COLOR_DARK),
            fontName="Helvetica-Bold",
            spaceAfter=4,
        )

        # Normal body text
        styles["body"] = ParagraphStyle(
            "Body",
            parent=base_styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor(self.COLOR_DARK),
            spaceAfter=4,
            leading=10,
        )

        # Small text for metadata
        styles["small"] = ParagraphStyle(
            "Small",
            parent=base_styles["Normal"],
            fontSize=7,
            textColor=colors.HexColor("#666666"),
            spaceAfter=2,
            fontName="Helvetica",
        )

        # Label text (for field names)
        styles["label"] = ParagraphStyle(
            "Label",
            parent=base_styles["Normal"],
            fontSize=7,
            textColor=colors.HexColor("#666666"),
            fontName="Helvetica-Bold",
            spaceAfter=2,
        )

        return styles

    def _get_risk_color(self, score: float) -> Tuple[str, str]:
        """Return color hex and classification for risk score."""
        if score >= 85:
            return self.COLOR_DANGER, "🔴🔴 EXTREME"
        elif score >= 70:
            return self.COLOR_DANGER, "🔴 CRITICAL"
        elif score >= 50:
            return self.COLOR_WARNING, "🟡 MEDIUM-ELEVATED"
        else:
            return self.COLOR_SUCCESS, "🟢 LOW"

    def generate_pdf(self, referral_data: Dict[str, Any]) -> io.BytesIO:
        """
        Generate a professional CBP referral package PDF.

        Args:
            referral_data: Complete referral data including case, shipment, risk scoring, etc.

        Returns:
            BytesIO buffer containing PDF content
        """
        logger.info(f"Generating referral PDF for case: {referral_data.get('case_id')}")

        try:
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                topMargin=self.MARGIN,
                bottomMargin=self.MARGIN,
                leftMargin=self.MARGIN,
                rightMargin=self.MARGIN,
            )

            # Build content
            content = []
            content.extend(self._build_cover_page(referral_data))
            content.extend(self._build_executive_summary(referral_data))
            content.extend(self._build_officer_narrative(referral_data))
            # Section 3-1 through 3-5: Core shipment data
            content.extend(self._build_shipment_identification(referral_data))
            content.extend(self._build_line_items(referral_data))
            content.extend(self._build_routing_history(referral_data))
            content.extend(self._build_parties_and_roles(referral_data))
            content.extend(self._build_entity_ownership_chain(referral_data))
            # Section 3-6 through 3-11: Analysis sections
            content.extend(self._build_historical_import_pattern(referral_data))
            content.extend(self._build_trade_flow_intelligence(referral_data))
            content.extend(self._build_document_review(referral_data))
            content.extend(self._build_document_consistency(referral_data))
            content.extend(self._build_supplier_verification(referral_data))
            content.extend(self._build_risk_indicators(referral_data))
            # Section 3-12 and beyond: Risk scoring, scenarios, determination
            content.extend(self._build_risk_scoring_breakdown(referral_data))
            content.extend(self._build_what_if_scenarios(referral_data))
            content.extend(self._build_formal_determination(referral_data))
            content.extend(self._build_appendix(referral_data))

            # Generate PDF
            doc.build(content)
            pdf_buffer.seek(0)

            logger.info(f"PDF generated successfully for case: {referral_data.get('case_id')}")
            return pdf_buffer

        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            raise

    def _build_cover_page(self, data: Dict[str, Any]) -> List:
        """Build cover page with case identification and risk assessment."""
        content = []
        risk_color, risk_level = self._get_risk_color(data.get("risk_score", 0))

        # Spacing
        content.append(Spacer(1, 1.2 * inch))

        # Title
        content.append(Paragraph("CUSTOMS AND BORDER PROTECTION", self.styles["cover_title"]))
        content.append(Paragraph("ENHANCED PENALTY ASSESSMENT PROGRAM", self.styles["cover_title"]))
        content.append(Paragraph("REFERRAL PACKAGE", self.styles["cover_title"]))
        content.append(Spacer(1, 0.3 * inch))

        # Case information
        case_id = data.get("case_id", "Unknown")
        shipment_id = data.get("shipment_id", "Unknown")
        date_prepared = datetime.now().strftime("%B %d, %Y")

        content.append(Paragraph(f"<b>Case ID:</b> {case_id}", self.styles["body"]))
        content.append(Paragraph(f"<b>Shipment ID:</b> {shipment_id}", self.styles["body"]))
        content.append(Paragraph(f"<b>Date Prepared:</b> {date_prepared}", self.styles["body"]))
        content.append(Spacer(1, 0.3 * inch))

        # Risk assessment box
        risk_score = data.get("risk_score", 0)
        recommendation = data.get("recommendation", "EXAMINE")
        content.append(
            Paragraph(
                f"<font color='{risk_color}'><b>RISK CLASSIFICATION: {risk_level}</b></font>",
                self.styles["cover_title"],
            )
        )
        content.append(
            Paragraph(
                f"<font color='{risk_color}'><b>RISK SCORE: {risk_score}/100</b></font>", self.styles["cover_title"]
            )
        )
        content.append(Spacer(1, 0.2 * inch))
        content.append(Paragraph(f"<b>RECOMMENDATION: {recommendation}</b>", self.styles["body"]))

        content.append(PageBreak())
        return content

    def _build_executive_summary(self, data: Dict[str, Any]) -> List:
        """Build executive summary section."""
        content = []
        content.append(Paragraph("EXECUTIVE SUMMARY", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        # Case overview
        shipment = data.get("shipment", {})
        content.append(Paragraph("<b>Case Overview</b>", self.styles["table_heading"]))

        overview_data = [
            ("Shipper", shipment.get("shipper_name", "N/A")),
            ("Consignee", shipment.get("consignee_name", "N/A")),
            ("Commodity", shipment.get("commodity_name", "N/A")),
            ("HS Code", shipment.get("hs_code", "N/A")),
            ("Route", f"{shipment.get('origin_country', 'N/A')} → {shipment.get('destination_country', 'N/A')}"),
            ("Declared Value", f"${shipment.get('declared_value', 0):,.2f}"),
        ]

        for label, value in overview_data:
            content.append(Paragraph(f"<b>{label}:</b> {value}", self.styles["body"]))

        content.append(Spacer(1, 0.15 * inch))

        # Risk findings
        content.append(Paragraph("<b>Summary Findings:</b>", self.styles["table_heading"]))
        risk_score = data.get("risk_score", 0)

        findings = "This shipment presents an "
        if risk_score >= 85:
            findings += "extreme-risk profile"
        elif risk_score >= 70:
            findings += "critical-risk profile"
        elif risk_score >= 50:
            findings += "medium-to-elevated-risk profile"
        else:
            findings += "low-risk profile"

        findings += " driven by anomaly detection signals and entity risk indicators."
        content.append(Paragraph(findings, self.styles["body"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(
            Paragraph(
                f"<b>Data Sources:</b> ISF-Filing, AIS-Archive, Altana-Atlas, Senzing-Trade-Graph", self.styles["small"]
            )
        )
        content.append(PageBreak())
        return content

    def _build_officer_narrative(self, data: Dict[str, Any]) -> List:
        """Build officer narrative section."""
        content = []
        content.append(Paragraph("OFFICER NARRATIVE (EDITABLE)", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        narrative = data.get("narrative", "")
        if not narrative:
            narrative = "Based on preliminary review of shipment data, the following concerns have been identified: automated risk scoring systems have flagged anomalies in ISF Element 9 data, AIS vessel routing patterns, and entity background verification. Officer review and possible physical examination is recommended before clearance."

        content.append(Paragraph(narrative, self.styles["body"]))
        content.append(Spacer(1, 0.1 * inch))
        content.append(
            Paragraph(
                f"<b>Data Source:</b> Officer Manual Review + Automated Risk Scoring Engine", self.styles["small"]
            )
        )
        content.append(PageBreak())
        return content

    def _build_shipment_identification(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-1: Shipment Identification."""
        content = []
        content.append(Paragraph("TABLE 3-1: SHIPMENT IDENTIFICATION", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        shipment = data.get("shipment", {})
        table_data = [
            ["Shipper Name", shipment.get("shipper_name", "N/A")],
            ["Shipper Country", shipment.get("origin_country", "N/A")],
            ["Consignee Name", shipment.get("consignee_name", "N/A")],
            ["Consignee Country", shipment.get("destination_country", "N/A")],
            ["Commodity", shipment.get("commodity_name", "N/A")],
            ["HS Code", shipment.get("hs_code", "N/A")],
            ["Quantity", f"{shipment.get('quantity', 1)} {shipment.get('unit', 'units')}"],
            ["Declared Value", f"${shipment.get('declared_value', 0):,.2f}"],
            ["Weight (kg)", f"{shipment.get('weight_kg', 0):,.0f}"],
        ]

        table = Table(table_data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(self.COLOR_HEADER_BG)),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )
        content.append(table)
        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph(f"<b>Data Source:</b> ISF-Filing (CBP Port Authority Records)", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_line_items(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-2: Line Items Detail."""
        content = []
        content.append(Paragraph("TABLE 3-2: LINE ITEMS DETAIL", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        shipment = data.get("shipment", {})
        line_items = data.get("line_items", [])

        if not line_items:
            # Default single item
            line_items = [
                {
                    "hs_code": shipment.get("hs_code", "N/A"),
                    "description": shipment.get("commodity_name", "N/A"),
                    "quantity": shipment.get("quantity", 1),
                    "unit": shipment.get("unit", "units"),
                    "value": shipment.get("declared_value", 0),
                }
            ]

        table_data = [["HS Code", "Description", "Quantity", "Unit", "Declared Value"]]
        for item in line_items:
            table_data.append(
                [
                    item.get("hs_code", ""),
                    item.get("description", "")[:35],
                    str(item.get("quantity", "")),
                    item.get("unit", ""),
                    f"${item.get('value', 0):,.2f}",
                ]
            )

        table = Table(table_data, colWidths=[1 * inch, 2 * inch, 0.8 * inch, 0.7 * inch, 1.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(self.COLOR_PRIMARY)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )
        content.append(table)
        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph(f"<b>Data Source:</b> Bill of Lading + ISF Manifest", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_routing_history(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-3: AIS Routing History."""
        content = []
        content.append(Paragraph("TABLE 3-3: AIS ROUTING HISTORY", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        routing = data.get("routing", {})

        table_data = [
            ["Vessel Name", routing.get("vessel_name", "N/A")],
            ["IMO Number", routing.get("vessel_imo", "N/A")],
            ["Port of Lading", routing.get("port_of_lading", "N/A")],
            ["Port of Unlading", routing.get("port_of_unlading", "N/A")],
            [
                "Dwell Days",
                f"{routing.get('dwell_days', 0):.1f} days (baseline: {routing.get('dwell_baseline', 0):.1f} days)",
            ],
            ["Dwell Anomaly", routing.get("dwell_anomaly", "NORMAL")],
            ["AIS Gaps", str(routing.get("ais_gaps", 0))],
            ["Transit Days", str(routing.get("transit_days", "N/A"))],
        ]

        table = Table(table_data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(self.COLOR_HEADER_BG)),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )
        content.append(table)
        content.append(Spacer(1, 0.1 * inch))
        content.append(
            Paragraph(f"<b>Data Source:</b> AIS-Archive (MarineTraffic + CBP Port Authority)", self.styles["small"])
        )
        content.append(PageBreak())
        return content

    def _build_parties_and_roles(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-4: Parties and Roles."""
        content = []
        content.append(Paragraph("TABLE 3-4: PARTIES AND ROLES", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        parties = data.get("parties", [])
        if not parties:
            parties = [
                {"name": data.get("shipment", {}).get("shipper_name", "N/A"), "role": "SHIPPER", "country": "N/A"},
                {"name": data.get("shipment", {}).get("consignee_name", "N/A"), "role": "CONSIGNEE", "country": "N/A"},
            ]

        table_data = [["Entity Name", "Role", "Country", "Risk Notes"]]
        for party in parties:
            table_data.append(
                [
                    party.get("name", "")[:30],
                    party.get("role", ""),
                    party.get("country", ""),
                    party.get("risk_note", "None identified")[:30],
                ]
            )

        table = Table(table_data, colWidths=[1.5 * inch, 1.2 * inch, 1 * inch, 1.3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(self.COLOR_PRIMARY)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )
        content.append(table)
        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph(f"<b>Data Source:</b> ISF-Filing + Senzing Entity Database", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_entity_ownership_chain(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-5: Entity Ownership Chain."""
        content = []
        content.append(Paragraph("TABLE 3-5: ENTITY OWNERSHIP CHAIN", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        entity_chain = data.get("entity_chain", [])
        if entity_chain:
            for tier in entity_chain:
                content.append(Paragraph(f"<b>Tier {tier.get('tier', 'N/A')}</b>", self.styles["table_heading"]))
                tier_data = [
                    ("Entity Name", tier.get("name", "N/A")),
                    ("Country", tier.get("country", "N/A")),
                    ("Ownership %", f"{tier.get('ownership_pct', 0)}%"),
                    ("Match Confidence", f"{tier.get('match_confidence', 0)}%"),
                    ("Risk Signal", tier.get("risk_signal", "None")),
                ]
                for label, value in tier_data:
                    content.append(Paragraph(f"  {label}: {value}", self.styles["body"]))
                content.append(Spacer(1, 0.08 * inch))
        else:
            content.append(Paragraph("Entity ownership chain data not available.", self.styles["body"]))

        content.append(
            Paragraph(f"<b>Data Source:</b> Senzing-Trade-Graph + Company Registry Lookups", self.styles["small"])
        )
        content.append(PageBreak())
        return content

    def _build_historical_import_pattern(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-6: Historical Import Pattern Analysis."""
        content = []
        content.append(Paragraph("TABLE 3-6: HISTORICAL IMPORT PATTERN ANALYSIS", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        section = data.get("section_3_6", {})
        if section:
            pattern_data = [
                ("Origin Country", section.get("origin", "N/A")),
                ("Destination Country", section.get("destination", "N/A")),
                ("LLM Generated", "Yes" if section.get("llm_generated") else "No"),
                ("Model", section.get("llm_model", "N/A") if section.get("llm_generated") else "Manual Analysis"),
            ]
            for label, value in pattern_data:
                content.append(Paragraph(f"<b>{label}:</b> {value}", self.styles["body"]))

            content.append(Spacer(1, 0.1 * inch))
            content.append(Paragraph("<b>Analysis Summary</b>", self.styles["table_heading"]))
            content.append(Paragraph(section.get("pattern", "No analysis available"), self.styles["body"]))
        else:
            content.append(Paragraph("No historical import pattern data available.", self.styles["body"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph("<b>Data Source:</b> Historical ISF Filing Analysis + Trade Pattern Intelligence", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_trade_flow_intelligence(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-7: Trade Flow Intelligence."""
        content = []
        content.append(Paragraph("TABLE 3-7: TRADE FLOW INTELLIGENCE", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        section = data.get("section_3_7", {})
        if section:
            trade_data = [
                ("HS Code", section.get("hs_code", "N/A")),
                ("Commodity", section.get("commodity", "N/A")),
                ("Origin Country", section.get("origin", "N/A")),
                ("AD/CVD Status", section.get("ad_cvd_status", "NONE")),
                ("AD/CVD Rate", section.get("ad_cvd_rate", "0%")),
                ("Prior Filings", str(section.get("prior_filings", 0))),
                ("Origin Shift Trend", section.get("origin_shift_trend", "STABLE")),
            ]
            for label, value in trade_data:
                content.append(Paragraph(f"<b>{label}:</b> {value}", self.styles["body"]))

            content.append(Spacer(1, 0.1 * inch))
            content.append(Paragraph("<b>Trade Flow Summary</b>", self.styles["table_heading"]))
            content.append(Paragraph(section.get("summary", "No analysis available"), self.styles["body"]))
        else:
            content.append(Paragraph("No trade flow intelligence data available.", self.styles["body"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph("<b>Data Source:</b> Tariff Database + AD/CVD Orders + Trade Pattern Analysis", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_document_review(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-8: Document Review Checklist."""
        content = []
        content.append(Paragraph("TABLE 3-8: DOCUMENT REVIEW CHECKLIST", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        section = data.get("section_3_8", {})
        documents = section.get("documents", [])

        if documents:
            table_data = [["Document", "Status", "Notes"]]
            status_colors = {"RECEIVED": self.COLOR_SUCCESS, "MISSING": self.COLOR_DANGER, "PENDING": self.COLOR_WARNING}

            for doc in documents:
                status = doc.get("status", "PENDING")
                table_data.append([
                    doc.get("document", "N/A"),
                    f'<font color="{status_colors.get(status, "#666")}">{status}</font>',
                    doc.get("notes", ""),
                ])

            table = Table(table_data, colWidths=[2.2*inch, 1*inch, 1.8*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 1, "#CCCCCC"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", "#F5F5F5"]),
            ]))
            content.append(table)
        else:
            content.append(Paragraph("No document review data available.", self.styles["body"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph("<b>Data Source:</b> CBP Document Portal + Shipper Submission Records", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_document_consistency(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-9: Document Consistency Matrix (ISF Element 9 Check)."""
        content = []
        content.append(Paragraph("TABLE 3-9: DOCUMENT CONSISTENCY MATRIX (ISF ELEMENT 9)", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        section = data.get("section_3_9", {})
        isf_data = section.get("isf_element9", {})

        if isf_data:
            is_mismatch = isf_data.get("is_mismatch", False)

            if is_mismatch:
                content.append(Paragraph(
                    '<font color="#D83933"><b>⚠️ ISF ELEMENT 9 MISMATCH DETECTED</b></font>',
                    self.styles["table_heading"]
                ))
                content.append(Spacer(1, 0.08 * inch))

            consistency_data = [
                ("Declared Origin (ISF Element 9)", isf_data.get("declared_origin", "N/A")),
                ("Actual Stuffing Country (AIS)", isf_data.get("actual_stuffing_country", "N/A")),
                ("Mismatch Status", "MISMATCH" if is_mismatch else "CONSISTENT"),
                ("Confidence Level", f"{isf_data.get('mismatch_confidence', 0) * 100:.1f}%"),
            ]

            for label, value in consistency_data:
                content.append(Paragraph(f"<b>{label}:</b> {value}", self.styles["body"]))

            evidence = isf_data.get("evidence", [])
            if evidence:
                content.append(Spacer(1, 0.08 * inch))
                content.append(Paragraph("<b>Supporting Evidence</b>", self.styles["table_heading"]))
                for ev in evidence:
                    content.append(Paragraph(f"• {ev}", self.styles["body"]))

        else:
            content.append(Paragraph("No ISF Element 9 consistency data available.", self.styles["body"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph(f"<b>Summary:</b> {section.get('summary', 'N/A')}", self.styles["small"]))
        content.append(Paragraph("<b>Data Source:</b> ISF Pre-Arrival Filing + AIS Vessel Tracking", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_supplier_verification(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-10: Supplier Manufacturing Verification."""
        content = []
        content.append(Paragraph("TABLE 3-10: SUPPLIER MANUFACTURING VERIFICATION", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        section = data.get("section_3_10", {})
        if section:
            age_months = section.get("shipper_age_months")
            age_risk = section.get("shipper_age_risk", "ESTABLISHED")

            risk_colors = {"VERY_NEW": self.COLOR_DANGER, "NEW": self.COLOR_WARNING, "ESTABLISHED": self.COLOR_SUCCESS}
            age_color = risk_colors.get(age_risk, "#666")

            supplier_data = [
                ("Supplier Name", section.get("shipper", "N/A")),
                ("Operating Age", f"{age_months} months" if age_months else "Unknown"),
                ("Age Risk Category", f'<font color="{age_color}"><b>{age_risk}</b></font>'),
                ("Declared Volume (kg)", f"{section.get('declared_volume_kg', 0):,.0f}"),
                ("Capacity Assessment", section.get("capacity_assessment", "Unknown")),
            ]

            for label, value in supplier_data:
                content.append(Paragraph(f"<b>{label}:</b> {value}", self.styles["body"]))

            content.append(Spacer(1, 0.1 * inch))
            content.append(Paragraph(f"<b>Summary:</b> {section.get('summary', 'N/A')}", self.styles["body"]))
        else:
            content.append(Paragraph("No supplier verification data available.", self.styles["body"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph("<b>Data Source:</b> Company Registry Lookups + Historical Filing Analysis", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_risk_indicators(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-11: Risk Indicator Summary."""
        content = []
        content.append(Paragraph("TABLE 3-11: RISK INDICATOR SUMMARY", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        section = data.get("section_3_11", {})
        indicators = section.get("indicators", [])

        if indicators:
            table_data = [["Risk Indicator", "Status", "Evidence", "Authority"]]

            for ind in indicators:
                # Handle both "present" (bool) and "risk_level" (str) formats
                present = ind.get("present", False)
                risk_level = ind.get("risk_level", "NORMAL")
                status = "PRESENT" if (present or risk_level in ["HIGH", "MEDIUM"]) else "ABSENT"
                status_color = self.COLOR_DANGER if status == "PRESENT" else self.COLOR_SUCCESS

                table_data.append([
                    ind.get("indicator", "N/A"),
                    f'<font color="{status_color}"><b>{status}</b></font>',
                    ind.get("evidence", "N/A")[:40],  # Truncate
                    ind.get("authority", "N/A")[:25],  # Truncate
                ])

            table = Table(table_data, colWidths=[1.8*inch, 1*inch, 1.8*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 1, "#CCCCCC"),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", "#F5F5F5"]),
            ]))
            content.append(table)
        else:
            content.append(Paragraph("No risk indicators data available.", self.styles["body"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph("<b>Data Source:</b> Automated Risk Scoring Engine + Intelligence Integration", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_risk_scoring_breakdown(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-12: Risk Scoring Breakdown with H1/H2/H3 components."""
        content = []
        content.append(Paragraph("TABLE 3-12: RISK SCORING BREAKDOWN (ML MODEL)", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        risk_scoring = data.get("risk_scoring", {})
        final_score = data.get("risk_score", 0)
        h1_score = risk_scoring.get("h1_score", 0)
        h2_score = risk_scoring.get("h2_score", 0)
        h3_score = risk_scoring.get("h3_score", 0)

        # Summary scores
        content.append(Paragraph("<b>Component Scores Summary</b>", self.styles["table_heading"]))
        summary_data = [
            ["Component", "Score", "Weight", "Result"],
        ]
        components = risk_scoring.get("components", [])
        if isinstance(components, list):
            for comp in components:
                summary_data.append(
                    [
                        comp.get("component", "")[:30],
                        f"{comp.get('score', 0):.1f}/10",
                        f"{comp.get('weight', 0):.0f}%",
                        f"{comp.get('weighted_result', 0):.1f}",
                    ]
                )

        table = Table(summary_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(self.COLOR_PRIMARY)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )
        content.append(table)
        content.append(Spacer(1, 0.15 * inch))

        # H2 Signals if available
        h2_signals = risk_scoring.get("h2_signals", [])
        if h2_signals:
            content.append(Paragraph("<b>H2 Anomaly Signals</b>", self.styles["table_heading"]))
            for signal in h2_signals:
                content.append(Paragraph(f"• {signal}", self.styles["body"]))
            content.append(Spacer(1, 0.1 * inch))

        # Score calculation
        content.append(Paragraph("<b>Final Score Calculation</b>", self.styles["table_heading"]))
        subtotal = risk_scoring.get("subtotal", 0)
        adjustments = risk_scoring.get("adjustments", [])
        confidence = risk_scoring.get("confidence_interval", "Unknown")

        content.append(Paragraph(f"Subtotal (Component Sum): {subtotal:.1f}", self.styles["body"]))
        for adj in adjustments:
            if adj.get("adjustment_points", 0) != 0:
                content.append(
                    Paragraph(
                        f"{adj.get('type', 'Adjustment')} ({adj.get('multiplier', 1):.2f}x): {adj.get('adjustment_points', 0):.1f} points",
                        self.styles["body"],
                    )
                )
        content.append(Spacer(1, 0.08 * inch))
        content.append(Paragraph(f"<b>FINAL RISK SCORE: {final_score}/100</b>", self.styles["table_heading"]))
        content.append(Paragraph(f"Confidence Interval: {confidence}", self.styles["small"]))

        content.append(Spacer(1, 0.1 * inch))
        content.append(
            Paragraph(
                f"<b>Data Source:</b> ISF-Filing, AIS-Archive, Altana-Atlas, Senzing-Trade-Graph, CBP ML-Risk-Scorer-v2.1",
                self.styles["small"],
            )
        )
        content.append(PageBreak())
        return content

    def _build_what_if_scenarios(self, data: Dict[str, Any]) -> List:
        """Build TABLE 3-7: What-If Scenarios with sensitivity analysis."""
        content = []
        content.append(Paragraph("TABLE 3-7: WHAT-IF SCENARIOS (SENSITIVITY ANALYSIS)", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        scenarios = data.get("what_if_scenarios", [])
        if scenarios:
            for idx, scenario in enumerate(scenarios, 1):
                scenario_num = f"Scenario {idx}"
                scenario_name = scenario.get("name", "What-If Scenario")
                base_score = scenario.get("base_score", 97)
                adjusted_score = scenario.get("adjusted_score", 0)
                impact = scenario.get("impact", "0 points")
                recommendation = scenario.get("recommendation", "N/A")
                is_true = scenario.get("scenario", False)

                content.append(Paragraph(f"<b>{scenario_num}: {scenario_name}</b>", self.styles["table_heading"]))
                content.append(Paragraph(f"Assumption: {'TRUE' if is_true else 'FALSE'}", self.styles["body"]))
                content.append(
                    Paragraph(
                        f"Current Score: {base_score}/100 → Scenario Score: {adjusted_score}/100", self.styles["body"]
                    )
                )
                content.append(Paragraph(f"Impact: {impact}", self.styles["body"]))
                content.append(Paragraph(f"Recommendation: {recommendation}", self.styles["body"]))
                content.append(Spacer(1, 0.1 * inch))
        else:
            content.append(Paragraph("What-if scenario analysis not available.", self.styles["body"]))

        content.append(Paragraph(f"<b>Data Source:</b> Risk-Scoring-What-If-Engine v1.2", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_document_checklist(self, data: Dict[str, Any]) -> List:
        """Build document evidence checklist."""
        content = []
        content.append(Paragraph("DOCUMENT EVIDENCE CHECKLIST", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        docs = data.get("documents", [])

        table_data = [["Document", "Required", "Status", "Officer Notes"]]
        if docs:
            for doc in docs:
                table_data.append(
                    [
                        doc.get("name", "")[:20],
                        "Yes" if doc.get("required") else "No",
                        doc.get("status", "PENDING"),
                        doc.get("notes", "")[:25],
                    ]
                )
        else:
            table_data.append(["Document evidence not available", "", "", ""])

        table = Table(table_data, colWidths=[1.5 * inch, 1 * inch, 1.2 * inch, 1.3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(self.COLOR_PRIMARY)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )
        content.append(table)
        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph(f"<b>Data Source:</b> CBP Document Portal + Shipper Submission", self.styles["small"]))
        content.append(PageBreak())
        return content

    def _build_formal_determination(self, data: Dict[str, Any]) -> List:
        """Build formal determination section."""
        content = []
        content.append(Paragraph("FORMAL DETERMINATION", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        recommendation = data.get("recommendation", "EXAMINE")
        risk_score = data.get("risk_score", 0)

        content.append(
            Paragraph(
                f"<b>Determination:</b> This shipment is subject to <b>{recommendation}</b>.", self.styles["body"]
            )
        )
        content.append(Spacer(1, 0.1 * inch))

        rationale = f"Risk score of {risk_score}/100 is in the "
        if risk_score >= 85:
            rationale += "EXTREME category"
        elif risk_score >= 70:
            rationale += "CRITICAL category"
        elif risk_score >= 50:
            rationale += "MEDIUM-ELEVATED category"
        else:
            rationale += "LOW risk category"
        rationale += " requiring officer review."

        content.append(Paragraph(f"<b>Rationale:</b> {rationale}", self.styles["body"]))
        content.append(Spacer(1, 0.1 * inch))

        content.append(
            Paragraph(f"<b>Submitted:</b> {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}", self.styles["small"])
        )
        content.append(Spacer(1, 0.2 * inch))

        content.append(
            Paragraph("Officer Signature: ________________________     Date: _____________", self.styles["small"])
        )
        content.append(Spacer(1, 0.15 * inch))
        content.append(
            Paragraph("Supervisor Review: ________________________     Date: _____________", self.styles["small"])
        )

        content.append(PageBreak())
        return content

    def _build_appendix(self, data: Dict[str, Any]) -> List:
        """Build appendix with data sources."""
        content = []
        content.append(Paragraph("APPENDIX: DATA SOURCES & METHODOLOGY", self.styles["section_heading"]))
        content.append(Spacer(1, 0.1 * inch))

        content.append(Paragraph("<b>Data Sources Used in This Assessment:</b>", self.styles["table_heading"]))
        sources = [
            "ISF-Filing: Importer Security Filing database (CBP)",
            "AIS-Archive: Automatic Identification System vessel tracking (MarineTraffic)",
            "Altana-Atlas: Sanctions & supply chain verification (Altana platform)",
            "Senzing-Trade-Graph: Entity relationship mapping (Senzing)",
            "CBP ML-Risk-Scorer-v2.1: Machine learning risk classification engine",
        ]
        for source in sources:
            content.append(Paragraph(f"• {source}", self.styles["body"]))

        content.append(Spacer(1, 0.15 * inch))
        content.append(Paragraph("<b>Methodology:</b>", self.styles["table_heading"]))

        methodology = (
            "This referral package was prepared using CBP's Enhanced Penalty Assessment (EAPA) framework, which combines "
            "automated risk scoring (H1, H2, H3 factors), anomaly detection algorithms, intelligence integration, and officer judgment. "
            "Each section includes explicit data source attribution for auditability."
        )
        content.append(Paragraph(methodology, self.styles["body"]))

        return content
