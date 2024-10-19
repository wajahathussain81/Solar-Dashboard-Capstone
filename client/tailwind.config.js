/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        red_coc: "#c8102e",
        grey_coc: "#4b4f55",
        "coc-secondary-9L": "#ededee",
        "coc-secondary-1L": "#5d6066",
        "coc-secondary-2L": "#6f7277",
        "coc-secondary-3L": "#818388",
        "coc-secondary-4L": "#939599",
        "coc-secondary-8L": "#dbdcdd",
        "coc-secondary-10L": "#f6f6f6",
      },
      fontFamily: {
        sans: ["Open Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};
