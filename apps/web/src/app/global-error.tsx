'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';

/**
 * Global error boundary for the entire app
 * This catches errors that escape component-level boundaries
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error to error reporting service
    if (process.env.NODE_ENV === 'production') {
      const errorData = {
        message: error.message,
        stack: error.stack,
        digest: error.digest,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
      };
      
      // Send to error tracking endpoint
      if (process.env.NEXT_PUBLIC_ERROR_TRACKING_ENDPOINT) {
        fetch(process.env.NEXT_PUBLIC_ERROR_TRACKING_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(errorData),
        }).catch(() => {
          // Silently fail
        });
      }
    } else {
      console.error('Global error:', error);
    }
  }, [error]);

  return (
    <html>
      <body>
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
          <div className="max-w-md w-full space-y-8">
            <div className="text-center">
              <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
              <h1 className="mt-4 text-3xl font-bold text-foreground">
                Application Error
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {error.message || 'An unexpected error has occurred'}
              </p>
              {error.digest && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Error ID: {error.digest}
                </p>
              )}
            </div>
            
            {process.env.NODE_ENV === 'development' && error.stack && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium text-muted-foreground">
                  Stack Trace (Development Only)
                </summary>
                <pre className="mt-2 text-xs bg-muted p-3 rounded overflow-auto max-h-64">
                  {error.stack}
                </pre>
              </details>
            )}
            
            <div className="mt-8 space-y-3">
              <button
                onClick={reset}
                className="w-full flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </button>
              
              <button
                onClick={() => window.location.href = '/'}
                className="w-full flex justify-center items-center px-4 py-2 border border-input text-sm font-medium rounded-md text-foreground bg-background hover:bg-accent focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                <Home className="h-4 w-4 mr-2" />
                Go to Home
              </button>
            </div>
            
            <p className="mt-4 text-center text-xs text-muted-foreground">
              If this problem persists, please contact support with Error ID: {error.digest || 'N/A'}
            </p>
          </div>
        </div>
      </body>
    </html>
  );
}