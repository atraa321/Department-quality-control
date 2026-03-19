import { defineConfig } from "vite"
import legacy from "@vitejs/plugin-legacy"
import vue from "@vitejs/plugin-vue"

export default defineConfig({
  plugins: [
    vue(),
    legacy({
      targets: ["chrome >= 49", "edge >= 79", "firefox >= 60"],
      modernPolyfills: true,
      renderLegacyChunks: true,
    }),
  ],
  build: {
    cssTarget: "chrome49",
    rollupOptions: {
      output: {
        manualChunks: {
          "vue-vendor": ["vue", "vue-router", "pinia"],
          "element-plus": ["element-plus", "@element-plus/icons-vue"],
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
})
