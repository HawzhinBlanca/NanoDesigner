// Professional logging system with multiple transports and levels
import { toast } from 'sonner';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  FATAL = 4,
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  category: string;
  message: string;
  data?: any;
  userId?: string;
  sessionId?: string;
  requestId?: string;
  stack?: string;
  performance?: {
    duration?: number;
    memory?: number;
  };
}

// Log transport interface
interface LogTransport {
  log(entry: LogEntry): void | Promise<void>;
}

// Console transport
class ConsoleTransport implements LogTransport {
  log(entry: LogEntry): void {
    const style = this.getStyle(entry.level);
    const prefix = `[${entry.timestamp}] [${LogLevel[entry.level]}] [${entry.category}]`;
    
    console.log(
      `%c${prefix}%c ${entry.message}`,
      style,
      'color: inherit',
      entry.data || ''
    );
    
    if (entry.stack) {
      console.error(entry.stack);
    }
  }
  
  private getStyle(level: LogLevel): string {
    switch (level) {
      case LogLevel.DEBUG:
        return 'color: #888';
      case LogLevel.INFO:
        return 'color: #0066cc';
      case LogLevel.WARN:
        return 'color: #ff9800';
      case LogLevel.ERROR:
        return 'color: #f44336';
      case LogLevel.FATAL:
        return 'color: #fff; background: #d32f2f; padding: 2px 4px; border-radius: 2px';
      default:
        return '';
    }
  }
}

// Local storage transport for debugging
class LocalStorageTransport implements LogTransport {
  private readonly maxEntries = 1000;
  private readonly storageKey = 'app_logs';
  
  log(entry: LogEntry): void {
    try {
      const existing = this.getLogs();
      existing.push(entry);
      
      // Keep only recent logs
      if (existing.length > this.maxEntries) {
        existing.splice(0, existing.length - this.maxEntries);
      }
      
      localStorage.setItem(this.storageKey, JSON.stringify(existing));
    } catch (e) {
      // Storage might be full or disabled
      console.warn('Failed to store log entry:', e);
    }
  }
  
  getLogs(): LogEntry[] {
    try {
      const stored = localStorage.getItem(this.storageKey);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }
  
  clearLogs(): void {
    localStorage.removeItem(this.storageKey);
  }
}

// Remote logging transport (e.g., to Sentry, LogRocket, etc.)
class RemoteTransport implements LogTransport {
  private queue: LogEntry[] = [];
  private batchSize = 10;
  private flushInterval = 5000; // 5 seconds
  private timer?: NodeJS.Timeout;
  
  constructor() {
    // Start batch timer
    this.startBatchTimer();
  }
  
  async log(entry: LogEntry): Promise<void> {
    this.queue.push(entry);
    
    // Immediately flush for errors and above
    if (entry.level >= LogLevel.ERROR) {
      await this.flush();
    } else if (this.queue.length >= this.batchSize) {
      await this.flush();
    }
  }
  
  private startBatchTimer(): void {
    this.timer = setInterval(() => {
      if (this.queue.length > 0) {
        this.flush();
      }
    }, this.flushInterval);
  }
  
  private async flush(): Promise<void> {
    if (this.queue.length === 0) return;
    
    const batch = this.queue.splice(0, this.queue.length);
    
    try {
      // Send to your logging endpoint
      if (process.env.NEXT_PUBLIC_LOG_ENDPOINT) {
        await fetch(process.env.NEXT_PUBLIC_LOG_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ logs: batch }),
        });
      }
      
      // Also send errors to Sentry if available
      if (typeof window !== 'undefined' && (window as any).Sentry) {
        batch
          .filter(entry => entry.level >= LogLevel.ERROR)
          .forEach(entry => {
            (window as any).Sentry.captureMessage(entry.message, {
              level: entry.level === LogLevel.FATAL ? 'fatal' : 
                     entry.level === LogLevel.ERROR ? 'error' : 'warning',
              extra: entry.data,
              tags: {
                category: entry.category,
                userId: entry.userId,
                sessionId: entry.sessionId,
              },
            });
          });
      }
    } catch (error) {
      console.error('Failed to send logs:', error);
    }
  }
  
  destroy(): void {
    if (this.timer) {
      clearInterval(this.timer);
    }
    this.flush();
  }
}

// Performance monitoring
class PerformanceMonitor {
  private marks: Map<string, number> = new Map();
  
  start(label: string): void {
    this.marks.set(label, performance.now());
  }
  
  end(label: string): number | null {
    const start = this.marks.get(label);
    if (!start) return null;
    
    const duration = performance.now() - start;
    this.marks.delete(label);
    return duration;
  }
  
  measure(label: string, fn: () => any): any {
    this.start(label);
    const result = fn();
    const duration = this.end(label);
    
    if (duration && duration > 1000) {
      Logger.warn('Performance', `Slow operation: ${label} took ${duration.toFixed(2)}ms`);
    }
    
    return result;
  }
  
  async measureAsync(label: string, fn: () => Promise<any>): Promise<any> {
    this.start(label);
    try {
      const result = await fn();
      const duration = this.end(label);
      
      if (duration && duration > 1000) {
        Logger.warn('Performance', `Slow async operation: ${label} took ${duration.toFixed(2)}ms`);
      }
      
      return result;
    } catch (error) {
      this.end(label);
      throw error;
    }
  }
}

// Main logger class
class LoggerClass {
  private level: LogLevel = LogLevel.INFO;
  private transports: LogTransport[] = [];
  private sessionId: string;
  private userId?: string;
  private performance = new PerformanceMonitor();
  
  constructor() {
    this.sessionId = this.generateSessionId();
    
    // Initialize transports based on environment
    if (typeof window !== 'undefined') {
      this.transports.push(new ConsoleTransport());
      
      if (process.env.NODE_ENV === 'development') {
        this.transports.push(new LocalStorageTransport());
      }
      
      if (process.env.NEXT_PUBLIC_LOG_ENDPOINT) {
        this.transports.push(new RemoteTransport());
      }
    }
  }
  
  setLevel(level: LogLevel): void {
    this.level = level;
  }
  
  setUserId(userId: string): void {
    this.userId = userId;
  }
  
  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  
  private log(level: LogLevel, category: string, message: string, data?: any): void {
    if (level < this.level) return;
    
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      category,
      message,
      data,
      userId: this.userId,
      sessionId: this.sessionId,
    };
    
    // Add stack trace for errors
    if (level >= LogLevel.ERROR && data instanceof Error) {
      entry.stack = data.stack;
    }
    
    // Add performance metrics
    if (typeof window !== 'undefined' && window.performance) {
      entry.performance = {
        memory: (window.performance as any).memory?.usedJSHeapSize,
      };
    }
    
    // Send to all transports
    this.transports.forEach(transport => {
      try {
        transport.log(entry);
      } catch (error) {
        console.error('Transport failed:', error);
      }
    });
    
    // Show user-facing notifications for errors
    if (level === LogLevel.ERROR && process.env.NODE_ENV === 'production') {
      toast.error('An error occurred. Our team has been notified.');
    } else if (level === LogLevel.FATAL) {
      toast.error('A critical error occurred. Please refresh the page.');
    }
  }
  
  debug(category: string, message: string, data?: any): void {
    this.log(LogLevel.DEBUG, category, message, data);
  }
  
  info(category: string, message: string, data?: any): void {
    this.log(LogLevel.INFO, category, message, data);
  }
  
  warn(category: string, message: string, data?: any): void {
    this.log(LogLevel.WARN, category, message, data);
  }
  
  error(category: string, message: string, data?: any): void {
    this.log(LogLevel.ERROR, category, message, data);
  }
  
  fatal(category: string, message: string, data?: any): void {
    this.log(LogLevel.FATAL, category, message, data);
  }
  
  // Performance logging
  time(label: string): void {
    this.performance.start(label);
  }
  
  timeEnd(label: string): void {
    const duration = this.performance.end(label);
    if (duration) {
      this.debug('Performance', `${label}: ${duration.toFixed(2)}ms`);
    }
  }
  
  measure(label: string, fn: () => any): any {
    return this.performance.measure(label, fn);
  }
  
  async measureAsync(label: string, fn: () => Promise<any>): Promise<any> {
    return this.performance.measureAsync(label, fn);
  }
  
  // Group logging
  group(label: string): void {
    if (typeof console.group === 'function') {
      console.group(label);
    }
  }
  
  groupEnd(): void {
    if (typeof console.groupEnd === 'function') {
      console.groupEnd();
    }
  }
  
  // Table logging
  table(data: any): void {
    if (typeof console.table === 'function') {
      console.table(data);
    }
  }
  
  // Clear logs (development only)
  clear(): void {
    if (process.env.NODE_ENV === 'development') {
      console.clear();
      this.transports
        .filter(t => t instanceof LocalStorageTransport)
        .forEach((t: any) => t.clearLogs());
    }
  }
  
  // Get stored logs (development only)
  getLogs(): LogEntry[] {
    const localStorage = this.transports.find(t => t instanceof LocalStorageTransport) as LocalStorageTransport;
    return localStorage?.getLogs() || [];
  }
}

// Singleton instance
export const Logger = new LoggerClass();

// React hook for component logging
export function useLogger(category: string) {
  return {
    debug: (message: string, data?: any) => Logger.debug(category, message, data),
    info: (message: string, data?: any) => Logger.info(category, message, data),
    warn: (message: string, data?: any) => Logger.warn(category, message, data),
    error: (message: string, data?: any) => Logger.error(category, message, data),
    time: (label: string) => Logger.time(`${category}:${label}`),
    timeEnd: (label: string) => Logger.timeEnd(`${category}:${label}`),
  };
}

// Error boundary logger
export function logErrorBoundary(error: Error, errorInfo: any): void {
  Logger.error('ErrorBoundary', 'Component crashed', {
    error: error.message,
    stack: error.stack,
    componentStack: errorInfo.componentStack,
  });
}

// API request logger
export function logApiRequest(
  method: string,
  url: string,
  data?: any,
  response?: any,
  error?: any
): void {
  if (error) {
    Logger.error('API', `${method} ${url} failed`, {
      request: data,
      error: error.message || error,
      status: error.status,
    });
  } else {
    Logger.info('API', `${method} ${url}`, {
      request: data,
      response: response?.data,
      status: response?.status,
    });
  }
}

// Navigation logger
export function logNavigation(from: string, to: string): void {
  Logger.info('Navigation', `${from} → ${to}`);
}

// Feature usage logger
export function logFeatureUsage(feature: string, metadata?: any): void {
  Logger.info('Feature', `Used: ${feature}`, metadata);
}

// Performance metrics logger
export function logPerformanceMetrics(): void {
  if (typeof window === 'undefined' || !window.performance) return;
  
  const navigation = performance.getEntriesByType('navigation')[0] as any;
  const paint = performance.getEntriesByType('paint');
  
  if (navigation) {
    Logger.info('Performance', 'Page load metrics', {
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
      loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
      domInteractive: navigation.domInteractive,
      firstPaint: paint.find(p => p.name === 'first-paint')?.startTime,
      firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime,
    });
  }
}

// Auto-log unhandled errors
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    Logger.error('Global', 'Unhandled error', {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      error: event.error,
    });
  });
  
  window.addEventListener('unhandledrejection', (event) => {
    Logger.error('Global', 'Unhandled promise rejection', {
      reason: event.reason,
    });
  });
}

export default Logger;