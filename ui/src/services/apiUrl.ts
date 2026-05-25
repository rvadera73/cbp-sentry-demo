/**
 * Centralized API URL resolver
 *
 * Usage:
 * - Local Docker: VITE_API_URL="" → uses /api (nginx proxy to sentry-api:8000)
 * - Cloud Run: VITE_API_URL="" → detects hash from sentry-ui URL, derives sentry-api URL
 * - Staging: VITE_API_URL="https://api.example.com" → uses explicit URL
 */

export const getAPIBaseURL = (): string => {
  if (typeof window === 'undefined') return '/api';

  // Priority 1: Explicit API URL from build-time env var
  if (import.meta.env.VITE_API_URL) {
    console.log('[apiUrl] Using VITE_API_URL:', import.meta.env.VITE_API_URL);
    return import.meta.env.VITE_API_URL;
  }

  const hostname = window.location.hostname;
  console.log('[apiUrl] Hostname:', hostname);

  // Priority 2: Local development (localhost)
  // Use nginx proxy at /api → http://sentry-api:8000
  if (hostname === 'localhost' || hostname.startsWith('localhost:')) {
    console.log('[apiUrl] Using localhost proxy: /api');
    return '/api';
  }

  // Priority 3: Cloud Run (sentry-ui-<HASH>.<REGION>.run.app)
  // Extract hash and region, construct sentry-api URL with same hash and region
  const cloudRunMatch = hostname.match(/^sentry-ui-(-?\d+)\.([\w\-]+)\.run\.app$/);
  if (cloudRunMatch) {
    const [, hash, region] = cloudRunMatch;
    const url = `https://sentry-api-${hash}.${region}.run.app/api`;
    console.log('[apiUrl] Cloud Run match - hash:', hash, 'region:', region, 'url:', url);
    return url;
  }

  // Fallback
  console.log('[apiUrl] No match - falling back to /api');
  return '/api';
};

export const API_BASE_URL = getAPIBaseURL();

/**
 * Construct full API endpoint URL
 * @param path - API path (e.g., '/api/shipments')
 * @returns Full URL
 */
export const getAPIEndpoint = (path: string): string => {
  const baseUrl = API_BASE_URL;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  // If baseUrl is already a full URL (http/https), append path
  if (baseUrl.startsWith('http')) {
    return `${baseUrl}${cleanPath}`;
  }

  // Otherwise, baseUrl is relative (like /api), append to it
  return `${baseUrl}${cleanPath}`;
};
