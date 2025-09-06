"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import React from "react";
import { PostHogProvider } from "@posthog/react";
import posthog from "posthog-js";
import { setAuthTokenProvider } from "@/lib/api";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 2, retryDelay: (a) => Math.min(1000 * 2 ** a, 5000) } }
});

function Fallback() {
  return <div className="p-4 text-sm text-red-600">Something went wrong. Please retry.</div>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  // Mock auth token provider for demo mode
  React.useEffect(() => {
    setAuthTokenProvider(async () => "demo-token");
  }, []);

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

