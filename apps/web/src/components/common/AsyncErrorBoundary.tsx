'use client';

import React, { Component, ReactNode, Suspense } from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  resetKeys?: Array<string | number>;
  resetOnPropsChange?: boolean;
  isolate?: boolean;
  showDetails?: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  errorCount: number;
}

/**
 * Production-grade error boundary for async components
 * Handles both sync and async errors with proper recovery
 */
export class AsyncErrorBoundary extends Component<Props, State> {
  private resetTimeoutId: number | null = null;
  private previousResetKeys: Array<string | number> = [];

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    };
    
    if (props.resetKeys) {
      this.previousResetKeys = props.resetKeys;
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const { onError } = this.props;
    
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error caught by boundary:', error);
      console.error('Error info:', errorInfo);
    }

    // Call custom error handler if provided
    if (onError) {
      onError(error, errorInfo);
    }

    // Log to error reporting service in production
    if (process.env.NODE_ENV === 'production') {
      this.logErrorToService(error, errorInfo);
    }

    // Update error count for rate limiting
    this.setState(prevState => ({
      errorInfo,
      errorCount: prevState.errorCount + 1,
    }));

    // Auto-reset after 10 seconds if error count is low
    if (this.state.errorCount < 3) {
      this.scheduleReset(10000);
    }
  }

  componentDidUpdate(prevProps: Props) {
    const { resetKeys, resetOnPropsChange } = this.props;
    const { hasError } = this.state;
    
    // Reset on prop changes if enabled
    if (hasError && prevProps.children !== this.props.children && resetOnPropsChange) {
      this.resetErrorBoundary();
    }
    
    // Reset if resetKeys changed
    if (resetKeys && this.previousResetKeys) {
      const hasResetKeyChanged = resetKeys.some(
        (key, idx) => key !== this.previousResetKeys[idx]
      );
      
      if (hasResetKeyChanged) {
        this.resetErrorBoundary();
        this.previousResetKeys = resetKeys;
      }
    }
  }

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      window.clearTimeout(this.resetTimeoutId);
    }
  }

  scheduleReset = (delay: number) => {
    if (this.resetTimeoutId) {
      window.clearTimeout(this.resetTimeoutId);
    }
    
    this.resetTimeoutId = window.setTimeout(() => {
      this.resetErrorBoundary();
    }, delay);
  };

  resetErrorBoundary = () => {
    if (this.resetTimeoutId) {
      window.clearTimeout(this.resetTimeoutId);
      this.resetTimeoutId = null;
    }
    
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  logErrorToService = (error: Error, errorInfo: React.ErrorInfo) => {
    // In production, send to error tracking service
    // Example: Sentry, LogRocket, etc.
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    };
    
    // Send to your error tracking endpoint
    if (process.env.NEXT_PUBLIC_ERROR_TRACKING_ENDPOINT) {
      fetch(process.env.NEXT_PUBLIC_ERROR_TRACKING_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorData),
      }).catch(() => {
        // Silently fail - don't want error reporting to cause more errors
      });
    }
  };

  render() {
    const { hasError, error, errorInfo, errorCount } = this.state;
    const { children, fallback, isolate, showDetails } = this.props;

    if (hasError && error) {
      // Custom fallback if provided
      if (fallback) {
        return <>{fallback}</>;
      }

      // Rate limit check - if too many errors, show permanent error
      if (errorCount >= 5) {
        return (
          <Card className="max-w-2xl mx-auto my-8 border-destructive">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                Too Many Errors
              </CardTitle>
              <CardDescription>
                This component is experiencing repeated errors. Please refresh the page or contact support.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button onClick={() => window.location.reload()} variant="default">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh Page
                </Button>
                <Button onClick={() => window.location.href = '/'} variant="outline">
                  <Home className="h-4 w-4 mr-2" />
                  Go Home
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      }

      // Default error UI
      return (
        <Card className={`${isolate ? 'max-w-2xl' : 'w-full'} mx-auto my-8 border-destructive`}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Something went wrong
            </CardTitle>
            <CardDescription>
              {error.message || 'An unexpected error occurred'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Error details in development */}
            {showDetails !== false && process.env.NODE_ENV === 'development' && (
              <details className="space-y-2">
                <summary className="cursor-pointer text-sm font-medium">
                  Error Details (Development Only)
                </summary>
                <div className="mt-2 space-y-2">
                  <div className="p-3 bg-muted rounded-md">
                    <p className="text-xs font-mono break-all">{error.stack}</p>
                  </div>
                  {errorInfo && (
                    <div className="p-3 bg-muted rounded-md">
                      <p className="text-xs text-muted-foreground mb-1">Component Stack:</p>
                      <pre className="text-xs font-mono break-all whitespace-pre-wrap">
                        {errorInfo.componentStack}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            )}
            
            {/* Recovery actions */}
            <div className="flex gap-2">
              <Button onClick={this.resetErrorBoundary} variant="default">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button onClick={() => window.history.back()} variant="outline">
                Go Back
              </Button>
            </div>
            
            {/* Auto-retry indicator */}
            {errorCount < 3 && (
              <p className="text-sm text-muted-foreground">
                Will automatically retry in a few seconds...
              </p>
            )}
          </CardContent>
        </Card>
      );
    }

    // No error, render children
    return <>{children}</>;
  }
}

/**
 * Hook to use with async components
 */
export function withAsyncErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <AsyncErrorBoundary {...errorBoundaryProps}>
      <Suspense fallback={<div>Loading...</div>}>
        <Component {...props} />
      </Suspense>
    </AsyncErrorBoundary>
  );
  
  WrappedComponent.displayName = `withAsyncErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}