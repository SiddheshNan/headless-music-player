/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,svelte}"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Custom dark theme colors
        'player': {
          'bg': '#0a0a0f',
          'card': '#16161f',
          'hover': '#1f1f2e',
          'accent': '#8b5cf6',
          'accent-hover': '#a78bfa',
          'text': '#e2e8f0',
          'text-muted': '#94a3b8',
          'border': '#2d2d3d'
        }
      },
      animation: {
        'spin-slow': 'spin 8s linear infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      }
    },
  },
  plugins: [],
}
