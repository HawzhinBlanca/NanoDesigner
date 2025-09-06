import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

export function middleware(req: NextRequest) {
  const res = NextResponse.next();
  // Strict CSP with env-based allowances
  const posthog = process.env.NEXT_PUBLIC_POSTHOG_HOST || "";
  const sentry = process.env.NEXT_PUBLIC_SENTRY_HOST || "";
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";
  const wsBase = apiBase.replace(/^http/, "ws");
  const connectSrc = ["'self'", "https:", "http:"]
    .concat(posthog ? [posthog] : [])
    .concat(sentry ? [sentry] : [])
    .concat(apiBase ? [apiBase] : [])
    .concat(wsBase ? [wsBase] : []);
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    `connect-src ${connectSrc.join(' ')}`,
    "font-src 'self' data:",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'"
  ].join("; ");
  res.headers.set("Content-Security-Policy", csp);
  res.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  res.headers.set("X-Content-Type-Options", "nosniff");
  res.headers.set("X-Frame-Options", "DENY");
  res.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  return res;
}

export const config = {
  matcher: ['/((?!.*\\..*|_next).*)', '/', '/(api|trpc)(.*)'],
};

