import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { fileURLToPath, URL } from 'node:url'

// 使用 HTTPS 后浏览器才暴露 navigator.mediaDevices（实时摄像头）；http:// 内网域名会降级为文件选择框
export default defineConfig({
  plugins: [vue(), basicSsl()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    https: true,
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
