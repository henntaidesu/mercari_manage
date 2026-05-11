import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { fileURLToPath, URL } from 'node:url'

const websideRoot = fileURLToPath(new URL('.', import.meta.url))
const DEV_PORT = 9600

// 默认 HTTPS：自签名证书。纯 HTTP：MERCARI_DEV_HTTP=1。
// 远程/域名访问（非本机浏览器）：在 webside/.env.development 中设置
// MERCARI_DEV_PUBLIC_HOST=nas.makurochan.com（或与地址栏一致的主机名/IP），
// 以便 HMR WebSocket 使用 ws/wss 连到可解析的主机，而不是 0.0.0.0。
export default defineConfig(({ mode }) => {
  const fileEnv = loadEnv(mode, websideRoot, 'MERCARI_')
  const env = { ...fileEnv, ...process.env }
  const devHttpOnly = env.MERCARI_DEV_HTTP === '1'
  const publicHost = (env.MERCARI_DEV_PUBLIC_HOST || '').trim() || undefined
  const useHttps = !devHttpOnly

  const hmr = publicHost
    ? {
        protocol: useHttps ? 'wss' : 'ws',
        host: publicHost,
        port: DEV_PORT,
        clientPort: DEV_PORT
      }
    : { protocol: useHttps ? 'wss' : 'ws' }

  return {
    plugins: devHttpOnly ? [vue()] : [vue(), basicSsl()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: '0.0.0.0',
      port: DEV_PORT,
      strictPort: true,
      https: useHttps,
      allowedHosts: true,
      hmr,
      ...(publicHost
        ? { origin: `${useHttps ? 'https' : 'http'}://${publicHost}:${DEV_PORT}` }
        : {}),
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:9601',
          changeOrigin: true
        },
        '/imges': {
          target: 'http://127.0.0.1:9601',
          changeOrigin: true
        }
      }
    }
  }
})
