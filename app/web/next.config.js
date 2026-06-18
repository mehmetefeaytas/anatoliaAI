/** @type {import('next').NextConfig} */
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // /api/* isteklerini FastAPI backend'e yönlendir (offline, anahtarsız)
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};

module.exports = nextConfig;
