"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import React from "react";
import { PostHogProvider } from "@posthog/react";
import posthog from "posthog-js";
import { ClerkProvider, useAuth } from "@clerk/nextjs";
import { setAuthTokenProvider } from "@/lib/api";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 2, retryDelay: (a) => Math.min(1000 * 2 ** a, 5000) } }
});

function Fallback() {
  return <div className="p-4 text-sm text-red-600">Something went wrong. Please retry.</div>;
}

// Inner component that has access to Clerk's useAuth
function AuthTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();
  
  React.useEffect(() => {
    setAuthTokenProvider(async () => {
      try {
        // Get JWT token from Clerk
        const token = await getToken();
        return token;
      } catch (error) {
        console.error('Failed to get auth token:', error);
        return null;
      }
    });
  }, [getToken]);

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  
  // If no Clerk key is provided, render without authentication (but don't show demo banner)
  if (!clerkPublishableKey) {
    return (
      <ErrorBoundary fallback={<Fallback />}>
        <PostHogProvider client={posthog}>
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        </PostHogProvider>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary fallback={<Fallback />}>
      <ClerkProvider publishableKey={clerkPublishableKey}>
        <AuthTokenProvider>
          <PostHogProvider client={posthog}>
            <QueryClientProvider client={queryClient}>
              {children}
            </QueryClientProvider>
          </PostHogProvider>
        </AuthTokenProvider>
      </ClerkProvider>
    </ErrorBoundary>
  );
}

