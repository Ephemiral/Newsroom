import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingIncludes: {
    '/event/[id]': ['../data/events/**/*'],
    '/': ['../data/events/**/*'],
  },
};

export default nextConfig;
