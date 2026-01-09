/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Block type colors
        block: {
          analysis: '#8b5cf6',    // Purple
          architecture: '#06b6d4', // Cyan
          stack: '#10b981',       // Emerald
          document: '#f59e0b',    // Amber
        },
        // Quality score colors
        quality: {
          excellent: '#22c55e',   // Green
          good: '#3b82f6',        // Blue
          warning: '#eab308',     // Yellow
          poor: '#ef4444',        // Red
        },
        // Status colors
        status: {
          pending: '#6b7280',
          processing: '#3b82f6',
          completed: '#22c55e',
          failed: '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
      },
      boxShadow: {
        'block': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'block-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'block-selected': '0 0 0 3px rgba(59, 130, 246, 0.5)',
      },
    },
  },
  plugins: [],
}
