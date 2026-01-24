/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', '"Helvetica Neue"', 'sans-serif'],
        body: ['"Space Grotesk"', '"Helvetica Neue"', 'sans-serif'],
      },
      colors: {
        night: '#0b1f2a',
        teal: '#1bb3a9',
        sand: '#f3e6d3',
        rust: '#d35b3f',
      },
    },
  },
  plugins: [],
};
