/**
 * Centralized API URL resolver
 *
 * Usage:
 * - Development (local Docker): Uses nginx proxy at /api → http://sentry-api:8000
 * - Staging/Production (Cloud Run): Uses VITE_API_URL set at build time
 *
 * NEVER try to extract hash from sentry-ui URL and construct sentry-api URL
 * because services have different hash codes when deployed separately.
 */

export const getAPIBaseURL = (): string => {
  if (typeof window === 'undefined') return '/api';

  // Priority 1: Build-time env var (set in Docker/Cloud Run)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // Priority 2: Local development or relative paths
  // Use nginx proxy at /api
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
