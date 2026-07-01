"""Load the REAL EAPA entity network (from the PDF harvester) into senzing.

Reads the harvester CSVs:
  eapa_entities.csv       eapa_case, entity_name, role, country, source_pdf
  eapa_relationships.csv  eapa_case, src_entity, rel_type, dst_entity

and:
  1. writes each distinct EAPA entity into senzing_entities (data_source=CBP-EAPA,
     CORD-shaped raw_data carrying role(s) + case(s)),
  2. writes the within-case relationships into senzing_relationships (real edges,
     not curated seeds),
  3. CROSS-REFERENCES each EAPA entity name against the existing CORD 244K
     (GLEIF/OFAC/OPEN-SANCTIONS/ICIJ/OpenOwnership) by normalized name and emits a
     MATCHES_CORD edge to any real hit — surfacing the *additional* entities and
     networks these actors are tied to.

Idempotent: clears prior CBP-EAPA-REAL edges (evidence LIKE 'eapa-real:%') before
re-inserting; entities are INSERT OR REPLACE.

Usage (host or container):
  python load_eapa_network.py --entities <path> --relationships <path> [--db /app/data/senzing.db]
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, sqlite3, sys
from collections import defaultdict

CORD_SOURCES = ("GLEIF", "OFAC", "OPEN-SANCTIONS", "ICIJ", "OPEN-OWNERSHIP", "OPEN_OWNERSHIP", "US-LABOR-VIOLATIONS", "GLOBALDATA")
_SUFFIX = re.compile(r"\b(inc|incorporated|llc|l\.l\.c|ltd|limited|co|corp|corporation|company|coalition|group|trading|industries|industrial|manufacturing|mfg|jsc|gmbh|pte|sdn bhd|srl|plc)\b\.?", re.I)
REL_MAP = {
    "CO_RESPONDENT": "CO_RESPONDENT", "SUPPLIED_BY": "SUPPLIED_BY",
    "ALLEGED_BY": "ALLEGED_BY", "RELATED_ENTITY": "RELATED_ENTITY",
}


def normname(s: str) -> str:
    s = (s or "").lower()
    s = _SUFFIX.sub(" ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def eid_for(name: str) -> str:
    return "EAPA:" + hashlib.sha1(normname(name).encode()).hexdigest()[:12]


def read_csv(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("SENZING_DB_PATH", "/app/data/senzing.db"))
    ap.add_argument("--entities", default="/app/reference/eapa_entities.csv")
    ap.add_argument("--relationships", default="/app/reference/eapa_relationships.csv")
    ap.add_argument("--registry", default="/app/reference/entity_registry.csv")
    ap.add_argument("--registry-rels", default="/app/reference/entity_registry_relationships.csv")
    args = ap.parse_args()

    ents = read_csv(args.entities)
    rels = read_csv(args.relationships)
    if not ents:
        print(f"[load_eapa] no entities at {args.entities} — nothing to do")
        return 1

    # --- collapse to distinct entities by normalized name ---
    nodes = {}  # nn -> {name, country, roles:set, cases:set}
    for r in ents:
        nm = (r.get("entity_name") or "").strip()
        nn = normname(nm)
        if not nn or len(nn) < 3:
            continue
        n = nodes.setdefault(nn, {"name": nm, "country": "", "roles": set(), "cases": set()})
        if not n["country"] and r.get("country"):
            n["country"] = r["country"].strip()
        if r.get("role"):
            n["roles"].add(r["role"].strip())
        if r.get("eapa_case"):
            n["cases"].add(r["eapa_case"].strip())

    conn = sqlite3.connect(args.db)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS senzing_entities (entity_id TEXT PRIMARY KEY, data_source TEXT, "
        "record_id TEXT, name_primary TEXT, country TEXT, entity_type TEXT, confidence REAL DEFAULT 1.0, "
        "raw_data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS senzing_relationships (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "entity_id_a TEXT, entity_id_b TEXT, relationship_type TEXT, confidence REAL, evidence TEXT)")
    cur = conn.cursor()
    # idempotent: drop prior real-EAPA edges
    cur.execute("DELETE FROM senzing_relationships WHERE evidence LIKE 'eapa-real:%'")

    # --- write entities ---
    for nn, n in nodes.items():
        eid = eid_for(n["name"])
        roles = sorted(n["roles"]) or ["importer"]
        raw = {
            "DATA_SOURCE": "CBP-EAPA", "RECORD_TYPE": "ORGANIZATION",
            "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": n["name"]}],
            "FLAG": "eapa_respondent" if "importer" in roles else "eapa_party",
            "EAPA_ROLES": roles, "EAPA_CASES": sorted(n["cases"]), "COUNTRY": n["country"],
        }
        cur.execute(
            "INSERT OR REPLACE INTO senzing_entities (entity_id, data_source, record_id, name_primary, "
            "country, entity_type, confidence, raw_data) VALUES (?,?,?,?,?,?,?,?)",
            (eid, "CBP-EAPA", (sorted(n["cases"]) or [""])[0], n["name"], n["country"],
             "organization", 1.0, json.dumps(raw)))

    # --- write within-case relationships (real edges) ---
    edge_n = 0
    for r in rels:
        a, b = (r.get("src_entity") or "").strip(), (r.get("dst_entity") or "").strip()
        if not a or not b or normname(a) == normname(b):
            continue
        rt = REL_MAP.get((r.get("rel_type") or "").strip().upper(), (r.get("rel_type") or "RELATED_ENTITY").strip().upper())
        cur.execute(
            "INSERT INTO senzing_relationships (entity_id_a, entity_id_b, relationship_type, confidence, evidence) "
            "VALUES (?,?,?,?,?)",
            (eid_for(a), eid_for(b), rt, 0.9, f"eapa-real:{r.get('eapa_case','')}"))
        edge_n += 1

    # --- cross-reference to CORD 244K by normalized name ---
    xref_n = 0
    q = "SELECT entity_id, name_primary, data_source FROM senzing_entities WHERE data_source IN ({})".format(
        ",".join("?" * len(CORD_SOURCES)))
    cord = cur.execute(q, CORD_SOURCES).fetchall()
    cord_by_nn = defaultdict(list)
    for cid, cname, csrc in cord:
        cord_by_nn[normname(cname)].append((cid, cname, csrc))
    for nn, n in nodes.items():
        if len(nn) < 6:  # avoid trivial-name false hits
            continue
        for cid, cname, csrc in cord_by_nn.get(nn, [])[:3]:
            cur.execute(
                "INSERT INTO senzing_relationships (entity_id_a, entity_id_b, relationship_type, confidence, evidence) "
                "VALUES (?,?,?,?,?)",
                (eid_for(n["name"]), cid, "MATCHES_CORD", 0.85, f"eapa-real:xref:{csrc}"))
            xref_n += 1

    # --- registry enrichment (GLEIF/EDGAR/OpenCorporates): identity + affiliates ---
    reg_ent, reg_rel = read_csv(args.registry), read_csv(args.registry_rels)
    reg_nodes = reg_edges = enriched = 0
    for r in reg_ent:
        eid = eid_for((r.get("entity_name") or "").strip())
        row = cur.execute("SELECT raw_data, country FROM senzing_entities WHERE entity_id=?", (eid,)).fetchone()
        if not row:
            continue
        try:
            raw = json.loads(row[0]) if row[0] else {}
        except Exception:
            raw = {}
        raw["REGISTRY"] = {k: r.get(k) for k in ("source", "matched_name", "identifier", "address", "incorporation_date", "status")}
        cur.execute("UPDATE senzing_entities SET raw_data=?, country=? WHERE entity_id=?",
                    (json.dumps(raw), r.get("country") or row[1] or "", eid))
        enriched += 1
    for r in reg_rel:
        src, dst = (r.get("src_name") or "").strip(), (r.get("dst_name") or "").strip()
        if not src or not dst:
            continue
        rt = (r.get("rel_type") or "AFFILIATE").strip().upper()
        deid = eid_for(dst)
        if not cur.execute("SELECT 1 FROM senzing_entities WHERE entity_id=?", (deid,)).fetchone():
            araw = {"DATA_SOURCE": "REGISTRY", "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": dst}],
                    "FLAG": "eapa_affiliate", "REGISTRY_SOURCE": r.get("source", "")}
            cur.execute("INSERT OR REPLACE INTO senzing_entities (entity_id, data_source, record_id, name_primary, "
                        "country, entity_type, confidence, raw_data) VALUES (?,?,?,?,?,?,?,?)",
                        (deid, "REGISTRY", r.get("dst_identifier", "") or "", dst, "", "organization", 0.9, json.dumps(araw)))
            reg_nodes += 1
        cur.execute("INSERT INTO senzing_relationships (entity_id_a, entity_id_b, relationship_type, confidence, evidence) "
                    "VALUES (?,?,?,?,?)", (eid_for(src), deid, rt, 0.9, f"eapa-real:registry:{r.get('source','')}"))
        reg_edges += 1

    conn.commit()
    conn.close()
    print(f"[load_eapa] entities={len(nodes)} within-case-edges={edge_n} cord-xref-edges={xref_n} "
          f"| registry: enriched={enriched} affiliate-nodes={reg_nodes} ownership-edges={reg_edges}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
