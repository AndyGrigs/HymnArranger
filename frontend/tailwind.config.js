/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        main: "var(--main-color)",
        text: "var(--text-color)",
        gray: "var(--gray-color)",
        lightgray: "var(--lightgray-color)",
        button: "var(--button-color)",
        "button-hover": "var(--button-hover-color)",
        rating: "var(--rating-color)",
        badges: "var(--badges-color)",
        inputs: "var(--inputs-color)",
        white: "var(--white-color)",
      },
      fontFamily: {
        main: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
