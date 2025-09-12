// This file configures the initialization of Sentry on the client side
import * as Sentry from '@sentry/nextjs';

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    
    // Adjust this value in production, or use tracesSampler for greater control
    tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,
    
    // Enable debug in development
    debug: process.env.NODE_ENV === 'development',
    
    // Enable session tracking
    autoSessionTracking: true,
    
    // Capture unhandled promise rejections  
    integrations: [
      Sentry.replayIntegration({
        // Mask all text content, exclude media
        maskAllText: true,
        blockAllMedia: false,
      }),
    ],
    
    // Set sample rates
    replaysSessionSampleRate: 0.1, // Sample 10% of sessions
    replaysOnErrorSampleRate: 1.0, // Sample 100% of sessions with errors
    
    // Environment
    environment: process.env.NODE_ENV,
    
    // Additional options
    beforeSend(event, hint) {
      // Filter out sensitive data
      if (event.request?.cookies) {
        delete event.request.cookies;
      }
      if (event.request?.headers) {
        delete event.request.headers['authorization'];
        delete event.request.headers['x-api-key'];
      }
      return event;
    },
  });
}