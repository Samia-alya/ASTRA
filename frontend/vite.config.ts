import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// Backend port. Default 8000; override when that port is taken, e.g. in PowerShell:
//   $env:API_PORT = "8010"; npm run dev
const apiPort = process.env.API_PORT ?? '8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // Calls to /api/... are forwarded to the FastAPI backend.
    proxy: {
      '/api': {
        target: `http://localhost:${apiPort}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
