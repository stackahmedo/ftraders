/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "'Noto Sans Bengali'", "system-ui", "sans-serif"],
      },
      colors: {
        brand: { 50: "#eef7f3", 100: "#d6ede2", 500: "#1f8a5b", 600: "#18724b", 700: "#135c3d", 900: "#0b3424" },
      },
    },
  },
  plugins: [],
};
