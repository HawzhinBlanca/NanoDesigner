'use client';

import { useEffect } from 'react';

/**
 * Service Worker Registration Component
 * Safely registers the service worker without using dangerouslySetInnerHTML
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    // Only register in production and if supported
    if (
      typeof window !== 'undefined' &&
      'serviceWorker' in navigator &&
      process.env.NODE_ENV === 'production'
    ) {
      // Register service worker after window load for better performance
      const registerSW = async () => {
        try {
          const registration = await navigator.serviceWorker.register('/sw.js', {
            scope: '/',
            updateViaCache: 'none', // Always check for updates
          });

          // Log registration success
          console.log('Service Worker registered successfully:', registration.scope);

          // Check for updates periodically (every hour)
          setInterval(() => {
            registration.update().catch(console.error);
          }, 60 * 60 * 1000);

          // Handle updates
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'activated') {
                  // New service worker activated
                  if (navigator.serviceWorker.controller) {
                    // Notify user about update
                    console.log('New service worker activated. Please refresh for updates.');
                    // You could show a toast notification here
                  }
                }
              });
            }
          });

          // Handle controller change (when SW takes control)
          navigator.serviceWorker.addEventListener('controllerchange', () => {
            // Service worker has taken control
            console.log('Service Worker has taken control of the page');
          });

        } catch (error) {
          console.error('Service Worker registration failed:', error);
          
          // Report to error tracking in production
          if (process.env.NEXT_PUBLIC_ERROR_TRACKING_ENDPOINT) {
            fetch(process.env.NEXT_PUBLIC_ERROR_TRACKING_ENDPOINT, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                error: 'Service Worker registration failed',
                message: error instanceof Error ? error.message : String(error),
                timestamp: new Date().toISOString(),
                url: window.location.href,
              }),
            }).catch(() => {
              // Silently fail error reporting
            });
          }
        }
      };

      // Wait for window load to avoid impacting initial page load
      if (document.readyState === 'complete') {
        registerSW();
      } else {
        window.addEventListener('load', registerSW, { once: true });
      }
    }

    // Cleanup function
    return () => {
      // No cleanup needed for service worker registration
    };
  }, []);

  // This component doesn't render anything
  return null;
}

/**
 * Hook to interact with the service worker
 */
export function useServiceWorker() {
  useEffect(() => {
    if (
      typeof window !== 'undefined' &&
      'serviceWorker' in navigator
    ) {
      // Listen for messages from service worker
      navigator.serviceWorker.addEventListener('message', (event) => {
        console.log('Message from Service Worker:', event.data);
        
        // Handle different message types
        if (event.data.type === 'CACHE_UPDATED') {
          console.log('Cache has been updated');
        } else if (event.data.type === 'OFFLINE_READY') {
          console.log('App is ready for offline use');
        }
      });
    }
  }, []);

  // Function to send message to service worker
  const sendMessage = (message: any) => {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage(message);
    }
  };

  // Function to check if we're online
  const isOnline = () => {
    return navigator.onLine;
  };

  // Function to clear all caches
  const clearCaches = async () => {
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
      );
      console.log('All caches cleared');
    }
  };

  // Function to check for updates
  const checkForUpdates = async () => {
    if (navigator.serviceWorker.controller) {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration) {
        await registration.update();
        console.log('Checking for service worker updates');
      }
    }
  };

  return {
    sendMessage,
    isOnline,
    clearCaches,
    checkForUpdates,
  };
}