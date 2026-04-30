import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f7f7f5",
        ink: "#20211f",
        muted: "#62645f",
        line: "#ddddda",
      },
    },
  },
  plugins: [],
};

export default config;
