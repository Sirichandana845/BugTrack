module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef2ff', 100: '#e0e7ff', 500: '#6366f1',
          600: '#4f46e5', 700: '#4338ca'
        }
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)'
      }
    }
  },
  plugins: []
}
