/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        'groww-green': '#00b386', // Groww's signature positive green
        'groww-red': '#eb5b3c',   // Groww's signature negative red
      }
    },
  },
  plugins: [],
}