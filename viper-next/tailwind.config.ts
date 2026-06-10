import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:     '#0C0C14',
        panel:  '#13131E',
        card:   '#18182A',
        card2:  '#1E1E30',
        brd:    '#2A2A40',
        brd2:   '#3A3A55',
        y:      '#EFDF00',
        yd:     '#C4B400',
        wht:    '#F0F0FA',
        muted:  '#7070A0',
        dim:    '#3A3A58',
        wa:     '#25D366',
        wad:    '#128C7E',
        util:   '#FF6B35',
        ag:     '#A855F7',
        env:    '#22C55E',
        'int-c':'#EAB308',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
