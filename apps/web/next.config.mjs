import { withSentryConfig } from "@sentry/nextjs";

// Security headers configuration
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: process.env.NODE_ENV === 'production'
      // Tight production policy: no unsafe-eval/inline for scripts
      ? [
          "default-src 'self'",
          "img-src 'self' https: data:",
          "script-src 'self' https://*.clerk.accounts.dev https://*.clerk.com https://*.sentry.io",
          "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
          "font-src 'self' data: https://fonts.gstatic.com",
          "connect-src 'self' https://api.nanodesigner.com https://openrouter.ai https://*.sentry.io",
          "frame-ancestors 'none'",
        ].join('; ')
      : [
          "default-src 'self'",
          "img-src 'self' http: https: data:",
          "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://*.clerk.accounts.dev https://*.clerk.com",
          "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
          "font-src 'self' data: https://fonts.gstatic.com",
          "connect-src 'self' http://localhost:* ws://localhost:* https://*.sentry.io",
        ].join('; ')
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on'
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=31536000; includeSubDomains'
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()'
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin'
  }
];

/** @type {import('next').NextConfig} */
const baseConfig = {
  images: { 
    formats: ["image/avif", "image/webp"], 
    minimumCacheTTL: 60,
    domains: [
      'via.placeholder.com',
      'images.unsplash.com',
      'placehold.co',
      'picsum.photos',
      'localhost'
    ],
    dangerouslyAllowSVG: false,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;"
  },
  compiler: { 
    removeConsole: process.env.NODE_ENV === "production" 
  },
  productionBrowserSourceMaps: false,
  
  // Add security headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
  
  // Optimize bundle
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['@radix-ui', '@tanstack', 'lucide-react']
  }
};

export default withSentryConfig(baseConfig, { silent: true });
