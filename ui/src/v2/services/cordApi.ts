/**
 * CORD Entity Resolution data layer — talks to the real /api/cord/* endpoints
 * (243K-entity Senzing-backed service via the sentry-api gateway).
 */

export interface CordMatch {
  entity_id: string;
  name: string;
  country?: string;
  data_source?: string;
  confidence?: number;
  flag?: string;       // watchlist only: sanctioned | forced_labor | offshore | high_risk
  program?: string;
}

export interface EntityDetail {
  entity: any;     // full resolved record (name, country, entity_type, raw_data: NAMES/ADDRESSES/SDN_PROGRAM…)
  chain: any[];    // ownership chain
  parties: any[];  // related parties
}

const hasName = (e: any) => e && typeof e.name === 'string' && e.name.trim().length > 0;

/** Best-effort name from a raw CORD record (service detail leaves it blank for
 * several sources — same gap as the index name_primary). */
function nameFromRaw(raw: any): string {
  for (const key of ['NAMES', 'NAME_LIST']) {
    const arr = raw?.[key];
    if (Array.isArray(arr) && arr.length) {
      const prim = arr.find((n: any) => n.NAME_TYPE === 'PRIMARY') || arr[0];
      const org = prim.NAME_ORG || prim.NAME_FULL;
      if (org) return org;
      const full = [prim.PRIMARY_NAME_FIRST, prim.PRIMARY_NAME_MIDDLE, prim.PRIMARY_NAME_LAST].filter(Boolean).join(' ').trim();
      if (full) return full;
    }
  }
  for (const key of ['PRIMARY_NAME_ORG', 'LEGAL_NAME_ORG', 'NAME', 'name', 'Title']) {
    if (raw?.[key]) return String(raw[key]);
  }
  return '';
}

function countryFromRaw(raw: any): string {
  const c = raw?.COUNTRIES;
  if (Array.isArray(c) && c.length) return c[0].REGISTRATION_COUNTRY || c[0].COUNTRY || c[0].ADDR_COUNTRY || '';
  return raw?.COUNTRY_CODE || raw?.BUSINESS_ADDR_STATE || '';
}

/** Default flagged/sanctioned watchlist (no search). */
export async function cordWatchlist(limit = 40): Promise<CordMatch[]> {
  try {
    const r = await fetch(`/api/cord/watchlist?limit=${limit}`);
    if (!r.ok) return [];
    const d = await r.json();
    return (d.entities || []).filter(hasName);
  } catch { return []; }
}

/** Search across all CORD entities by name. */
export async function cordSearch(name: string, limit = 30): Promise<CordMatch[]> {
  // Strip FTS5 operator characters so queries like "co., ltd." don't 500.
  const term = name.replace(/[^\p{L}\p{N}\s]/gu, ' ').trim();
  if (!term) return [];
  try {
    const r = await fetch(`/api/cord/search?name=${encodeURIComponent(term)}&limit=${limit}`);
    if (!r.ok) return [];
    const d = await r.json();
    return (d.matches || []).filter(hasName);
  } catch { return []; }
}

/** Full detail for one entity: record + ownership chain + related parties. */
export async function cordEntityDetail(entityId: string): Promise<EntityDetail> {
  const enc = encodeURIComponent(entityId);
  const safe = async (u: string) => { try { const r = await fetch(u); return r.ok ? await r.json() : {}; } catch { return {}; } };
  const [e, c, p] = await Promise.all([
    safe(`/api/cord/entity/${enc}`),
    safe(`/api/cord/entity/${enc}/chain`),
    safe(`/api/cord/entity/${enc}/parties`),
  ]);
  // /entity returns { entity: { entity: {...} } }
  const entity = e?.entity?.entity || e?.entity || {};
  const raw = entity.raw_data || {};
  if (!entity.name || !entity.name.trim()) entity.name = nameFromRaw(raw);
  if (!entity.country) entity.country = countryFromRaw(raw);
  return { entity, chain: Array.isArray(c?.chain) ? c.chain : [], parties: Array.isArray(p?.parties) ? p.parties : [] };
}

/** Lightweight risk for a list row (only flag/source known, not full detail). */
export function flagRisk(flag?: string, source?: string): { score: number; tier: string } {
  const f = flag || '';
  const s = (source || '').toUpperCase();
  if (f === 'sanctioned' || s === 'OFAC' || s === 'OPEN-SANCTIONS') return { score: 92, tier: 'CRITICAL' };
  if (f === 'forced_labor' || s === 'US-LABOR-VIOLATIONS') return { score: 78, tier: 'HIGH' };
  if (f === 'offshore' || s === 'ICIJ') return { score: 64, tier: 'HIGH' };
  if (f === 'high_risk' || s === 'NOMINO-RISK') return { score: 58, tier: 'MEDIUM' };
  return { score: 30, tier: 'LOW' };
}

/** Derive a 0-100 risk score + tier from real entity signals. */
export function entityRisk(detail: EntityDetail, flag?: string): { score: number; tier: string; signals: string[] } {
  const raw = detail.entity?.raw_data || {};
  const src = (detail.entity?.data_source || '').toUpperCase();
  const signals: string[] = [];
  let score = 25;

  const sdn = raw.SDN_PROGRAM || raw.OFAC_PROGRAM;
  if (sdn || flag === 'sanctioned' || src === 'OFAC' || src === 'OPEN-SANCTIONS') { score = 92; signals.push(`OFAC/sanctions listing${sdn ? ` (${sdn})` : ''}`); }
  else if (flag === 'forced_labor' || src === 'US-LABOR-VIOLATIONS') { score = 78; signals.push('US forced-labor / labor violation record'); }
  else if (flag === 'offshore' || src === 'ICIJ') { score = 64; signals.push('Appears in ICIJ offshore-leaks data'); }
  else if (flag === 'high_risk' || src === 'NOMINO-RISK') { score = 58; signals.push('Flagged in third-party risk data'); }

  const chainDepth = detail.chain?.length || 0;
  if (chainDepth >= 3) { score = Math.min(100, score + 8); signals.push(`Multi-layer ownership chain (${chainDepth} levels)`); }
  const partyCount = detail.parties?.length || 0;
  if (partyCount >= 4) { score = Math.min(100, score + 5); signals.push(`Dense related-party network (${partyCount})`); }

  const tier = score >= 80 ? 'CRITICAL' : score >= 60 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW';
  return { score, tier, signals };
}
