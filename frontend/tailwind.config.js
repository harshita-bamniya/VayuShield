/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        aqi: {
          good: "#00B050",
          satisfactory: "#92D050",
          moderate: "#FFFF00",
          poor: "#FF0000",
          "very-poor": "#C00000",
          severe: "#7030A0",
        },
      },
    },
  },
  plugins: [],
};
