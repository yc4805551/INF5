import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { ServerResponse } from 'http';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, '../config', '')
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:5179'

  console.log(`[vite-config] Using API Target: ${apiTarget}`)

  return {
    base: '/INF3/',
    envDir: '../config',
    plugins: [react()],
    server: {
      server: {
        host: true, // Listen on all addresses (0.0.0.0)
        port: 5178,
        strictPort: true,
        cors: true, // Explicitly enable CORS
        // hmr: {
        //   clientPort: 5178, 
        // },
        watch: {
          // Ignore changes to tsconfig.json to prevent unwanted server restarts
          // if an IDE or another tool modifies it.
          ignored: ['**/tsconfig.json'],
        },
        proxy: {
          // Proxy for the local backend, which handles both knowledge base
          // and AI generation requests during development.
          '/proxy-api': {
            target: apiTarget, // Proxy target for the local backend service.
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/proxy-api/, '/api'),
            // Add logging to help debug proxy issues.
            configure: (proxy, options) => {
              proxy.on('proxyReq', (proxyReq, req, res) => {
                console.log(`[vite-proxy] Sending request: ${req.method} ${req.url} -> ${options.target}${proxyReq.path}`);
              });
              proxy.on('proxyRes', (proxyRes, req, res) => {
                console.log(`[vite-proxy] Received response: ${proxyRes.statusCode} ${req.url}`);
              });
              proxy.on('error', (err, req, res) => {
                console.error('[vite-proxy] Error:', err);
                // FIX: Use the imported ServerResponse for a proper type guard to resolve TypeScript errors on `res` which could be a Socket.
                if (res instanceof ServerResponse && !res.headersSent) {
                  res.writeHead(502, { 'Content-Type': 'application/json' });
                  res.end(JSON.stringify({ message: 'Proxy Error', error: err.message }));
                }
              });
            }
          },
        }
      },
    }
  })