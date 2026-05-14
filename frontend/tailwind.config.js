/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface:  '#0d0d0d',
        panel:    '#111111',
        border:   '#1e1e1e',
        up:       '#00c853',
        down:     '#f44336',
        neutral:  '#9e9e9e',
        accent:   '#1565c0',
        header:   '#0a0a0a',
      },
      fontFamily: {
        mono: ['Consolas', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': '0.65rem',
        xs: '0.72rem',
      },
    },
  },
  plugins: [],
}
