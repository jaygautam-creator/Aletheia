import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle for lean, reproducible container images.
  output: "standalone",
  // Pin the workspace root to this directory so an unrelated parent lockfile
  // cannot be mis-inferred as the project root.
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
