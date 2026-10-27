/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class', // Enable dark mode using the 'dark' class
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          green: '#7DC832',
          navy: '#1A1F3A',
        },
        background: {
          light: '#f7fafc',
          dark: '#0f172a', // Slate 900
          cardLight: '#ffffff',
          cardDark: '#1e293b', // Slate 800
        },
        text: {
          primaryLight: '#1A1F3A',
          secondaryLight: '#718096',
          primaryDark: '#f1f5f9', // Slate 100
          secondaryDark: '#94a3b8', // Slate 400
        },
        border: {
          light: '#e2e8f0',
          dark: '#334155', // Slate 700
        }
      }
    },
  },
  plugins: [],
}
