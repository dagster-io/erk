/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['Source Serif 4', 'serif'],
      },
      colors: {
        'blue-brand': {
          DEFAULT: '#3C39EE',
          dark: '#1713e1',
        },
        'light-blue-brand': '#468AFC',
        'teal-brand': '#0DA7CD',
      },
    },
  },
  plugins: [],
};
