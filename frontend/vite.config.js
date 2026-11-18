import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server runs on 5173 so it matches CORS_ORIGINS in backend/.env
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // fail loudly instead of silently moving to a port that CORS would block
  },
});
