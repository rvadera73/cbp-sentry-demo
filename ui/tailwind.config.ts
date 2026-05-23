import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'sentry': {
          navy: '#013060',
          teal: '#4AC4D3',
          orange: '#E6800C',
          'light-blue': '#DBF3F6',
          'dark-teal': '#0B6980',
          slate: '#44546A',
        },
      },
      fontFamily: {
        sans: ['system-ui', 'Arial', 'sans-serif'],
      },
      fontSize: {
        'xs': ['0.825rem', { lineHeight: '1.1rem' }],
        'sm': ['0.9625rem', { lineHeight: '1.375rem' }],
        'base': ['1.1rem', { lineHeight: '1.65rem' }],
        'lg': ['1.2375rem', { lineHeight: '1.925rem' }],
        'xl': ['1.375rem', { lineHeight: '1.925rem' }],
        '2xl': ['1.65rem', { lineHeight: '2.2rem' }],
      },
    },
  },
  plugins: [],
} satisfies Config
