import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: { '/api': process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8020' },
  },
  build: {
    rollupOptions: {
      output: { manualChunks: (id) => (id.includes('recharts') || id.includes('d3-') ? 'charts' : id.includes('highlight.js') ? 'highlight' : undefined) },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: false,
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
