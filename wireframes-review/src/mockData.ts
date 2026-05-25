import { CBPOfficer, Case, TradeEntity, Shipment, AIFinding, ReferralPackage, ThreatFeedEvent } from './types';

export const INITIAL_OFFICERS: CBPOfficer[] = [
  {
    id: "officer_1",
    name: "Rav J. D.",
    badge: "CBP-98522",
    role: "Senior Intelligence Analyst / Trade Enforcement",
    email: "ravjdpr@gmail.com",
    shift: "Eastern Shift Alpha",
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80"
  },
  {
    id: "officer_2",
    name: "Sarah Jenkins",
    badge: "CBP-41092",
    role: "Field Investigation Officer",
    email: "s.jenkins@cbp.dhs.gov",
    shift: "Gulf Coast Shift",
    avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80"
  },
  {
    id: "officer_3",
    name: "Marcus Chen",
    badge: "CBP-32044",
    role: "District Import Specialist",
    email: "m.chen@cbp.dhs.gov",
    shift: "Pacific Northwest Shift",
    avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=150&q=80"
  }
];

export const INITIAL_CASES: Case[] = [
  {
    case_id: "CBP-2026-9041",
    case_name: "Silicon Origin Concealment via Vietnam Corridors",
    target_entity: "Vina Solar Technologies LLC",
    risk_score: 87,
    assigned_officer: "Rav J. D.",
    investigation_stage: "Overview",
    case_status: "Active",
    referral_status: "In Progress",
    priority: "Critical",
    opened_date: "2026-05-10",
    sla_timer: "3 days remaining",
    product_category: "Solar Photovoltaic Modules (8541.43.00)",
    ai_confidence: 91,
    ai_synopsis: "AI analysis indicates a highly probable origin-concealment pattern. Vina Solar Technologies acts as an intermediary assembly shop in industrial zones of Bac Giang, Vietnam. Bill-of-lading auditing shows continuous heavy intake of raw high-purity polysilicon wafers from Xinjiang-based restricted manufacturer Tianshan Solar Materials Corp with final assemblies routed instantly to US ports under falsified country of origin Declarations to evade Section 301 trade remedies."
  },
  {
    case_id: "CBP-2026-7815",
    case_name: "Plywood Transshipment Evasion via Da Nang",
    target_entity: "Pacific Wood & Veneer Import Inc",
    risk_score: 72,
    assigned_officer: "Sarah Jenkins",
    investigation_stage: "Overview",
    case_status: "Under Audit",
    referral_status: "Not Initiated",
    priority: "High",
    opened_date: "2026-05-14",
    sla_timer: "9 days remaining",
    product_category: "Hardwood Plywood Panelings (4412.33.00)",
    ai_confidence: 84,
    ai_synopsis: "Evasive transshipment anomaly detected via Da Nang Port. pacific Wood & Veneer declared manufacturing processes inside Vietnam. However, chemical veneer analysis matched regional Siberian Birch fibers, indicating bulk transshipment of unfinished Chinese plywood sheets into Vietnam for quick edge-banding, relabeling, and immediate export onto Florida ports."
  },
  {
    case_id: "CBP-2026-5512",
    case_name: "Structural Steel Evasion through Sriracha Corridor",
    target_entity: "Apex Steel Builders Group",
    risk_score: 93,
    assigned_officer: "Marcus Chen",
    investigation_stage: "Overview",
    case_status: "Active",
    referral_status: "Awaiting Approval",
    priority: "Critical",
    opened_date: "2026-04-20",
    sla_timer: "SLA Violated (Overdue)",
    product_category: "Structural Alloy Steel Channels (7308.90.95)",
    ai_confidence: 96,
    ai_synopsis: "Severe circular invoicing and route shielding operations detected. Subject utilizes a network of shell companies in Bangkok and Sriracha, Thailand. Flat carbon steel is rolled in Hebei, transported to Ban Laem port, repackaged, and bills of lading shifted through three distinct maritime freight brokerage identities to evade Anti-Dumping Duty orders totaling 244.5%."
  },
  {
    case_id: "CBP-2026-4401",
    case_name: "Organic Cotton Fiber Origin Deception Scheme",
    target_entity: "EcoTextile Logistics LLC",
    risk_score: 41,
    assigned_officer: "Sarah Jenkins",
    investigation_stage: "Overview",
    case_status: "Under Audit",
    referral_status: "Not Initiated",
    priority: "Medium",
    opened_date: "2026-05-18",
    sla_timer: "15 days remaining",
    product_category: "Combed Cotton Yarns (5205.22.00)",
    ai_confidence: 72,
    ai_synopsis: "Supply chain mapping detected a raw-cotton correlation anomaly. Subject import manifests point to a spinning company in Ho Chi Minh City as fiber origin. Automated satellite crop imaging and invoice ledger tracing show local spinning factories imported 92% of input lint material from restricted regional entities operating in forced-labor designated coordinates."
  },
  {
    case_id: "CBP-2026-3108",
    case_name: "Aluminum Extrusion Circumvention via Penang",
    target_entity: "Summit Global Metals Corp",
    risk_score: 65,
    assigned_officer: "Unassigned",
    investigation_stage: "Overview",
    case_status: "Active",
    referral_status: "Not Initiated",
    priority: "High",
    opened_date: "2026-05-20",
    sla_timer: "22 days remaining",
    product_category: "Aluminum Hollow Profiles (7604.21.00)",
    ai_confidence: 79,
    ai_synopsis: "Summmit Global Metals imported extreme custom extrusions claiming Malaysian origin. However, Penang extrusion plants lack active electrical industrial consumption records commensurate with high-tonnage smelting, demonstrating shell-front operation masking originating Chinese mills."
  }
];

export const INITIAL_ENTITIES: TradeEntity[] = [
  // Entities for Silicon Origin Case (CBP-2026-9041)
  {
    entity_id: "ENT-901",
    entity_type: "Importer",
    entity_name: "BrightPath Solar Corp (US Custodian)",
    country: "United States",
    risk_level: "Medium",
    sanctions_status: "None",
    known_affiliations: ["Vina Solar Technologies LLC", "Asia Pacific Energy Logistics"],
    enforcement_history: "No statutory seizures. Flagged twice under WRO (Withhold Release Order) compliance queries in 2025; resolved with minimal importer notes.",
    ownership_indicators: "Delaware registered shell facade owned by East Asia Capital Partners with banking trail terminating in Macau.",
    registration_status: "Active - CBP Customs Bond No. 90-A882",
    watchlist_status: "Clean",
    address: "2400 Sand Hill Road, Building 4, Menlo Park, CA 94025",
    tax_id: "94-3209841",
    phone: "+1 (650) 809-2191",
    shared_identifiers: ["ENT-904"] // Shares phone or manager contact with Pacific Logistics
  },
  {
    entity_id: "ENT-902",
    entity_type: "Intermediary",
    entity_name: "Vina Solar Technologies LLC",
    country: "Vietnam",
    risk_level: "Critical",
    sanctions_status: "Under Investigation",
    known_affiliations: ["BrightPath Solar Corp", "Tianshan Solar Materials Corp", "Jiangsu Maritime Forwarders"],
    enforcement_history: "Active CBP withhold enforcement query. Site audit report 2025-V12 indicates factory premises are mainly warehousing/packaging with zero industrial silicon ingot sawing machines installed, despite claiming 1.2GW fabrication capacity.",
    ownership_indicators: "Joint venture entity: 85% stakeholder is Jiangsu Solar Holdings (restricted Chinese state-affiliated entity).",
    registration_status: "Active Enterprise ID: 0108849202",
    watchlist_status: "High Alert Watchlist",
    address: "Bac Giang Industrial Zone, Lot 44A, Viet Yen District, Bac Giang Province, Vietnam",
    tax_id: "VN-80983214",
    phone: "+84 (24) 3894-1192",
    shared_identifiers: ["ENT-903"] // Shares shipping agent addresses
  },
  {
    entity_id: "ENT-903",
    entity_type: "Manufacturer",
    entity_name: "Tianshan Solar Materials Corp",
    country: "China",
    risk_level: "Critical",
    sanctions_status: "Blocked list",
    known_affiliations: ["Vina Solar Technologies LLC", "Urumqi Chemical Logistics"],
    enforcement_history: "Placed on Uyghur Forced Labor Prevention Act (UFLPA) Entity List as of August 2024. Subject to absolute importation ban.",
    ownership_indicators: "Directly owned subsidiary of Xinjiang State Development & Energy Investment Group.",
    registration_status: "Sanctioned - Restricted Entity No. US-DHS-2024-UFLPA",
    watchlist_status: "UFLPA Restricted Entity List",
    address: "710 Tianshan Industrial Avenue, Midong District, Urumqi, Xinjiang, China",
    tax_id: "CN-9165010078",
    phone: "+86 (991) 489-0219",
    shared_identifiers: []
  },
  {
    entity_id: "ENT-904",
    entity_type: "Broker",
    entity_name: "Asia Pacific Energy Logistics",
    country: "Hong Kong",
    risk_level: "High",
    sanctions_status: "None",
    known_affiliations: ["BrightPath Solar Corp", "Jiangsu Maritime Forwarders"],
    enforcement_history: "Filing agent on 12 flagged evasive routings under investigation. Acted as central billing intermediary in currency shell swap.",
    ownership_indicators: "Incorporated in Hong Kong as blind private nominee trust.",
    registration_status: "HK-CR Registered No. 29310892",
    watchlist_status: "Entity Resolution Flagged",
    address: "Kowloon Finance Center, Suite 1009, 21 Nathan Road, Kowloon, Hong Kong",
    tax_id: "HK-2893108",
    phone: "+852 (2) 555-0192",
    shared_identifiers: ["ENT-901"]
  },

  // Entities for Structural Steel Case (CBP-2026-5512)
  {
    entity_id: "ENT-501",
    entity_type: "Importer",
    entity_name: "Apex Steel Builders Group",
    country: "United States",
    risk_level: "High",
    sanctions_status: "Under Investigation",
    known_affiliations: ["Sriracha Steel Mills", "Bang Laem Maritime Brokers"],
    enforcement_history: "Customs audit penalty of $142,000 in 2024 for misclassification of structural beams under flat-rolled tariff exclusions.",
    ownership_indicators: "Owned entirely by Apex Holding LLC, structured through Cayman Islands.",
    registration_status: "Active - CBP Customs Bond No. 24-B9041",
    watchlist_status: "Audit Watchlist",
    address: "180 East Broad Street, Columbus, OH 43215",
    tax_id: "31-0984120",
    phone: "+1 (614) 222-1092",
    shared_identifiers: []
  },
  {
    entity_id: "ENT-502",
    entity_type: "Exporter",
    entity_name: "Sriracha Steel Mills LTD",
    country: "Thailand",
    risk_level: "Critical",
    sanctions_status: "None",
    known_affiliations: ["Apex Steel Builders", "Hebei Carbon-Steel Rolled Corp"],
    enforcement_history: "Identified as core shipping hub of circular Chinese billing under trade enforcement raid 2025. Documented taking large raw billets from Tangshan Harbor and applying zinc lacquer coat to claim local origin.",
    ownership_indicators: "Joint venture 60% funded by Chinese steel conglomerate Tangshan Iron & Steel Co.",
    registration_status: "Active Thai ID: 0205562100",
    watchlist_status: "Tariff Evasion Flagged",
    address: "71 Sukhumvit Road, Sriracha District, Chonburi 20110, Thailand",
    tax_id: "TH-02052109",
    phone: "+66 (38) 4920-112",
    shared_identifiers: []
  }
];

export const INITIAL_SHIPMENTS: Shipment[] = [
  // Shipments for Solar modules (CBP-2026-9041)
  {
    shipment_id: "SH-904101",
    origin_country: "Vietnam",
    destination_country: "United States",
    declared_origin: "Vietnam",
    suspected_origin: "China",
    product_code: "8541.43.0030",
    product_description: "Solar Crystalline Silicon Photovoltaic Modules, pre-assembled panel structures 440W.",
    route: ["Tianjin Port (Origin)", "Hai Phong Port (Transit-Swap)", "Naha Port (Coaling)", "Los Angeles Port (Discharge)"],
    container_id: "MSKU-8209412",
    manifest_data: {
      shipper: "Vina Solar Technologies LLC",
      consignee: "BrightPath Solar Corp",
      weight_kg: 24310,
      declared_value_usd: 142000,
      carrier: "Maersk Shipping Lines",
      vessel: "Maersk Mc-Kinney Moller",
      voyage_number: "2604-W2",
      bill_of_lading: "MSK9041029108"
    },
    manifest_anomalies: [
      "Container dead-weight discrepancy: Shipment claims silicon module assemblies, but physical container gross weight exceeds maximum crystalline silicon composite threshold by 14%",
      "Circular billing routing: Invoice originates from Asia Pacific Energy Logistics (HK), but shipping physical cargo moves from Tianjin on joint feeder-lines"
    ],
    ai_anomaly_score: 89,
    customs_flags: ["Origin Mismatch", "Weight Discrepancy", "Restricted Carrier Loop"],
    inspection_history: "Uninspected at current dock; held under physical examination order at Los Angeles Port terminal 400.",
    date: "2026-05-18"
  },
  {
    shipment_id: "SH-904102",
    origin_country: "Vietnam",
    destination_country: "United States",
    declared_origin: "Vietnam",
    suspected_origin: "China",
    product_code: "8541.43.0030",
    product_description: "Solar Photovoltaic Cell Silicon Arrays framework.",
    route: ["Shanghai Port", "Hai Phong Port (Transit)", "Long Beach Port (Discharge)"],
    container_id: "OOLU-9104821",
    manifest_data: {
      shipper: "Vina Solar Technologies LLC",
      consignee: "BrightPath Solar Corp",
      weight_kg: 22010,
      declared_value_usd: 124500,
      carrier: "OOCL Shipping LLC",
      vessel: "OOCL Germany",
      voyage_number: "045-E",
      bill_of_lading: "OOL28109489"
    },
    manifest_anomalies: [
      "No direct local factory input: Cross-border trucking logs between Bac Giang and Chinese border are aligned with shipment cargo loading times"
    ],
    ai_anomaly_score: 74,
    customs_flags: ["Filing Pattern Shock"],
    inspection_history: "CBP Border agent document query dispatched to BrightPath on 2026-05-19. Importer response pending.",
    date: "2026-05-15"
  },
  {
    shipment_id: "SH-904103",
    origin_country: "Vietnam",
    destination_country: "United States",
    declared_origin: "Vietnam",
    suspected_origin: "China",
    product_code: "8541.43.0030",
    product_description: "High efficiency multi-junction Photovoltaic Panels.",
    route: ["Hai Phong Port", "Seattle Port"],
    container_id: "EMCU-1829410",
    manifest_data: {
      shipper: "Vina Solar Technologies LLC",
      consignee: "BrightPath Solar Corp",
      weight_kg: 23400,
      declared_value_usd: 131000,
      carrier: "Evergreen Marine",
      vessel: "Ever Glory",
      voyage_number: "EG-113",
      bill_of_lading: "EGLV1089204"
    },
    manifest_anomalies: [],
    ai_anomaly_score: 30,
    customs_flags: [],
    inspection_history: "Passed preliminary desktop clearance 2026-05-11. Released from terminal.",
    date: "2026-05-11"
  },

  // Structural Steel Case (CBP-2026-5512)
  {
    shipment_id: "SH-551201",
    origin_country: "Thailand",
    destination_country: "United States",
    declared_origin: "Thailand",
    suspected_origin: "China",
    product_code: "7308.90.9590",
    product_description: "Pre-fabricated heavy structural alloy beams.",
    route: ["Tangshan Port", "Ban Laem (Transit)", "Sriracha (Container Load)", "New York Port"],
    container_id: "TGBU-9021810",
    manifest_data: {
      shipper: "Sriracha Steel Mills LTD",
      consignee: "Apex Steel Builders Group",
      weight_kg: 44100,
      declared_value_usd: 310000,
      carrier: "COSCO Logistics",
      vessel: "COSCO Nebula",
      voyage_number: "C-904",
      bill_of_lading: "COSB910248"
    },
    manifest_anomalies: [
      "Origin processing energy index mismatch: Processing billets into heavy structural shapes requires high-energy smelting logs. Regional municipal supply records show zero mechanical rolling mills active at the Sriracha yard location.",
      "Inward-Outward imbalance: Sriracha yard imported 50,000 tons of rough carbon raw steel from Tangshan last month, and exported exactly 49,850 tons of 'Thai premium' structural shapes this week."
    ],
    ai_anomaly_score: 95,
    customs_flags: ["Origin Evasion Likelihood", "Inward-Outward Volumetric Balance Alarm", "Sanctioned Mill Correlation"],
    inspection_history: "Active targeting order. Held at NY Newark Port Terminal A for destructive physical chemical testing of steel alloys.",
    date: "2026-05-14"
  }
];

export const INITIAL_FINDINGS: AIFinding[] = [
  {
    finding_id: "FIND-901",
    title: "Uyghur Forced Labor Prevention Act (UFLPA) Direct Wave Match",
    confidence: 94,
    finding_type: "Origin Concealment",
    severity: "Critical",
    explanation: "Deep ledger auditing reveals Vina Solar Technologies acts as a processing shell back-hauling state-subsidized polysilicon blocks fabricated in prohibited Midong-based manufacturing complexes of Tianshan Solar Materials, utilizing falsified inland bills of lading prior to Sea shipment.",
    evidence_links: ["SH-904101", "ENT-902", "ENT-903"],
    verification_status: "Accepted"
  },
  {
    finding_id: "FIND-902",
    title: "Tri-Party Circular Invoice Flow Strategy",
    confidence: 87,
    finding_type: "Circular Invoicing",
    severity: "High",
    explanation: "BrightPath Solar Corp sends monetary consideration to broker Asia Pacific Energy (HK). The funds flow into Nominee Private Banking accounts while cargo manifests are systematically back-dated directly to Changzhou factories, hiding direct transactions with the true restricted manufacturing source.",
    evidence_links: ["ENT-901", "ENT-904", "SH-904101"],
    verification_status: "Accepted"
  },
  {
    finding_id: "FIND-903",
    title: "Vessel AIS Routing Shield Alert",
    confidence: 78,
    finding_type: "Routing Deviation",
    severity: "Medium",
    explanation: "Maersk feeder vessels loading cargo containers designated for Vina Solar turned off AIS (Automatic Identification System) transponders for 36 hours during passage through critical strait coordinates, coinciding precisely with local unregistered trans-loading operations.",
    evidence_links: ["SH-904102"],
    verification_status: "Needs Review"
  }
];

export const INITIAL_REFERRALS: ReferralPackage[] = [
  {
    referral_id: "REF-9041",
    case_id: "CBP-2026-9041",
    package_status: "Draft",
    generated_date: "2026-05-20",
    approval_state: "Under Analyst Review",
    evidence_inventory_ids: ["SH-904101", "SH-904102", "ENT-901", "ENT-902", "ENT-903", "FIND-901", "FIND-902"],
    narrative: {
      executive_summary: "The CBP Investigative Command has established a case for criminal evasion of Section 301 duties and violation of the Uyghur Forced Labor Prevention Act (UFLPA). BrightPath Solar Corp systematically imported solar PV modules through Viet Yen/Bac Giang Province, Vietnam, which were documented to be originating from the Xinjiang UFLPA restricted entity Tianshan Solar Materials Corp. Imposed remedies total $8.4M in unpaid tariffs and immediate seizure of current maritime inventory.",
      subject_overview: "BrightPath Solar Corp is the consignee / importer of record headquartered in Menlo Park, California. The primary transshipping intermediary is Vina Solar Technologies LLC (Vietnam), which operates as a facade facility with insufficient power grids to run critical ingot-scaling or cell manufacturing. The true manufacturing origin is Tianshan Solar Materials Corp (Urumqi, CN).",
      investigation_findings: "1. Raw wafer trace records: Audit records indicate direct flow of high-metallurgical polysilicon blocks from Xinjiang to Hainan, cross-border truck-haul to Vietnam.\n2. Container physical density mismatch: Registered containers weighed 14% higher than documented silicon structures, indicative of concealed raw steel frame components shipped together to obfuscate total customs valuation.",
      trade_pattern_analysis: "Visual mapping demonstrates classic transshipment: China production -> Vietnam border cross -> Minimal relabeling/packaging in Vietnam EPZ (Export Processing Zones) -> US Port of Los Angeles. Inward-outward container audits reveal zero local consumption or domestic consumption of raw components in Vietnam.",
      evidence_summary: "- Master Cargo Bill of Lading MSK9041029108 representing 24MT solar modules.\n- DHS physical yard audit reports confirming lack of smelting machines at Vietnam plant.\n- Bank ledger trail under Broker Asia Pacific Energy (HK) matching the Changzhou transaction dates.",
      applicable_violations: "1. 19 U.S.C. § 1592: Penalties for fraud, gross negligence, and negligence.\n2. UFLPA Public Law 117-78: Statutory exclusion of goods manufactured in Xinjiang.\n3. 18 U.S.C. § 545: Smuggling goods into the United States.",
      recommended_enforcement: "1. Issue immediate red targeting orders for all subsequent container filings corresponding to consignee BrightPath Solar.\n2. Establish statutory seize-and-hold at LAPD terminals.\n3. Refer the case file to the Department of Justice (DOJ) for criminal enforcement under 18 U.S.C. § 545."
    }
  }
];

export const INITIAL_THREAT_FEED: ThreatFeedEvent[] = [
  {
    id: "evt_101",
    severity: "Critical",
    title: "Sanctioned Mill Correlation Detected",
    description: "Container TGBU-9021810 currently entering NY seaport contains steel billets tracked to Tangshan Heavy Steel Co.",
    timestamp: "10 min ago",
    confidence: 96,
    related_entity: "ENT-502",
    related_case_id: "CBP-2026-5512"
  },
  {
    id: "evt_102",
    severity: "High",
    title: "AIS Signal Spoof Alarm",
    description: "Feeder Vessel loading solar cells entering Da Nang exhibited circular coordinates, masking true origin port loading in Guangzhou.",
    timestamp: "42 min ago",
    confidence: 87,
    related_entity: "Pacific Wood & Veneer Import Inc",
    related_case_id: "CBP-2026-7815"
  },
  {
    id: "evt_103",
    severity: "Medium",
    title: "Evasive Postal Code Filing Match",
    description: "New registration filer Summit Global Metals matches a registered business address blacklisted during the 2024 Aluminum Enforcements.",
    timestamp: "2 hours ago",
    confidence: 79,
    related_entity: "Summit Global Metals Corp",
    related_case_id: "CBP-2026-3108"
  },
  {
    id: "evt_104",
    severity: "Critical",
    title: "Rapid Filing Volume Spurt",
    description: "Bac Giang exporter filings spiked 340% within 4 days, contrasting starkly with regional freight train limits.",
    timestamp: "4 hours ago",
    confidence: 91,
    related_case_id: "CBP-2026-9041"
  }
];
