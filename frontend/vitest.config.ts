import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const root = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Mirror the tsconfig "@/*" -> "./*" path alias for tests.
    alias: { "@": root },
  },
  test: {
    environment: "jsdom",
    globals: false,
    include: ["**/*.test.ts", "**/*.test.tsx"],
  },
});
