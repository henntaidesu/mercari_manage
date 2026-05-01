import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 9600,
    host: true,
    allowedHosts: ['nas.makurochan.com'],
    proxy: {
      '/api': {
        target: 'http://localhost:9601',
        changeOrigin: true
      },
      '/imges': {
        target: 'http://localhost:9601',
        changeOrigin: true
      }
    }
  }
})
