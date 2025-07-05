/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // PWA configuration
  experimental: {
    webpackBuildWorker: true,
  },
  
  // PWA optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  
  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080',
  },
  
  // Performance optimization
  poweredByHeader: false,
  generateEtags: false,
  
  // Internationalization for Japanese
  i18n: {
    locales: ['ja', 'en'],
    defaultLocale: 'ja',
  },
  
  // Comprehensive Security headers
  async headers() {
    const securityHeaders = [
      // Prevent clickjacking attacks
      {
        key: 'X-Frame-Options',
        value: 'DENY',
      },
      // Prevent MIME type sniffing
      {
        key: 'X-Content-Type-Options',
        value: 'nosniff',
      },
      // Control referrer information
      {
        key: 'Referrer-Policy',
        value: 'strict-origin-when-cross-origin',
      },
      // Force HTTPS connections (HSTS)
      {
        key: 'Strict-Transport-Security',
        value: 'max-age=31536000; includeSubDomains; preload',
      },
      // Disable DNS prefetching for privacy
      {
        key: 'X-DNS-Prefetch-Control',
        value: 'off',
      },
      // Prevent IE from opening downloads directly
      {
        key: 'X-Download-Options',
        value: 'noopen',
      },
      // Restrict cross-domain policies
      {
        key: 'X-Permitted-Cross-Domain-Policies',
        value: 'none',
      },
      // Control browser features and APIs
      {
        key: 'Permissions-Policy',
        value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=(), fullscreen=(self), sync-xhr=()',
      },
      // Content Security Policy - Comprehensive XSS protection
      {
        key: 'Content-Security-Policy',
        value: [
          "default-src 'self'",
          "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
          "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data: https: blob:",
          "font-src 'self' data:",
          "connect-src 'self' https://www.sangiin.go.jp",
          "media-src 'self'",
          "object-src 'none'",
          "child-src 'none'",
          "worker-src 'self'",
          "frame-ancestors 'none'",
          "form-action 'self'",
          "base-uri 'self'",
          "manifest-src 'self'",
          "upgrade-insecure-requests"
        ].join('; '),
      },
      // Cross-Origin settings for enhanced security
      {
        key: 'Cross-Origin-Opener-Policy',
        value: 'same-origin',
      },
      {
        key: 'Cross-Origin-Resource-Policy',
        value: 'same-origin',
      },
      {
        key: 'Cross-Origin-Embedder-Policy',
        value: 'require-corp',
      },
    ];

    return [
      {
        source: '/(.*)',
        headers: securityHeaders,
      },
      // Additional headers for API routes
      {
        source: '/api/(.*)',
        headers: [
          ...securityHeaders,
          {
            key: 'Cache-Control',
            value: 'no-store, no-cache, must-revalidate, proxy-revalidate',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          },
          {
            key: 'Expires',
            value: '0',
          },
        ],
      },
      // Service Worker specific headers
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;