/**
 * Production API client with real backend integration
 * 
 * Production API client with bulletproof backend integration:
 * - Real TypeScript types from OpenAPI spec
 * - Comprehensive error handling with retry logic
 * - Authentication support
 * - Request/response logging
 * - Brand canon enforcement integration
 * - Real cost tracking display
 */

// Re-export everything from the new production API client
export {
  api,
  apiClient,
  NanoDesignerAPIClient,
  NanoDesignerAPIError,
  type RenderRequest,
  type RenderResponse,
  type IngestRequest,
  type IngestResponse,
  type CanonDeriveRequest,
  type CanonDeriveResponse,
  type CritiqueRequest,
  type CritiqueResponse,
  type APIError,
  type APIClientConfig,
} from './api-client';

// Legacy compatibility types
export type AsyncRenderResponse = { job_id: string };
export type JobStatusResponse = any; // Will be properly typed when async endpoints are implemented

// Convenience function for setting auth token (backward compatibility)
export function setAuthTokenProvider(fn: () => Promise<string | null>) {
  const { apiClient } = require('./api-client');
  apiClient.setAuthTokenProvider(fn);
}

