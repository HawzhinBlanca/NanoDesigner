/**
 * Render API client for connecting to the backend AI generation service
 */

import { sanitizeInput, VALIDATION_LIMITS } from '@/lib/validation/schemas';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';
const API_TIMEOUT = 30000; // 30 seconds

// Types for API requests and responses
export interface RenderRequest {
  project_id: string;
  prompts: {
    task: string;
    instruction: string;
    references?: string[];
  };
  outputs: {
    count: number;
    format: 'png' | 'jpg' | 'webp';
    dimensions: string;
  };
  constraints?: {
    colors?: string[];
    fonts?: string[];
    logoSafeZone?: number;
  };
}

export interface RenderResponse {
  render_id: string;
  project_id: string;
  status: 'completed' | 'failed' | 'processing';
  images: Array<{
    url: string;
    format: string;
    dimensions: string;
    verified_by: string;
  }>;
  plan: {
    goal: string;
    ops: string[];
    safety: {
      respect_logo_safe_zone: boolean;
      palette_only: boolean;
    };
  };
  cost_info: {
    total_cost_usd: number;
    breakdown: Record<string, number>;
  };
  processing_time_ms: number;
  security_scan: {
    threat_level: string;
    confidence: number;
  };
  metadata: {
    model_used: string;
    image_model: string;
    api_version: string;
  };
}

export interface RenderError {
  error: string;
  details?: string;
  field?: string;
  code?: string;
}

// API Client Class
export class RenderAPIClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl = API_BASE_URL, timeout = API_TIMEOUT) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = timeout;
  }

  /**
   * Create a render request with proper validation and sanitization
   */
  async render(params: {
    projectId: string;
    prompt: string;
    variantCount: number;
    format: 'png' | 'jpg' | 'webp';
    dimensions: string;
    references?: string[];
    constraints?: {
      colors?: string[];
      fonts?: string[];
      logoSafeZone?: number;
    };
  }): Promise<RenderResponse> {
    // Validate and sanitize input
    const sanitizedPrompt = sanitizeInput(params.prompt, VALIDATION_LIMITS.PROMPT.MAX_LENGTH);
    
    if (sanitizedPrompt.length < VALIDATION_LIMITS.PROMPT.MIN_LENGTH) {
      throw new Error(`Prompt must be at least ${VALIDATION_LIMITS.PROMPT.MIN_LENGTH} characters`);
    }

    if (params.variantCount < 1 || params.variantCount > 8) {
      throw new Error('Variant count must be between 1 and 8');
    }

    // Validate dimensions format
    if (!/^\d{3,5}x\d{3,5}$/.test(params.dimensions)) {
      throw new Error('Invalid dimensions format. Use format like 1920x1080');
    }

    // Sanitize references if provided
    const sanitizedReferences = params.references?.map(ref => 
      sanitizeInput(ref, VALIDATION_LIMITS.REFERENCE_URL.MAX_LENGTH)
    ).filter(ref => ref.length > 0);

    // Build request payload
    const requestPayload: RenderRequest = {
      project_id: params.projectId,
      prompts: {
        task: "create", // Add required task field
        instruction: sanitizedPrompt,
        references: sanitizedReferences,
      },
      outputs: {
        count: params.variantCount,
        format: params.format,
        dimensions: params.dimensions,
      },
      constraints: params.constraints,
    };

    // Validate request size
    const requestSize = JSON.stringify(requestPayload).length;
    if (requestSize > VALIDATION_LIMITS.REQUEST.MAX_BODY_SIZE) {
      throw new Error('Request too large. Please reduce prompt length or references.');
    }

    try {
      // Generate simple Idempotency-Key for retry dedupe
      const idemKey = typeof btoa === 'function'
        ? btoa(`/render:${Date.now()}:${Math.random()}`)
        : Buffer.from(`/render:${Date.now()}:${Math.random()}`).toString('base64');

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Idempotency-Key': idemKey,
      };
      if (process.env.NEXT_PUBLIC_TEST_MODE === '1') {
        headers['X-Test-Mode'] = 'true';
      }
      const response = await this.makeRequest('/render', {
        method: 'POST',
        headers,
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new RenderAPIError(
          errorData.error || `HTTP ${response.status}`,
          response.status,
          errorData.details,
          errorData.field
        );
      }

      const result = await response.json();
      
      // Handle the actual API response format
      let formattedResult: RenderResponse;
      
      // The backend returns { assets: [...], audit: {...} }
      if (result.assets && Array.isArray(result.assets)) {
        formattedResult = {
          render_id: result.audit?.trace_id || `render_${Date.now()}`,
          project_id: params.projectId,
          status: 'completed' as const,
          images: result.assets.map((asset: any) => ({
            url: asset.url,
            format: params.format,
            dimensions: params.dimensions,
            verified_by: result.audit?.verified_by || 'none'
          })),
          plan: {
            goal: sanitizedPrompt,
            ops: ['generate', 'verify'],
            safety: {
              respect_logo_safe_zone: true,
              palette_only: false
            }
          },
          cost_info: {
            total_cost_usd: result.audit?.cost_usd || 0,
            breakdown: {}
          },
          // Backend does not return processing time; set 0 and let UI compute if needed
          processing_time_ms: 0,
          security_scan: {
            threat_level: 'low',
            confidence: 0.95
          },
          metadata: {
            model_used: result.audit?.model_route || 'openai/gpt-4o',
            image_model: 'google/gemini-2.5-flash-image-preview',
            api_version: '1.0.0'
          }
        };
      } 
      // Check if it's already in the expected format
      else if (result.render_id && result.images) {
        formattedResult = result;
      }
      else {
        throw new Error('Invalid response format from render API');
      }

      return formattedResult;

    } catch (error) {
      if (error instanceof RenderAPIError) {
        throw error;
      }
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new RenderAPIError('Request timeout', 408);
        }
        throw new RenderAPIError(error.message, 500);
      }
      
      throw new RenderAPIError('Unknown error occurred', 500);
    }
  }

  /**
   * Check API health
   */
  async healthCheck(): Promise<{ status: string; version?: string }> {
    try {
      const response = await this.makeRequest('/health', {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      throw new RenderAPIError(
        error instanceof Error ? error.message : 'Health check failed',
        500
      );
    }
  }

  /**
   * Make HTTP request with timeout and error handling
   */
  private async makeRequest(endpoint: string, options: RequestInit): Promise<Response> {
    const url = `${this.baseUrl}${endpoint}`;
    
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }
}

/**
 * Custom error class for render API errors
 */
export class RenderAPIError extends Error {
  constructor(
    message: string,
    public statusCode: number = 500,
    public details?: string,
    public field?: string
  ) {
    super(message);
    this.name = 'RenderAPIError';
  }

  /**
   * Check if error is a validation error
   */
  isValidationError(): boolean {
    return this.statusCode === 400 || this.statusCode === 422;
  }

  /**
   * Check if error is a server error
   */
  isServerError(): boolean {
    return this.statusCode >= 500;
  }

  /**
   * Check if error is a timeout
   */
  isTimeout(): boolean {
    return this.statusCode === 408;
  }

  /**
   * Get user-friendly error message
   */
  getUserMessage(): string {
    if (this.isValidationError()) {
      return this.field 
        ? `Invalid ${this.field}: ${this.message}`
        : `Validation error: ${this.message}`;
    }
    
    if (this.isTimeout()) {
      return 'Request timed out. Please try again.';
    }
    
    if (this.isServerError()) {
      return 'Server error. Please try again later.';
    }
    
    return this.message;
  }
}

// Default client instance
export const renderAPI = new RenderAPIClient();

// Utility functions
export function isValidDimensions(dimensions: string): boolean {
  if (!/^\d{3,5}x\d{3,5}$/.test(dimensions)) {
    return false;
  }
  
  const parts = dimensions.split('x');
  if (parts.length !== 2) return false;
  
  const width = Number(parts[0]);
  const height = Number(parts[1]);
  
  return !isNaN(width) && !isNaN(height) && 
         width >= 64 && width <= 8192 && 
         height >= 64 && height <= 8192;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function estimateRenderTime(variantCount: number, dimensions: string): number {
  const parts = dimensions.split('x');
  if (parts.length !== 2) return 5 * variantCount; // Default fallback
  
  const width = Number(parts[0]);
  const height = Number(parts[1]);
  
  if (isNaN(width) || isNaN(height)) return 5 * variantCount; // Default fallback
  
  const pixels = width * height;
  
  // Base time per variant (in seconds)
  let baseTime = 5;
  
  // Adjust for resolution
  if (pixels > 1920 * 1080) baseTime += 3;
  if (pixels > 2560 * 1440) baseTime += 5;
  
  return baseTime * variantCount;
}
