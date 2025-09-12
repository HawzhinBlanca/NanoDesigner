/**
 * Client-side rate limiting and throttling utilities
 */

interface RateLimitConfig {
  maxRequests: number;
  windowMs: number;
  identifier?: string;
}

interface ThrottleConfig {
  delay: number;
  maxWait?: number;
  leading?: boolean;
  trailing?: boolean;
}

interface DebounceConfig {
  delay: number;
  maxWait?: number;
}

// Token bucket implementation for rate limiting
class TokenBucket {
  private tokens: number;
  private lastRefill: number;
  private readonly maxTokens: number;
  private readonly refillRate: number;
  
  constructor(maxTokens: number, refillRatePerSecond: number) {
    this.maxTokens = maxTokens;
    this.tokens = maxTokens;
    this.refillRate = refillRatePerSecond;
    this.lastRefill = Date.now();
  }
  
  private refill(): void {
    const now = Date.now();
    const timePassed = (now - this.lastRefill) / 1000;
    const tokensToAdd = timePassed * this.refillRate;
    
    this.tokens = Math.min(this.maxTokens, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }
  
  tryConsume(tokens: number = 1): boolean {
    this.refill();
    
    if (this.tokens >= tokens) {
      this.tokens -= tokens;
      return true;
    }
    
    return false;
  }
  
  getAvailableTokens(): number {
    this.refill();
    return Math.floor(this.tokens);
  }
  
  getTimeUntilNextToken(): number {
    if (this.tokens >= 1) return 0;
    return ((1 - this.tokens) / this.refillRate) * 1000;
  }
}

// Rate limiter class
export class RateLimiter {
  private buckets: Map<string, TokenBucket> = new Map();
  private requestQueue: Map<string, Array<() => void>> = new Map();
  
  constructor(private defaultConfig: RateLimitConfig) {}
  
  private getBucket(identifier: string): TokenBucket {
    if (!this.buckets.has(identifier)) {
      const refillRate = this.defaultConfig.maxRequests / (this.defaultConfig.windowMs / 1000);
      this.buckets.set(identifier, new TokenBucket(this.defaultConfig.maxRequests, refillRate));
    }
    return this.buckets.get(identifier)!;
  }
  
  async acquire(identifier: string = 'default'): Promise<void> {
    const bucket = this.getBucket(identifier);
    
    if (bucket.tryConsume()) {
      return Promise.resolve();
    }
    
    // Queue the request
    return new Promise((resolve) => {
      if (!this.requestQueue.has(identifier)) {
        this.requestQueue.set(identifier, []);
      }
      
      this.requestQueue.get(identifier)!.push(resolve);
      
      // Process queue after delay
      const delay = bucket.getTimeUntilNextToken();
      setTimeout(() => this.processQueue(identifier), delay);
    });
  }
  
  private processQueue(identifier: string): void {
    const queue = this.requestQueue.get(identifier);
    if (!queue || queue.length === 0) return;
    
    const bucket = this.getBucket(identifier);
    const resolve = queue.shift();
    
    if (resolve && bucket.tryConsume()) {
      resolve();
    }
    
    // Continue processing if there are more requests
    if (queue.length > 0) {
      const delay = bucket.getTimeUntilNextToken();
      setTimeout(() => this.processQueue(identifier), delay);
    }
  }
  
  isRateLimited(identifier: string = 'default'): boolean {
    const bucket = this.getBucket(identifier);
    return bucket.getAvailableTokens() < 1;
  }
  
  getRemainingRequests(identifier: string = 'default'): number {
    const bucket = this.getBucket(identifier);
    return bucket.getAvailableTokens();
  }
  
  reset(identifier: string = 'default'): void {
    this.buckets.delete(identifier);
    this.requestQueue.delete(identifier);
  }
}

// Throttle function
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  config: ThrottleConfig | number
): T & { cancel: () => void; flush: () => void } {
  const options: ThrottleConfig = typeof config === 'number' 
    ? { delay: config } 
    : config;
  
  let timeoutId: NodeJS.Timeout | null = null;
  let lastCallTime: number | null = null;
  let lastInvokeTime = 0;
  let lastArgs: any[] | null = null;
  let lastThis: any = null;
  let result: any;
  
  const invoke = (time: number) => {
    const args = lastArgs!;
    const thisArg = lastThis;
    
    lastArgs = lastThis = null;
    lastInvokeTime = time;
    result = func.apply(thisArg, args);
    return result;
  };
  
  const shouldInvoke = (time: number): boolean => {
    const timeSinceLastCall = lastCallTime ? time - lastCallTime : 0;
    const timeSinceLastInvoke = time - lastInvokeTime;
    
    return !lastCallTime ||
      timeSinceLastCall >= options.delay ||
      timeSinceLastCall < 0 ||
      (options.maxWait !== undefined && timeSinceLastInvoke >= options.maxWait);
  };
  
  const trailingEdge = (time: number) => {
    timeoutId = null;
    
    if (options.trailing !== false && lastArgs) {
      return invoke(time);
    }
    
    lastArgs = lastThis = null;
    return result;
  };
  
  const timerExpired = () => {
    const time = Date.now();
    
    if (shouldInvoke(time)) {
      return trailingEdge(time);
    }
    
    const timeSinceLastCall = lastCallTime ? time - lastCallTime : 0;
    const timeSinceLastInvoke = time - lastInvokeTime;
    const timeWaiting = options.delay - timeSinceLastCall;
    const remaining = options.maxWait !== undefined
      ? Math.min(timeWaiting, options.maxWait - timeSinceLastInvoke)
      : timeWaiting;
    
    timeoutId = setTimeout(timerExpired, remaining);
  };
  
  const throttled = function (this: any, ...args: any[]) {
    const time = Date.now();
    const isInvoking = shouldInvoke(time);
    
    lastArgs = args;
    lastThis = this;
    lastCallTime = time;
    
    if (isInvoking) {
      if (!timeoutId) {
        lastInvokeTime = Date.now();
        if (options.leading !== false) {
          result = func.apply(this, args);
        }
        timeoutId = setTimeout(timerExpired, options.delay);
      }
    } else if (!timeoutId) {
      timeoutId = setTimeout(timerExpired, options.delay);
    }
    
    return result;
  } as T;
  
  (throttled as any).cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    lastInvokeTime = 0;
    lastArgs = lastCallTime = lastThis = null;
  };
  
  (throttled as any).flush = () => {
    if (timeoutId) {
      trailingEdge(Date.now());
    }
  };
  
  return throttled as T & { cancel: () => void; flush: () => void };
}

// Debounce function
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  config: DebounceConfig | number
): T & { cancel: () => void; flush: () => void } {
  const options: DebounceConfig = typeof config === 'number' 
    ? { delay: config } 
    : config;
  
  let timeoutId: NodeJS.Timeout | null = null;
  let lastArgs: any[] | null = null;
  let lastThis: any = null;
  let lastCallTime: number | null = null;
  let result: any;
  let maxTimeoutId: NodeJS.Timeout | null = null;
  
  const invokeFunc = () => {
    const args = lastArgs!;
    const thisArg = lastThis;
    
    lastArgs = lastThis = null;
    result = func.apply(thisArg, args);
    return result;
  };
  
  const startTimer = (wait: number) => {
    return setTimeout(() => {
      timeoutId = null;
      
      if (maxTimeoutId) {
        clearTimeout(maxTimeoutId);
        maxTimeoutId = null;
      }
      
      if (lastArgs) {
        invokeFunc();
      }
    }, wait);
  };
  
  const debounced = function (this: any, ...args: any[]) {
    lastArgs = args;
    lastThis = this;
    lastCallTime = Date.now();
    
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    timeoutId = startTimer(options.delay);
    
    // Set max wait timer if configured
    if (options.maxWait !== undefined && !maxTimeoutId) {
      maxTimeoutId = setTimeout(() => {
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        maxTimeoutId = null;
        
        if (lastArgs) {
          invokeFunc();
        }
      }, options.maxWait);
    }
    
    return result;
  } as T;
  
  (debounced as any).cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    if (maxTimeoutId) {
      clearTimeout(maxTimeoutId);
      maxTimeoutId = null;
    }
    lastArgs = lastThis = lastCallTime = null;
  };
  
  (debounced as any).flush = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    if (maxTimeoutId) {
      clearTimeout(maxTimeoutId);
      maxTimeoutId = null;
    }
    
    if (lastArgs) {
      invokeFunc();
    }
  };
  
  return debounced as T & { cancel: () => void; flush: () => void };
}

// React hook for rate limiting
export function useRateLimiter(config: RateLimitConfig) {
  const limiterRef = React.useRef<RateLimiter>();
  
  if (!limiterRef.current) {
    limiterRef.current = new RateLimiter(config);
  }
  
  const execute = React.useCallback(async <T,>(
    fn: () => Promise<T>,
    identifier?: string
  ): Promise<T> => {
    await limiterRef.current!.acquire(identifier);
    return fn();
  }, []);
  
  const isRateLimited = React.useCallback((identifier?: string): boolean => {
    return limiterRef.current!.isRateLimited(identifier);
  }, []);
  
  const getRemainingRequests = React.useCallback((identifier?: string): number => {
    return limiterRef.current!.getRemainingRequests(identifier);
  }, []);
  
  const reset = React.useCallback((identifier?: string): void => {
    limiterRef.current!.reset(identifier);
  }, []);
  
  return {
    execute,
    isRateLimited,
    getRemainingRequests,
    reset
  };
}

// React hook for throttling
export function useThrottle<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const throttledRef = React.useRef<T & { cancel: () => void }>();
  
  React.useEffect(() => {
    throttledRef.current = throttle(callback, delay);
    
    return () => {
      throttledRef.current?.cancel();
    };
  }, [callback, delay]);
  
  return React.useCallback((...args: Parameters<T>) => {
    return throttledRef.current?.(...args);
  }, []) as T;
}

// React hook for debouncing
export function useDebounce<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const debouncedRef = React.useRef<T & { cancel: () => void }>();
  
  React.useEffect(() => {
    debouncedRef.current = debounce(callback, delay);
    
    return () => {
      debouncedRef.current?.cancel();
    };
  }, [callback, delay]);
  
  return React.useCallback((...args: Parameters<T>) => {
    return debouncedRef.current?.(...args);
  }, []) as T;
}

import React from 'react';