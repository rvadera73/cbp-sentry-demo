"""
reference_data.py — Seeded trade-enforcement reference data for the Gate-1 scope.

Scope corridor: VN -> US, HS 7604 (aluminum extrusions) + 8541 (solar cells).

IMPORTANT: All values in this module are SEEDED FROM PUBLIC RECORD (Federal
Register AD/CVD orders, Commerce circumvention determinations, USTR Section 301
actions, CBP UFLPA guidance, and public market price norms). There is no
internet access in this environment, so these are hard-coded snapshots.
The live fetch via fetch_adcvd / Comtrade / entities resolution is a LATER SWAP:
these functions are the seam where a live data client will be dropped in.

All public functions are DEFENSIVE: they return None / 0 / False when the input
is unknown or malformed, and never raise on bad input.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _hs4(hs_code) -> str:
    """Normalize an HS code to its 4-digit chapter-heading prefix.

    Accepts '7604', '7604.21', '7604.21.00', 7604, etc. Returns '' on garbage.
    """
    if hs_code is None:
        return ""
    try:
        digits = "".join(ch for ch in str(hs_code) if ch.isdigit())
        return digits[:4]
    except Exception:  # pragma: no cover - pure defensiveness
        return ""


def _country(code) -> str:
    """Normalize a country to a 2-letter upper code; map common long forms."""
    if not code:
        return ""
    c = str(code).strip().upper()
    _LONG = {
        "CHINA": "CN", "VIETNAM": "VN", "MALAYSIA": "MY", "THAILAND": "TH",
        "CAMBODIA": "KH", "UNITED STATES": "US", "USA": "US",
    }
    return _LONG.get(c, c[:2])


# ---------------------------------------------------------------------------
# AD/CVD ORDERS — seeded from public record.
#
# Aluminum extrusions (HS 7604 / 7610 / 7616):
#   Original orders on aluminum extrusions FROM CHINA:
#     AD: A-570-967  (antidumping)
#     CVD: C-570-968 (countervailing)
#   Public-record rates: AD margins ~ up to 86%; CVD rates very high, with the
#   PRC-wide / adverse-facts-available CVD reaching ~374%. Commerce and CBP
#   have repeatedly found transshipment of Chinese aluminum extrusions through
#   Vietnam, Malaysia, and Thailand to evade these orders (EAPA cases).
#   In 2024 Commerce also issued NEW AD/CVD orders on aluminum extrusions from
#   ~14 additional countries (incl. Vietnam, Malaysia, Thailand, etc.).
#
# Crystalline-silicon photovoltaic (solar) cells (HS 8541, also 8501 modules):
#   Original AD/CVD orders on solar cells FROM CHINA (A-570-979 / C-570-980).
#   In Aug 2023 Commerce issued an affirmative CIRCUMVENTION finding: certain
#   solar cells/modules completed in Cambodia (KH), Malaysia (MY), Thailand (TH),
#   and Vietnam (VN) using Chinese wafers/inputs are circumventing the China
#   orders and subject to duties. Polysilicon supply chains are also exposed to
#   UFLPA (Xinjiang forced-labor) enforcement.
#
# Section 301 (USTR): List actions imposed an additional 25% tariff on broad
# categories of Chinese-origin goods, including aluminum and many electronics.
#
# UFLPA: rebuttable presumption barring goods linked to Xinjiang / listed
# entities; polysilicon (solar feedstock) is a high-priority enforcement sector.
# ---------------------------------------------------------------------------

# Active AD/CVD order universe, keyed by HS-4 chapter heading. Each entry is the
# public-record snapshot for the China-origin order plus the set of known
# transshipment hubs where circumvention/evasion has been found.
_ADCVD_ORDERS = {
    "7604": {
        "commodity": "Aluminum extrusions",
        "primary_origin": "CN",
        "order": "A-570-967 (AD) / C-570-968 (CVD)",
        "ad_rate": 0.86,        # ~86% AD margin (public record, decimal)
        "cvd_rate": 3.74,       # up to ~374% CVD (AFA / PRC-wide, decimal)
        "section_301": 0.25,    # +25% List 3 additional duty on China-origin
        "uflpa": False,
        # Hubs where Chinese aluminum extrusions have been transshipped/evaded:
        "transship_hubs": ["VN", "MY", "TH", "KH", "ID"],
    },
    # 7610/7616 share the aluminum-extrusions order family (structures, profiles,
    # heat sinks / pallets covered by scope-rulings). Same order, same hubs.
    "7610": {
        "commodity": "Aluminum structures/profiles",
        "primary_origin": "CN",
        "order": "A-570-967 (AD) / C-570-968 (CVD)",
        "ad_rate": 0.86,
        "cvd_rate": 3.74,
        "section_301": 0.25,
        "uflpa": False,
        "transship_hubs": ["VN", "MY", "TH", "KH", "ID"],
    },
    "8541": {
        "commodity": "Crystalline-silicon photovoltaic (solar) cells",
        "primary_origin": "CN",
        "order": "A-570-979 (AD) / C-570-980 (CVD); 2023 circumvention finding (VN/MY/TH/KH)",
        "ad_rate": 0.238,       # ~23.8% representative AD (China-wide, decimal)
        "cvd_rate": 0.15,       # ~15% representative CVD (decimal)
        "section_301": 0.25,
        "uflpa": True,          # polysilicon / Xinjiang exposure
        "transship_hubs": ["VN", "MY", "TH", "KH"],
    },
    # 8501 = solar modules/panels (assembled). Same enforcement posture as 8541.
    "8501": {
        "commodity": "Solar modules/panels",
        "primary_origin": "CN",
        "order": "A-570-979 (AD) / C-570-980 (CVD); 2023 circumvention finding (VN/MY/TH/KH)",
        "ad_rate": 0.238,
        "cvd_rate": 0.15,
        "section_301": 0.25,
        "uflpa": True,
        "transship_hubs": ["VN", "MY", "TH", "KH"],
    },
}


# ---------------------------------------------------------------------------
# MARKET PRICE NORMS ($/unit). Unit is $/kg for these commodity families
# (manifests carry declared_weight_kg). Seeded from public market references.
#   - Aluminum extrusions (7604/7610/7616): ~$2.6/kg (LME aluminum base ~$2.2/kg
#     + extrusion/fabrication premium). Undervaluation below this is a price
#     anomaly / evasion indicator.
#   - Solar cells (8541): ~$0.45/kg equivalent reference for declared PV cells.
# ---------------------------------------------------------------------------
_PRICE_NORMS_USD_PER_KG = {
    "7604": 2.60,   # aluminum extrusions ~$2.6/kg (public market norm)
    "7610": 2.80,   # aluminum structures/profiles
    "7616": 3.20,   # other aluminum articles (heat sinks, etc.)
    "8541": 0.45,   # crystalline-silicon PV cells (declared $/kg reference)
    "8501": 0.50,   # solar modules/panels
}


def adcvd_for(hs_code, origin_country) -> Optional[Dict]:
    """Return the AD/CVD enforcement profile for (hs_code, origin_country).

    Returns a dict with keys:
        ad_rate, cvd_rate, section_301, uflpa, order, transship_hubs,
        commodity, origin_is_primary, origin_is_transship_hub
    or None when no active order is known for the HS family.

    An order applies when:
      * the HS-4 family has a seeded order, AND
      * the origin is the primary order country (CN), OR
      * the origin is a known transshipment hub for that order
        (VN/MY/TH/KH/...), which is the scope-relevant evasion case.

    Defensive: returns None on unknown HS / origin; never raises.

    NOTE: seeded from public record; live fetch via fetch_adcvd is a later swap.
    """
    try:
        hs4 = _hs4(hs_code)
        if not hs4:
            return None
        order = _ADCVD_ORDERS.get(hs4)
        if not order:
            return None

        origin = _country(origin_country)
        primary = order["primary_origin"]
        hubs = order.get("transship_hubs", [])

        origin_is_primary = bool(origin) and origin == primary
        origin_is_hub = bool(origin) and origin in hubs

        # If we have an origin and it's neither the primary order country nor a
        # known transshipment hub, the order doesn't directly apply.
        if origin and not (origin_is_primary or origin_is_hub):
            return None

        return {
            "ad_rate": order.get("ad_rate", 0.0),
            "cvd_rate": order.get("cvd_rate", 0.0),
            "section_301": order.get("section_301", 0.0),
            "uflpa": bool(order.get("uflpa", False)),
            "order": order.get("order"),
            "transship_hubs": list(hubs),
            "commodity": order.get("commodity"),
            "origin_is_primary": origin_is_primary,
            "origin_is_transship_hub": origin_is_hub,
        }
    except Exception as exc:  # pragma: no cover - pure defensiveness
        logger.debug("adcvd_for(%r, %r) failed: %s", hs_code, origin_country, exc)
        return None


def price_norm(hs_code) -> Optional[float]:
    """Return the seeded market price norm ($/kg) for an HS family, or None.

    Defensive: returns None on unknown / malformed HS code.

    NOTE: seeded from public record; live fetch via comtrade is a later swap.
    """
    try:
        return _PRICE_NORMS_USD_PER_KG.get(_hs4(hs_code))
    except Exception:  # pragma: no cover
        return None


def is_scope_corridor(origin, dest, hs) -> bool:
    """True if (origin, dest, hs) is in the Gate-1 scope corridor.

    Scope: VN -> US, HS 7604 (aluminum extrusions) or 8541 (solar cells).

    Defensive: returns False on any unknown/malformed input; never raises.

    NOTE: seeded from public record; live fetch via entities is a later swap.
    """
    try:
        if _country(origin) != "VN":
            return False
        if _country(dest) != "US":
            return False
        return _hs4(hs) in ("7604", "8541")
    except Exception:  # pragma: no cover
        return False
