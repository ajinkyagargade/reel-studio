/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { display: ['"Space Grotesk"', 'Inter', 'sans-serif'], sans: ['Inter', 'sans-serif'] },
      boxShadow: { glow: '0 0 30px rgba(124,58,237,.45)' },
      colors: { 'dark-200': '#12121a' },
      colors: {
        brand: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
        },
      },
    },
  },
  plugins: [],
};
