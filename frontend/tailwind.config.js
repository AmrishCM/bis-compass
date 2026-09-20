/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      fontFamily: {
        sans: ['Atkinson Hyperlegible', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        primary: '#0F172A',
        secondary: '#334155',
        accent: '#0369A1',
        background: '#F8FAFC',
        // Optional: additional neutral colors
        'neutral-50': '#F8FAFC',
        'neutral-100': '#F1F5F9',
        'neutral-200': '#E2E8F0',
        'neutral-300': '#CBD5E1',
        'neutral-400': '#94A3B8',
        'neutral-500': '#64748B',
        'neutral-600': '#475569',
        'neutral-700': '#334155',
        'neutral-800': '#1E293B',
        'neutral-900': '#0F172A',
      }
    },
  },
  plugins: [],
}