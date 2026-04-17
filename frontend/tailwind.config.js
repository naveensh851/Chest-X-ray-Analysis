/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'sans-serif'],
        display: ['Sora', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        navy: {
          50:  '#f0f4ff',
          100: '#e0eaff',
          200: '#c1d4fe',
          300: '#93b3fd',
          400: '#5f87f9',
          500: '#3b5ff5',
          600: '#1f3de8',
          700: '#1a2fd4',
          800: '#1a28ab',
          900: '#1b2787',
          950: '#141954',
        },
        clinical: {
          50:  '#f5faff',
          100: '#eaf3ff',
          200: '#d3e7ff',
          300: '#aacffe',
          400: '#74adfc',
          500: '#4788f8',
          600: '#2e68ed',
          700: '#2353d9',
          800: '#2244b0',
          900: '#213d8b',
        },
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'pulse-soft': 'pulse 3s ease-in-out infinite',
        'fade-in': 'fadeIn 0.6s ease forwards',
        'slide-up': 'slideUp 0.5s ease forwards',
        'scale-in': 'scaleIn 0.4s ease forwards',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to:   { opacity: '1', transform: 'scale(1)' },
        },
      },
      boxShadow: {
        'card': '0 4px 24px -4px rgba(30,50,120,0.10), 0 1.5px 6px -1px rgba(30,50,120,0.06)',
        'card-hover': '0 12px 40px -8px rgba(30,50,120,0.16), 0 4px 14px -2px rgba(30,50,120,0.10)',
        'glow': '0 0 32px 0 rgba(59,95,245,0.18)',
        'inner-lg': 'inset 0 2px 10px 0 rgba(30,50,120,0.08)',
      },
    },
  },
  plugins: [],
}
