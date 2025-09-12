/**
 * Enhanced API client with retry logic, exponential backoff, and circuit breaker
 */

interface RetryConfig {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
  retryableStatusCodes?: number[];
  timeout?: number;
}

interface CircuitBreakerConfig {
  failureThreshold?: number;
  resetTimeout?: number;
  halfOpenRequests?: number;
}

class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime: number | null = null;
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  private successCount = 0;
  
  constructor(private config: CircuitBreakerConfig = {}) {
    this.config.failureThreshold = config.failureThreshold ?? 5;
    this.config.resetTimeout = config.resetTimeout ?? 60000; // 1 minute
    this.config.halfOpenRequests = config.halfOpenRequests ?? 3;
  }
  
  canMakeRequest(): boolean {
    if (this.state === 'closed') return true;
    
    if (this.state === 'open') {
      const now = Date.now();
      if (this.lastFailureTime && (now - this.lastFailureTime) > this.config.resetTimeout!) {
        this.state = 'half-open';
        this.successCount = 0;
        return true;
      }
      return false;
    }
    
    // half-open state
    return true;
  }
  
  recordSuccess(): void {
    if (this.state === 'half-open') {
      this.successCount++;
      if (this.successCount >= this.config.halfOpenRequests!) {
        this.state = 'closed';
        this.failureCount = 0;
      }
    } else if (this.state === 'closed') {
      this.failureCount = Math.max(0, this.failureCount - 1);
    }
  }
  
  recordFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    
    if (this.failureCount >= this.config.failureThreshold!) {
      this.state = 'open';
    }
    
    if (this.state === 'half-open') {
      this.state = 'open';
    }
  }
  
  getState(): string {
    return this.state;
  }
}

export class RetryClient {
  private circuitBreaker: CircuitBreaker;
  private defaultConfig: RetryConfig = {
    maxRetries: 3,
    initialDelay: 1000,
    maxDelay: 10000,
    backoffMultiplier: 2,
    retryableStatusCodes: [408, 429, 500, 502, 503, 504],
    timeout: 30000,
  };
  
  constructor(
    private baseURL: string,
    config?: RetryConfig,
    circuitBreakerConfig?: CircuitBreakerConfig
  ) {
    this.defaultConfig = { ...this.defaultConfig, ...config };
    this.circuitBreaker = new CircuitBreaker(circuitBreakerConfig);
  }
  
  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  private calculateDelay(attempt: number): number {
    const delay = Math.min(
      this.defaultConfig.initialDelay! * Math.pow(this.defaultConfig.backoffMultiplier!, attempt),
      this.defaultConfig.maxDelay!
    );
    // Add jitter to prevent thundering herd
    return delay + Math.random() * 1000;
  }
  
  private isRetryable(error: any): boolean {
    // Network errors are retryable
    if (!error.response) return true;
    
    // Check if status code is retryable
    return this.defaultConfig.retryableStatusCodes!.includes(error.response.status);
  }
  
  async request<T>(
    path: string,
    options: RequestInit = {},
    retryConfig?: RetryConfig
  ): Promise<T> {
    const config = { ...this.defaultConfig, ...retryConfig };
    
    // Check circuit breaker
    if (!this.circuitBreaker.canMakeRequest()) {
      throw new Error(`Circuit breaker is open. Service temporarily unavailable.`);
    }
    
    let lastError: any;
    
    for (let attempt = 0; attempt <= config.maxRetries!; attempt++) {
      try {
        // Add timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), config.timeout!);
        
        const response = await fetch(`${this.baseURL}${path}`, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          const error: any = new Error(`HTTP ${response.status}: ${response.statusText}`);
          error.response = response;
          error.status = response.status;
          throw error;
        }
        
        const data = await response.json();
        
        // Record success
        this.circuitBreaker.recordSuccess();
        
        return data;
      } catch (error: any) {
        lastError = error;
        
        // Record failure
        this.circuitBreaker.recordFailure();
        
        // Don't retry if it's the last attempt
        if (attempt === config.maxRetries!) {
          break;
        }
        
        // Don't retry if not retryable
        if (!this.isRetryable(error)) {
          break;
        }
        
        // Don't retry if circuit breaker is open
        if (!this.circuitBreaker.canMakeRequest()) {
          break;
        }
        
        // Calculate delay and wait
        const delay = this.calculateDelay(attempt);
        console.log(`Retry attempt ${attempt + 1}/${config.maxRetries} after ${Math.round(delay)}ms`);
        await this.sleep(delay);
      }
    }
    
    // Enhance error with retry information
    if (lastError) {
      lastError.retriesExhausted = true;
      lastError.circuitBreakerState = this.circuitBreaker.getState();
    }
    
    throw lastError;
  }
  
  async get<T>(path: string, config?: RetryConfig): Promise<T> {
    return this.request<T>(path, { method: 'GET' }, config);
  }
  
  async post<T>(path: string, data: any, config?: RetryConfig): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      config
    );
  }
  
  async put<T>(path: string, data: any, config?: RetryConfig): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      },
      config
    );
  }
  
  async delete<T>(path: string, config?: RetryConfig): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' }, config);
  }
  
  getCircuitBreakerState(): string {
    return this.circuitBreaker.getState();
  }
}

// Create singleton instance
const apiClient = new RetryClient(
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  {
    maxRetries: 3,
    initialDelay: 1000,
    maxDelay: 10000,
  },
  {
    failureThreshold: 5,
    resetTimeout: 60000,
  }
);

export default apiClient;