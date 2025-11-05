import { defineConfig, loadEnv, ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env variables from .env files
  // The third parameter '' makes it load all variables, not just those prefixed with VITE_
  const env = loadEnv(mode, '.', '');

  // Dynamically build the proxy configuration from environment variables
  const proxyConfig: Record<string, ProxyOptions> = {};

  // --- OpenAI Proxy ---
  const openaiProxyPath = env.OPENAI_PROXY_PATH || '/proxy/openai';
  if (env.OPENAI_TARGET_URL) {
    proxyConfig[openaiProxyPath] = {
      target: env.OPENAI_TARGET_URL,
      changeOrigin: true,
      rewrite: (path) => path.replace(new RegExp(`^${openaiProxyPath}`), ''),
    };
  }

  // --- DeepSeek Proxy ---
  const deepseekProxyPath = env.DEEPSEEK_PROXY_PATH || '/proxy/deepseek';
  if (env.DEEPSEEK_TARGET_URL) {
    proxyConfig[deepseekProxyPath] = {
      target: env.DEEPSEEK_TARGET_URL,
      changeOrigin: true,
      rewrite: (path) => path.replace(new RegExp(`^${deepseekProxyPath}`), ''),
    };
  }

  // --- Ali Proxy ---
  const aliProxyPath = env.ALI_PROXY_PATH || '/proxy/ali';
  if (env.ALI_TARGET_URL) {
    proxyConfig[aliProxyPath] = {
      target: env.ALI_TARGET_URL,
      changeOrigin: true,
      rewrite: (path) => path.replace(new RegExp(`^${aliProxyPath}`), ''),
    };
  }

  return {
    // Set the base path for deployment to the specific GitHub repository.
    base: '/INF3/',
    plugins: [react()],
    server: {
      watch: {
        // Ignore changes to tsconfig.json to prevent unwanted server restarts
        // if an IDE or another tool modifies it.
        ignored: ['**/tsconfig.json'],
      },
      proxy: {
        // Proxy for the local knowledge base backend
        '/api': {
          target: 'http://127.0.0.1:5000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        // Dynamically add proxies for external AI services
        ...proxyConfig,
      }
    },
    // This makes the environment variables available in your client-side code
    // on the `process.env` object.
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
      'process.env.API_KEY': JSON.stringify(env.VITE_GEMINI_API_KEY),
      'process.env.OPENAI_API_KEY': JSON.stringify(env.VITE_OPENAI_API_KEY || env.OPENAI_API_KEY),
      'process.env.DEEPSEEK_API_KEY': JSON.stringify(env.VITE_DEEPSEEK_API_KEY || env.DEEPSEEK_API_KEY),
      'process.env.ALI_API_KEY': JSON.stringify(env.VITE_ALI_API_KEY || env.ALI_API_KEY),
      'process.env.OPENAI_ENDPOINT': JSON.stringify(env.VITE_OPENAI_ENDPOINT || `${openaiProxyPath}/v1/chat/completions`),
      'process.env.OPENAI_MODEL': JSON.stringify(env.VITE_OPENAI_MODEL || env.OPENAI_MODEL || 'gpt-5-ca'),
      'process.env.DEEPSEEK_ENDPOINT': JSON.stringify(env.VITE_DEEPSEEK_ENDPOINT || `${deepseekProxyPath}/v1/chat/completions`),
      'process.env.DEEPSEEK_MODEL': JSON.stringify(env.VITE_DEEPSEEK_MODEL || env.DEEPSEEK_MODEL || 'deepseek-chat'),
      'process.env.ALI_ENDPOINT': JSON.stringify(env.VITE_ALI_ENDPOINT || `${aliProxyPath}/v1/chat/completions`),
      'process.env.ALI_MODEL': JSON.stringify(env.VITE_ALI_MODEL || env.ALI_MODEL || 'doubao-seed-1-6-thinking-250715'),
    }
  }
})