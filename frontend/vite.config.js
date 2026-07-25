import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5000'

  return {
    plugins: [react()],
    server: {
      open: true,
      // Escuta em todas as interfaces para permitir testar de outro
      // dispositivo da mesma rede (o app deriva a API do host acessado)
      host: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
          timeout: 60000,
          configure: (proxy) => {
            proxy.on('error', (err, req) => {
              console.log('Erro no proxy:', err.message, req?.url)
            })
            proxy.on('proxyReq', (proxyReq, req) => {
              console.log('Enviando requisição:', req.method, req.url)
            })
            proxy.on('proxyRes', (proxyRes, req) => {
              console.log('Resposta recebida:', proxyRes.statusCode, req.url)
            })
          }
        }
      }
    }
  }
})