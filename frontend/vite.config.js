import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // During development, /api/* is forwarded to the FastAPI backend so the
    // browser never sees a cross-origin request. In production the front-end
    // is built to static files and served by whatever you like; point the
    // axios baseURL at the backend directly there.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
