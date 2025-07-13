/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // PWA configuration
  experimental: {
    // webpackBuildWorker: true, // Disabled due to module resolution issues
  },
  
  // Development server configuration  
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://127.0.0.1:8000/api/:path*',
        },
      ];
    }
    return [];
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
    minimumCacheTTL: 60 * 60 * 24 * 7, // 7 days
    dangerouslyAllowSVG: false,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;"
  },
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  },
  
  // Performance optimization
  poweredByHeader: false,
  generateEtags: false,
  compress: true,
  
  // Bundle analyzer (run with ANALYZE=true npm run build)
  webpack: (config, { dev, isServer }) => {
    if (process.env.ANALYZE) {
      const withBundleAnalyzer = require('@next/bundle-analyzer')({
        enabled: true
      });
      return withBundleAnalyzer(config);
    }
    
    // Production optimizations
    if (!dev && !isServer) {
      config.optimization.splitChunks.cacheGroups = {
        ...config.optimization.splitChunks.cacheGroups,
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
          priority: 10,
        },
        heroicons: {
          test: /[\\/]node_modules[\\/]@heroicons[\\/]/,
          name: 'heroicons',
          chunks: 'all',
          priority: 20,
        }
      };
    }
    
    return config;
  },
  
  // Internationalization - disabled for initial release
  // i18n: {
  //   locales: ['ja', 'en'],
  //   defaultLocale: 'ja',
  // },
  
  // Security headers - Disabled for development troubleshooting
  async headers() {
    const isDevelopment = process.env.NODE_ENV === 'development';
    
    // Minimal headers for development
    if (isDevelopment) {
      return [
        {
          source: '/(.*)',
          headers: [
            {
              key: 'X-Frame-Options',
              value: 'SAMEORIGIN',
            },
          ],
        },
      ];
    }
    
    const securityHeaders = [
      // Prevent clickjacking attacks
      {
        key: 'X-Frame-Options',
        value: 'DENY',
      },
      // Control referrer information
      {
        key: 'Referrer-Policy',
        value: 'strict-origin-when-cross-origin',
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
        value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=(), fullscreen=(self), sync-xhr=()',
      },
      // Content Security Policy - Development-friendly with Google Fonts
      {
        key: 'Content-Security-Policy',
        value: [
          "default-src 'self'",
          "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
          "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
          "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com",
          "img-src 'self' data: https: blob:",
          "font-src 'self' data: https://fonts.googleapis.com https://fonts.gstatic.com",
          "connect-src 'self' http://localhost:8000 http://localhost:8080 https://www.sangiin.go.jp",
          "media-src 'self'",
          "object-src 'none'",
          "child-src 'none'",
          "worker-src 'self'",
          "frame-ancestors 'none'",
          "form-action 'self'",
          "base-uri 'self'",
          "manifest-src 'self'",
          "upgrade-insecure-requests"
        ].filter(Boolean).join('; '),
      },
      // Force HTTPS connections (HSTS) - Production only
      {
        key: 'Strict-Transport-Security',
        value: 'max-age=31536000; includeSubDomains; preload',
      },
      // Prevent MIME type sniffing - Production only
      {
        key: 'X-Content-Type-Options',
        value: 'nosniff',
      },
      // Cross-Origin settings for enhanced security - Production only
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