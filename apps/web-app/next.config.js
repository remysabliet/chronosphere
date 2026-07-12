/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Enable React 19 compiler
  reactCompiler: true,

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com',
        pathname: '/memosphere/**',
      },
    ],
    formats: ['image/avif', 'image/webp'],
  },

  // Environment variables validation
  env: {
    NEXT_PUBLIC_APP_URL:
      process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
  },

  // Headers for security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // Redirects
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/',
        permanent: true,
      },
      {
        // No standalone sign-up page exists — Cognito's Hosted UI handles
        // both sign-in and sign-up from the login flow.
        source: '/register',
        destination: '/login',
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
