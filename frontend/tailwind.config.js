/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta RCA
        navy: {
          DEFAULT: '#1E2B5E',
          50: '#F2F4FA',
          100: '#E0E5F0',
          200: '#B7C0DA',
          300: '#7E8DBA',
          400: '#4A5C95',
          500: '#1E2B5E',
          600: '#19244F',
          700: '#141D40',
          800: '#0F1631',
          900: '#0A0F22',
        },
        olive: {
          DEFAULT: '#8A9A5B',
          50: '#F5F7EE',
          100: '#E9EDD7',
          200: '#D2DAB0',
          300: '#B5C285',
          400: '#9CAB6B',
          500: '#8A9A5B',
          600: '#6F7C49',
          700: '#5A6539',
          800: '#454D2B',
          900: '#30371D',
        },
        military: '#3D4F1E',
        leather: '#6B4C30',
        sand: '#A8845F',
        tan: '#C4B99A',
        bone: {
          DEFAULT: '#EEEAE3',
          50: '#FAFAF8',
          100: '#F5F2EC',
          200: '#EEEAE3',
          300: '#E5E0D6',
          400: '#D4CCBC',
        },
        // Aliases semánticos
        bg: '#FAFAF8',
        surface: '#FFFFFF',
        surface2: '#F5F2EC',
        border: '#E5E0D6',
        text: '#1E2B5E',
        muted: '#6B7280',
        accent: '#8A9A5B',
        success: '#3D4F1E',
        warn: '#A8845F',
        danger: '#B33A3A',
      },
      fontFamily: {
        display: ['"SF Pro Display"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Helvetica', 'Arial', 'sans-serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Helvetica', 'Arial', 'sans-serif'],
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.025em',
      },
      boxShadow: {
        'soft': '0 1px 2px rgba(30, 43, 94, 0.04), 0 4px 12px rgba(30, 43, 94, 0.04)',
        'card': '0 1px 3px rgba(30, 43, 94, 0.06), 0 8px 24px rgba(30, 43, 94, 0.06)',
        'lift': '0 4px 8px rgba(30, 43, 94, 0.08), 0 16px 40px rgba(30, 43, 94, 0.08)',
        'inner-soft': 'inset 0 1px 2px rgba(30, 43, 94, 0.04)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scaleIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(24px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.96)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
