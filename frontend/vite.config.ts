import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@components': resolve(__dirname, './src/components'),
      '@pages': resolve(__dirname, './src/pages'),
      '@hooks': resolve(__dirname, './src/hooks'),
      '@stores': resolve(__dirname, './src/stores'),
      '@services': resolve(__dirname, './src/services'),
      '@types': resolve(__dirname, './src/types'),
      '@utils': resolve(__dirname, './src/utils'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Code splitting strategy for optimal loading
        manualChunks: {
          // Core React libraries
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // State management
          'vendor-state': ['zustand', '@tanstack/react-query'],
          // Visualization libraries (lazy loaded separately)
          'vendor-viz': ['reactflow'],
          // UI libraries
          'vendor-ui': ['@headlessui/react', 'lucide-react', 'framer-motion'],
          // Markdown rendering
          'vendor-md': ['react-markdown', 'remark-gfm'],
          // Diagram rendering (lazy loaded)
          'vendor-diagram': ['mermaid'],
        },
      },
    },
    // Chunk size warnings
    chunkSizeWarningLimit: 500,
  },
  // Development server configuration
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
