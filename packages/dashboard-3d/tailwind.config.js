/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: {
          950: '#070A12',
          900: '#0B1020',
          800: '#101A34',
        },
        neon: {
          cyan: '#22D3EE',
          amber: '#F59E0B',
          crimson: '#FB7185',
        },
      },
      boxShadow: {
        glass: '0 10px 30px rgba(0,0,0,0.35)',
      },
      backdropBlur: {
        glass: '14px',
      },
    },
  },
  plugins: [],
}
