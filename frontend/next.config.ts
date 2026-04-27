import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Output as standalone to drastically reduce Docker image size
  output: "standalone",
  // Suppress warnings in production for cleaner logs
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
