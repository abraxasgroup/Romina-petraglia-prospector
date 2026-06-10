import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Viper Prospector · Petraglia Renault',
  description: 'Panel de gestión WhatsApp para prospección comercial',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  )
}
