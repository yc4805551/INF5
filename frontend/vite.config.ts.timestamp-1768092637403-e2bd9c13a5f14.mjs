// vite.config.ts
import { defineConfig, loadEnv } from "file:///C:/Users/Administrator/Documents/project2/INFV5/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///C:/Users/Administrator/Documents/project2/INFV5/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
import { ServerResponse } from "http";
var vite_config_default = defineConfig(({ mode }) => {
  const env = loadEnv(mode, "../config", "");
  const apiTarget = env.VITE_API_TARGET || "http://localhost:5179";
  console.log(`[vite-config] Using API Target: ${apiTarget}`);
  return {
    base: "/INF3/",
    envDir: "../config",
    plugins: [react()],
    server: {
      host: true,
      // Listen on all addresses (0.0.0.0)
      port: 5178,
      strictPort: true,
      allowedHosts: ["www.yc01.top"],
      // Allow external domain access
      cors: true,
      // Explicitly enable CORS
      // hmr: {
      //   clientPort: 5178, 
      // },
      watch: {
        // Ignore changes to tsconfig.json to prevent unwanted server restarts
        // if an IDE or another tool modifies it.
        ignored: ["**/tsconfig.json"]
      },
      proxy: {
        // Proxy for the local backend, which handles both knowledge base
        // and AI generation requests during development.
        "/proxy-api": {
          target: apiTarget,
          // Proxy target for the local backend service.
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/proxy-api/, "/api"),
          // Add logging to help debug proxy issues.
          configure: (proxy, options) => {
            proxy.on("proxyReq", (proxyReq, req, res) => {
              console.log(`[vite-proxy] Sending request: ${req.method} ${req.url} -> ${options.target}${proxyReq.path}`);
            });
            proxy.on("proxyRes", (proxyRes, req, res) => {
              console.log(`[vite-proxy] Received response: ${proxyRes.statusCode} ${req.url}`);
            });
            proxy.on("error", (err, req, res) => {
              console.error("[vite-proxy] Error:", err);
              if (res instanceof ServerResponse && !res.headersSent) {
                res.writeHead(502, { "Content-Type": "application/json" });
                res.end(JSON.stringify({ message: "Proxy Error", error: err.message }));
              }
            });
          }
        },
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          configure: (proxy, options) => {
            proxy.on("proxyReq", (proxyReq, req, res) => {
              console.log(`[vite-proxy] Sending request: ${req.method} ${req.url} -> ${options.target}${proxyReq.path}`);
            });
          }
        },
        "/static": {
          target: apiTarget,
          changeOrigin: true
        }
      }
    }
  };
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxVc2Vyc1xcXFxBZG1pbmlzdHJhdG9yXFxcXERvY3VtZW50c1xcXFxwcm9qZWN0MlxcXFxJTkZWNVxcXFxmcm9udGVuZFwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiQzpcXFxcVXNlcnNcXFxcQWRtaW5pc3RyYXRvclxcXFxEb2N1bWVudHNcXFxccHJvamVjdDJcXFxcSU5GVjVcXFxcZnJvbnRlbmRcXFxcdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0M6L1VzZXJzL0FkbWluaXN0cmF0b3IvRG9jdW1lbnRzL3Byb2plY3QyL0lORlY1L2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnLCBsb2FkRW52IH0gZnJvbSAndml0ZSdcclxuaW1wb3J0IHJlYWN0IGZyb20gJ0B2aXRlanMvcGx1Z2luLXJlYWN0J1xyXG5pbXBvcnQgeyBTZXJ2ZXJSZXNwb25zZSB9IGZyb20gJ2h0dHAnO1xyXG5cclxuLy8gaHR0cHM6Ly92aXRlanMuZGV2L2NvbmZpZy9cclxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKCh7IG1vZGUgfSkgPT4ge1xyXG4gIC8vIExvYWQgZW52IGZpbGUgYmFzZWQgb24gYG1vZGVgIGluIHRoZSBjdXJyZW50IHdvcmtpbmcgZGlyZWN0b3J5LlxyXG4gIC8vIFNldCB0aGUgdGhpcmQgcGFyYW1ldGVyIHRvICcnIHRvIGxvYWQgYWxsIGVudiByZWdhcmRsZXNzIG9mIHRoZSBgVklURV9gIHByZWZpeC5cclxuICBjb25zdCBlbnYgPSBsb2FkRW52KG1vZGUsICcuLi9jb25maWcnLCAnJylcclxuICBjb25zdCBhcGlUYXJnZXQgPSBlbnYuVklURV9BUElfVEFSR0VUIHx8ICdodHRwOi8vbG9jYWxob3N0OjUxNzknXHJcblxyXG4gIGNvbnNvbGUubG9nKGBbdml0ZS1jb25maWddIFVzaW5nIEFQSSBUYXJnZXQ6ICR7YXBpVGFyZ2V0fWApXHJcblxyXG4gIHJldHVybiB7XHJcbiAgICBiYXNlOiAnL0lORjMvJyxcclxuICAgIGVudkRpcjogJy4uL2NvbmZpZycsXHJcbiAgICBwbHVnaW5zOiBbcmVhY3QoKV0sXHJcbiAgICBzZXJ2ZXI6IHtcclxuICAgICAgaG9zdDogdHJ1ZSwgLy8gTGlzdGVuIG9uIGFsbCBhZGRyZXNzZXMgKDAuMC4wLjApXHJcbiAgICAgIHBvcnQ6IDUxNzgsXHJcbiAgICAgIHN0cmljdFBvcnQ6IHRydWUsXHJcbiAgICAgIGFsbG93ZWRIb3N0czogWyd3d3cueWMwMS50b3AnXSwgLy8gQWxsb3cgZXh0ZXJuYWwgZG9tYWluIGFjY2Vzc1xyXG4gICAgICBjb3JzOiB0cnVlLCAvLyBFeHBsaWNpdGx5IGVuYWJsZSBDT1JTXHJcbiAgICAgIC8vIGhtcjoge1xyXG4gICAgICAvLyAgIGNsaWVudFBvcnQ6IDUxNzgsIFxyXG4gICAgICAvLyB9LFxyXG4gICAgICB3YXRjaDoge1xyXG4gICAgICAgIC8vIElnbm9yZSBjaGFuZ2VzIHRvIHRzY29uZmlnLmpzb24gdG8gcHJldmVudCB1bndhbnRlZCBzZXJ2ZXIgcmVzdGFydHNcclxuICAgICAgICAvLyBpZiBhbiBJREUgb3IgYW5vdGhlciB0b29sIG1vZGlmaWVzIGl0LlxyXG4gICAgICAgIGlnbm9yZWQ6IFsnKiovdHNjb25maWcuanNvbiddLFxyXG4gICAgICB9LFxyXG4gICAgICBwcm94eToge1xyXG4gICAgICAgIC8vIFByb3h5IGZvciB0aGUgbG9jYWwgYmFja2VuZCwgd2hpY2ggaGFuZGxlcyBib3RoIGtub3dsZWRnZSBiYXNlXHJcbiAgICAgICAgLy8gYW5kIEFJIGdlbmVyYXRpb24gcmVxdWVzdHMgZHVyaW5nIGRldmVsb3BtZW50LlxyXG4gICAgICAgICcvcHJveHktYXBpJzoge1xyXG4gICAgICAgICAgdGFyZ2V0OiBhcGlUYXJnZXQsIC8vIFByb3h5IHRhcmdldCBmb3IgdGhlIGxvY2FsIGJhY2tlbmQgc2VydmljZS5cclxuICAgICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgICAgIHJld3JpdGU6IChwYXRoKSA9PiBwYXRoLnJlcGxhY2UoL15cXC9wcm94eS1hcGkvLCAnL2FwaScpLFxyXG4gICAgICAgICAgLy8gQWRkIGxvZ2dpbmcgdG8gaGVscCBkZWJ1ZyBwcm94eSBpc3N1ZXMuXHJcbiAgICAgICAgICBjb25maWd1cmU6IChwcm94eSwgb3B0aW9ucykgPT4ge1xyXG4gICAgICAgICAgICBwcm94eS5vbigncHJveHlSZXEnLCAocHJveHlSZXEsIHJlcSwgcmVzKSA9PiB7XHJcbiAgICAgICAgICAgICAgY29uc29sZS5sb2coYFt2aXRlLXByb3h5XSBTZW5kaW5nIHJlcXVlc3Q6ICR7cmVxLm1ldGhvZH0gJHtyZXEudXJsfSAtPiAke29wdGlvbnMudGFyZ2V0fSR7cHJveHlSZXEucGF0aH1gKTtcclxuICAgICAgICAgICAgfSk7XHJcbiAgICAgICAgICAgIHByb3h5Lm9uKCdwcm94eVJlcycsIChwcm94eVJlcywgcmVxLCByZXMpID0+IHtcclxuICAgICAgICAgICAgICBjb25zb2xlLmxvZyhgW3ZpdGUtcHJveHldIFJlY2VpdmVkIHJlc3BvbnNlOiAke3Byb3h5UmVzLnN0YXR1c0NvZGV9ICR7cmVxLnVybH1gKTtcclxuICAgICAgICAgICAgfSk7XHJcbiAgICAgICAgICAgIHByb3h5Lm9uKCdlcnJvcicsIChlcnIsIHJlcSwgcmVzKSA9PiB7XHJcbiAgICAgICAgICAgICAgY29uc29sZS5lcnJvcignW3ZpdGUtcHJveHldIEVycm9yOicsIGVycik7XHJcbiAgICAgICAgICAgICAgLy8gRklYOiBVc2UgdGhlIGltcG9ydGVkIFNlcnZlclJlc3BvbnNlIGZvciBhIHByb3BlciB0eXBlIGd1YXJkIHRvIHJlc29sdmUgVHlwZVNjcmlwdCBlcnJvcnMgb24gYHJlc2Agd2hpY2ggY291bGQgYmUgYSBTb2NrZXQuXHJcbiAgICAgICAgICAgICAgaWYgKHJlcyBpbnN0YW5jZW9mIFNlcnZlclJlc3BvbnNlICYmICFyZXMuaGVhZGVyc1NlbnQpIHtcclxuICAgICAgICAgICAgICAgIHJlcy53cml0ZUhlYWQoNTAyLCB7ICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbicgfSk7XHJcbiAgICAgICAgICAgICAgICByZXMuZW5kKEpTT04uc3RyaW5naWZ5KHsgbWVzc2FnZTogJ1Byb3h5IEVycm9yJywgZXJyb3I6IGVyci5tZXNzYWdlIH0pKTtcclxuICAgICAgICAgICAgICB9XHJcbiAgICAgICAgICAgIH0pO1xyXG4gICAgICAgICAgfVxyXG4gICAgICAgIH0sXHJcbiAgICAgICAgJy9hcGknOiB7XHJcbiAgICAgICAgICB0YXJnZXQ6IGFwaVRhcmdldCxcclxuICAgICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgICAgIGNvbmZpZ3VyZTogKHByb3h5LCBvcHRpb25zKSA9PiB7XHJcbiAgICAgICAgICAgIHByb3h5Lm9uKCdwcm94eVJlcScsIChwcm94eVJlcSwgcmVxLCByZXMpID0+IHtcclxuICAgICAgICAgICAgICBjb25zb2xlLmxvZyhgW3ZpdGUtcHJveHldIFNlbmRpbmcgcmVxdWVzdDogJHtyZXEubWV0aG9kfSAke3JlcS51cmx9IC0+ICR7b3B0aW9ucy50YXJnZXR9JHtwcm94eVJlcS5wYXRofWApO1xyXG4gICAgICAgICAgICB9KTtcclxuICAgICAgICAgIH1cclxuICAgICAgICB9LFxyXG4gICAgICAgICcvc3RhdGljJzoge1xyXG4gICAgICAgICAgdGFyZ2V0OiBhcGlUYXJnZXQsXHJcbiAgICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXHJcbiAgICAgICAgfVxyXG4gICAgICB9XHJcbiAgICB9XHJcbiAgfVxyXG59KSJdLAogICJtYXBwaW5ncyI6ICI7QUFBd1csU0FBUyxjQUFjLGVBQWU7QUFDOVksT0FBTyxXQUFXO0FBQ2xCLFNBQVMsc0JBQXNCO0FBRy9CLElBQU8sc0JBQVEsYUFBYSxDQUFDLEVBQUUsS0FBSyxNQUFNO0FBR3hDLFFBQU0sTUFBTSxRQUFRLE1BQU0sYUFBYSxFQUFFO0FBQ3pDLFFBQU0sWUFBWSxJQUFJLG1CQUFtQjtBQUV6QyxVQUFRLElBQUksbUNBQW1DLFNBQVMsRUFBRTtBQUUxRCxTQUFPO0FBQUEsSUFDTCxNQUFNO0FBQUEsSUFDTixRQUFRO0FBQUEsSUFDUixTQUFTLENBQUMsTUFBTSxDQUFDO0FBQUEsSUFDakIsUUFBUTtBQUFBLE1BQ04sTUFBTTtBQUFBO0FBQUEsTUFDTixNQUFNO0FBQUEsTUFDTixZQUFZO0FBQUEsTUFDWixjQUFjLENBQUMsY0FBYztBQUFBO0FBQUEsTUFDN0IsTUFBTTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsTUFJTixPQUFPO0FBQUE7QUFBQTtBQUFBLFFBR0wsU0FBUyxDQUFDLGtCQUFrQjtBQUFBLE1BQzlCO0FBQUEsTUFDQSxPQUFPO0FBQUE7QUFBQTtBQUFBLFFBR0wsY0FBYztBQUFBLFVBQ1osUUFBUTtBQUFBO0FBQUEsVUFDUixjQUFjO0FBQUEsVUFDZCxTQUFTLENBQUMsU0FBUyxLQUFLLFFBQVEsZ0JBQWdCLE1BQU07QUFBQTtBQUFBLFVBRXRELFdBQVcsQ0FBQyxPQUFPLFlBQVk7QUFDN0Isa0JBQU0sR0FBRyxZQUFZLENBQUMsVUFBVSxLQUFLLFFBQVE7QUFDM0Msc0JBQVEsSUFBSSxpQ0FBaUMsSUFBSSxNQUFNLElBQUksSUFBSSxHQUFHLE9BQU8sUUFBUSxNQUFNLEdBQUcsU0FBUyxJQUFJLEVBQUU7QUFBQSxZQUMzRyxDQUFDO0FBQ0Qsa0JBQU0sR0FBRyxZQUFZLENBQUMsVUFBVSxLQUFLLFFBQVE7QUFDM0Msc0JBQVEsSUFBSSxtQ0FBbUMsU0FBUyxVQUFVLElBQUksSUFBSSxHQUFHLEVBQUU7QUFBQSxZQUNqRixDQUFDO0FBQ0Qsa0JBQU0sR0FBRyxTQUFTLENBQUMsS0FBSyxLQUFLLFFBQVE7QUFDbkMsc0JBQVEsTUFBTSx1QkFBdUIsR0FBRztBQUV4QyxrQkFBSSxlQUFlLGtCQUFrQixDQUFDLElBQUksYUFBYTtBQUNyRCxvQkFBSSxVQUFVLEtBQUssRUFBRSxnQkFBZ0IsbUJBQW1CLENBQUM7QUFDekQsb0JBQUksSUFBSSxLQUFLLFVBQVUsRUFBRSxTQUFTLGVBQWUsT0FBTyxJQUFJLFFBQVEsQ0FBQyxDQUFDO0FBQUEsY0FDeEU7QUFBQSxZQUNGLENBQUM7QUFBQSxVQUNIO0FBQUEsUUFDRjtBQUFBLFFBQ0EsUUFBUTtBQUFBLFVBQ04sUUFBUTtBQUFBLFVBQ1IsY0FBYztBQUFBLFVBQ2QsV0FBVyxDQUFDLE9BQU8sWUFBWTtBQUM3QixrQkFBTSxHQUFHLFlBQVksQ0FBQyxVQUFVLEtBQUssUUFBUTtBQUMzQyxzQkFBUSxJQUFJLGlDQUFpQyxJQUFJLE1BQU0sSUFBSSxJQUFJLEdBQUcsT0FBTyxRQUFRLE1BQU0sR0FBRyxTQUFTLElBQUksRUFBRTtBQUFBLFlBQzNHLENBQUM7QUFBQSxVQUNIO0FBQUEsUUFDRjtBQUFBLFFBQ0EsV0FBVztBQUFBLFVBQ1QsUUFBUTtBQUFBLFVBQ1IsY0FBYztBQUFBLFFBQ2hCO0FBQUEsTUFDRjtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
