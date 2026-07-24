/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        orbitron: ['Orbitron', 'sans-serif'],
        rajdhani: ['Rajdhani', 'sans-serif'],
      },
      colors: {
        cyan: {
          primary: '#00f7ff',
          dim: '#00b8c4',
          glow: 'rgba(0,247,255,0.3)',
        },
        blue: {
          hud: '#0080ff',
          deep: '#0a0e17',
          panel: 'rgba(0,20,40,0.75)',
        },
        green: {
          hud: '#00ff88',
        },
        red: {
          hud: '#ff3366',
        },
        amber: {
          hud: '#ffaa00',
        },
      },
      boxShadow: {
        'cyan-glow': '0 0 20px rgba(0,247,255,0.5)',
        'cyan-glow-lg': '0 0 40px rgba(0,247,255,0.7)',
        'green-glow': '0 0 10px rgba(0,255,136,0.5)',
        'red-glow': '0 0 10px rgba(255,51,102,0.5)',
      },
      backdropBlur: {
        hud: '12px',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'spin-slow': 'spin 8s linear infinite',
        'spin-reverse': 'spinReverse 6s linear infinite',
        'spin-medium': 'spin 12s linear infinite',
        'scan-line': 'scanLine 3s linear infinite',
        'radar-sweep': 'radarSweep 3s linear infinite',
        blink: 'blink 1s step-end infinite',
        'data-flow': 'dataFlow 2s linear infinite',
        'fade-in-up': 'fadeInUp 0.5s ease-out',
        'scan-overlay': 'scanOverlay 0.1s linear infinite',
        float: 'float 4s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(0,247,255,0.5)' },
          '50%': { boxShadow: '0 0 50px rgba(0,247,255,0.9), 0 0 80px rgba(0,247,255,0.4)' },
        },
        spinReverse: {
          from: { transform: 'rotate(360deg)' },
          to: { transform: 'rotate(0deg)' },
        },
        radarSweep: {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.2' },
        },
        dataFlow: {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '0 60px' },
        },
        fadeInUp: {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
      },
    },
  },
  plugins: [],
};
