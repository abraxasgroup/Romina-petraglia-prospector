'use client'

import { useEffect, useState } from 'react'
import type { ToastItem } from '@/lib/types'

const CONFIG: Record<string, { icon: string; msg: string; color: string }> = {
  enviado:    { icon: '✅', msg: 'Marcado como Enviado',    color: '#22C55E' },
  interesado: { icon: '⭐', msg: 'Marcado como Interesado', color: '#EAB308' },
  descartado: { icon: '✕',  msg: 'Marcado como Descartado', color: '#6B7280' },
  pendiente:  { icon: '↩',  msg: 'Reseteado a Pendiente',   color: '#818CF8' },
  csv:        { icon: '📥', msg: 'CSV exportado',            color: '#818CF8' },
}

function ToastBubble({ item, onDone }: { item: ToastItem; onDone: () => void }) {
  const [fading, setFading] = useState(false)
  const cfg = CONFIG[item.state]

  useEffect(() => {
    const t1 = setTimeout(() => setFading(true), 2000)
    const t2 = setTimeout(onDone, 2350)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [onDone])

  return (
    <div
      className={`flex items-center gap-2 px-4 py-3 rounded-xl border border-brd2
        bg-card2 shadow-xl text-sm font-semibold text-wht transition-all duration-300
        ${fading ? 'opacity-0 translate-x-4' : 'opacity-100 translate-x-0'}`}
      style={{ borderLeftColor: cfg.color, borderLeftWidth: 3 }}
    >
      <span>{cfg.icon}</span>
      <span>{cfg.msg}</span>
    </div>
  )
}

export default function Toast({
  toasts,
  onRemove,
}: {
  toasts: ToastItem[]
  onRemove: (id: number) => void
}) {
  return (
    <div className="fixed top-20 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <ToastBubble key={t.id} item={t} onDone={() => onRemove(t.id)} />
      ))}
    </div>
  )
}
