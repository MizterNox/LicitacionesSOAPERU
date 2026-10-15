/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Superficies oscuras (azul pizarra profundo) — Sidebar, tarjetas IA
        ink: {
          50: '#EEF2F9',
          100: '#D8DFEE',
          200: '#B4C0D8',
          300: '#8494B3',
          400: '#5B6B8C',
          500: '#3E4E6E',
          600: '#2A3A5C',
          700: '#1E2A45',
          800: '#141C30',
          850: '#0E1526',
          900: '#0A0F1E',
          950: '#060913',
        },
        // Acento primario: púrpura tecnológico
        brand: {
          50: '#F5F3FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED',
          700: '#6D28D9',
          800: '#5B21B6',
          900: '#4C1D95',
          950: '#2E1065',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      boxShadow: {
        soft: '0 1px 2px 0 rgb(15 23 42 / 0.05), 0 8px 24px -12px rgb(15 23 42 / 0.12)',
        card: '0 1px 2px 0 rgb(15 23 42 / 0.04), 0 12px 32px -16px rgb(15 23 42 / 0.18)',
        'glow-brand': '0 0 0 1px rgb(139 92 246 / 0.2), 0 8px 32px -8px rgb(124 58 237 / 0.45)',
        'panel-l': '-24px 0 48px -32px rgb(2 6 23 / 0.35)',
      },
    },
  },
  plugins: [],
}
