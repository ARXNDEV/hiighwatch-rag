import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Suppress warnings in production for cleaner logs
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
