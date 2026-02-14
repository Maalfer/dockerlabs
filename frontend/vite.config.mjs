import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/auth': 'http://127.0.0.1:5000',
      '/bunkerlabs': 'http://127.0.0.1:5000',
      '/upload-profile-photo': 'http://127.0.0.1:5000',
      '/reclamar-maquina': 'http://127.0.0.1:5000',
      '/request_username_change': 'http://127.0.0.1:5000'
    }
  }
})

