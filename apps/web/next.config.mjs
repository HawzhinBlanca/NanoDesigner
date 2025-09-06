import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const withBundleAnalyzer = (config) => {
  if (process.env.ANALYZE === 'true') {
    // Next 15 built-in analyzer flag (simulate via env guard)
    config.experimental = config.experimental || {};
    config.experimental.optimizePackageImports = ["lucide-react", "@radix-ui/react-*"];
  }
  return config;
};

let baseConfig = withBundleAnalyzer({
  experimental: {
    optimizePackageImports: ["lucide-react", "@radix-ui/react-*"]
  },
  images: { formats: ["image/avif", "image/webp"], minimumCacheTTL: 60 },
  compiler: { removeConsole: process.env.NODE_ENV === "production" },
  productionBrowserSourceMaps: false
});

const nextConfig = withSentryConfig(baseConfig, { silent: true });

export default nextConfig;

