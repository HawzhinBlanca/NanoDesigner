/**
 * Production-grade API client for NanoDesigner backend
 * 
 * This client provides type-safe access to all backend endpoints with:
 * - Real TypeScript types from OpenAPI spec
 * - Comprehensive error handling
 * - Authentication support
 * - Request/response logging
 * - Retry logic for transient failures
 */

import { components, paths } from '@sgd/types';

// Extract types from the OpenAPI spec
export type RenderRequest = components['schemas']['RenderRequest'];
export type RenderResponse = components['schemas']['RenderResponse'];
export type IngestRequest = components['schemas']['IngestRequest'];
export type IngestResponse = components['schemas']['IngestResponse'];
export type CanonDeriveRequest = components['schemas']['CanonDeriveRequest'];
export type CanonDeriveResponse = components['schemas']['CanonDeriveResponse'];
export type CritiqueRequest = components['schemas']['CritiqueRequest'];
export type CritiqueResponse = components['schemas']['CritiqueResponse'];

// API Error types
export interface APIError {
  error: string;
  message: string;
  trace_id?: string;
  details?: Record<string, any>;
}

class NanoDesignerAPIError extends Error {
  public readonly status: number;
  public readonly error: APIError;
  public readonly traceId?: string;

  constructor(status: number, error: APIError) {
    super(error.message);
    this.name = 'NanoDesignerAPIError';
    this.status = status;
    this.error = error;
    this.traceId = error.trace_id;
  }

  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }

  get isRateLimited(): boolean {
    return this.status === 429;
  }

  get isContentPolicyViolation(): boolean {
    return this.status === 400 && this.error.error === 'ContentPolicyViolationException';
  }

  get isValidationError(): boolean {
    return this.status === 422;
  }
}

// Configuration
export interface APIClientConfig {
  baseURL?: string;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
  authTokenProvider?: () => Promise<string | null>;
  onError?: (error: NanoDesignerAPIError) => void;
  onRequest?: (url: string, init: RequestInit) => void;
  onResponse?: (url: string, response: Response) => void;
}

const DEFAULT_CONFIG: Required<APIClientConfig> = {
  baseURL: process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000',
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
  authTokenProvider: async () => null,
  onError: () => {},
  onRequest: () => {},
  onResponse: () => {},
};

class NanoDesignerAPIClient {
  private config: Required<APIClientConfig>;

  constructor(config: APIClientConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Update the authentication token provider
   */
  setAuthTokenProvider(provider: () => Promise<string | null>): void {
    this.config.authTokenProvider = provider;
  }

  /**
   * Make an authenticated request with retry logic
   */
  private async request<T>(
    endpoint: string,
    init: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseURL}${endpoint}`;
    
    // Add authentication if available
    const token = await this.config.authTokenProvider();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((init.headers as Record<string, string>) || {}),
    };
    
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const requestInit: RequestInit = {
      ...init,
      headers,
      signal: AbortSignal.timeout(this.config.timeout),
    };

    // Log request
    this.config.onRequest(url, requestInit);

    let lastError: Error | null = null;

    // Retry logic
    for (let attempt = 0; attempt <= this.config.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, requestInit);
        
        // Log response
        this.config.onResponse(url, response);

        if (!response.ok) {
          const errorData = await this.parseErrorResponse(response);
          const apiError = new NanoDesignerAPIError(response.status, errorData);
          
          // Don't retry client errors (4xx) except rate limits
          if (apiError.isClientError && !apiError.isRateLimited) {
            this.config.onError(apiError);
            throw apiError;
          }
          
          // Don't retry on the last attempt
          if (attempt === this.config.retryAttempts) {
            this.config.onError(apiError);
            throw apiError;
          }
          
          lastError = apiError;
        } else {
          // Success - parse and return response
          const data = await response.json();
          return data as T;
        }
      } catch (error) {
        if (error instanceof NanoDesignerAPIError) {
          throw error;
        }
        
        lastError = error as Error;
        
        // Don't retry on the last attempt
        if (attempt === this.config.retryAttempts) {
          break;
        }
      }

      // Wait before retry (exponential backoff)
      if (attempt < this.config.retryAttempts) {
        const delay = this.config.retryDelay * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    // All retries exhausted
    throw lastError || new Error('Request failed after all retry attempts');
  }

  /**
   * Parse error response from the API
   */
  private async parseErrorResponse(response: Response): Promise<APIError> {
    try {
      const data = await response.json();
      
      // Handle FastAPI validation errors
      if (response.status === 422 && data.detail) {
        return {
          error: 'ValidationError',
          message: 'Request validation failed',
          details: { validation_errors: data.detail },
        };
      }
      
      // Handle our custom error format
      if (data.error && data.message) {
        return data as APIError;
      }
      
      // Handle generic errors
      return {
        error: 'APIError',
        message: data.detail || data.message || 'An error occurred',
        details: data,
      };
    } catch {
      // Fallback for non-JSON responses
      const text = await response.text();
      return {
        error: 'HTTPError',
        message: text || `HTTP ${response.status} ${response.statusText}`,
      };
    }
  }

  /**
   * Generate graphic designs using AI
   */
  async render(request: RenderRequest): Promise<RenderResponse> {
    return this.request<RenderResponse>('/render', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Start asynchronous rendering job
   */
  async renderAsync(request: RenderRequest): Promise<{ job_id: string }> {
    return this.request<{ job_id: string }>('/render/async', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get status of asynchronous rendering job
   */
  async getJobStatus(jobId: string): Promise<any> {
    return this.request(`/render/jobs/${jobId}`);
  }

  /**
   * Ingest documents and extract brand canon
   */
  async ingest(request: IngestRequest): Promise<IngestResponse> {
    return this.request<IngestResponse>('/ingest', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Derive brand canon from project assets
   */
  async deriveCanon(request: CanonDeriveRequest): Promise<CanonDeriveResponse> {
    return this.request<CanonDeriveResponse>('/canon/derive', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get existing brand canon for a project
   */
  async getCanon(projectId: string): Promise<CanonDeriveResponse> {
    return this.request<CanonDeriveResponse>(`/canon/${projectId}`);
  }

  /**
   * Critique assets against brand canon
   */
  async critique(request: CritiqueRequest): Promise<CritiqueResponse> {
    return this.request<CritiqueResponse>('/critique', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Health check
   */
  async health(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/healthz');
  }

  /**
   * Get API metrics (if available)
   */
  async metrics(): Promise<string> {
    const response = await fetch(`${this.config.baseURL}/metrics`);
    return response.text();
  }
}

// Default client instance
export const apiClient = new NanoDesignerAPIClient({
  onError: (error) => {
    console.error('API Error:', {
      status: error.status,
      message: error.message,
      traceId: error.traceId,
      details: error.error.details,
    });
  },
  onRequest: (url, init) => {
    console.log('API Request:', {
      method: init.method || 'GET',
      url,
      hasAuth: !!(init.headers as any)?.Authorization,
    });
  },
  onResponse: (url, response) => {
    console.log('API Response:', {
      url,
      status: response.status,
      ok: response.ok,
    });
  },
});

// Legacy API object for backward compatibility
export const api = {
  render: (req: RenderRequest) => apiClient.render(req),
  renderAsync: (req: RenderRequest) => apiClient.renderAsync(req),
  jobStatus: (jobId: string) => apiClient.getJobStatus(jobId),
  ingest: (req: IngestRequest) => apiClient.ingest(req),
  canonDerive: (req: CanonDeriveRequest) => apiClient.deriveCanon(req),
};

// Types are already exported above where they're defined

export { NanoDesignerAPIClient, NanoDesignerAPIError };
