import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

// Simplified middleware without crypto module for edge runtime compatibility
export function middleware(req: NextRequest) {
  const res = NextResponse.next();
  
  // Apply security headers
  const posthog = process.env.NEXT_PUBLIC_POSTHOG_HOST || "";
  const sentry = process.env.NEXT_PUBLIC_SENTRY_HOST || "";
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";
  const wsBase = apiBase.replace(/^http/, "ws");
  const connectSrc = ["'self'", "https:", "http:", "https://*.clerk.accounts.dev", "https://*.clerk.com"]
    .concat(posthog ? [posthog] : [])
    .concat(sentry ? [sentry] : [])
    .concat(apiBase ? [apiBase] : [])
    .concat(wsBase ? [wsBase] : []);
  
  const isProd = process.env.NODE_ENV === 'production';
  
  const csp = [
    "default-src 'self'",
    // Allow unsafe-inline for development
    isProd
      ? "script-src 'self' 'unsafe-inline' https://*.clerk.accounts.dev https://*.clerk.com"
      : "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.clerk.accounts.dev https://*.clerk.com",
    "style-src 'self' 'unsafe-inline' https://*.clerk.accounts.dev https://*.clerk.com",
    "img-src 'self' data: blob: https://*.clerk.accounts.dev https://*.clerk.com",
    `connect-src ${connectSrc.join(' ')}`,
    "font-src 'self' data: https://*.clerk.accounts.dev https://*.clerk.com",
    "frame-src 'self' https://*.clerk.accounts.dev https://*.clerk.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'"
  ].join("; ");
  
  res.headers.set("Content-Security-Policy", csp);
  res.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  res.headers.set("X-Content-Type-Options", "nosniff");
  res.headers.set("X-Frame-Options", "DENY");
  res.headers.set("X-XSS-Protection", "1; mode=block");
  res.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()");
  
  // Additional security headers for production
  if (isProd) {
    res.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload");
    res.headers.set("X-DNS-Prefetch-Control", "off");
    res.headers.set("X-Download-Options", "noopen");
    res.headers.set("X-Permitted-Cross-Domain-Policies", "none");
  }
  
  // Add warning header if Clerk is not configured
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    res.headers.set("X-Auth-Status", "disabled");
  }
  
  return res;
}

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};