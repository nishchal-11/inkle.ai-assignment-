/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      colors: {
        ink: {
          50: "#f0f5ff",
          100: "#dfe9ff",
          500: "#4f46e5",
          600: "#4338ca",
          900: "#1e1b4b",
        },
      },
      boxShadow: {
        glass: "0 20px 45px rgba(15, 23, 42, 0.35)",
      },
    },
  },
  plugins: [],
}

