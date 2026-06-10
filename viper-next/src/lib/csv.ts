import type { Lead, EstadoType } from './types'
import { detectPhoneType } from './phone'

export function exportCSV(leads: Lead[], estados: Record<string, EstadoType>) {
  const headers = [
    'Nombre', 'Dirección', 'Teléfono', 'Tipo Línea',
    'Modelo Sugerido', 'Zona', 'Rubro', 'Estado', 'Link WhatsApp',
  ]

  const rows = leads.map((lead, i) => {
    const id = `c${i}`
    const telTipo = detectPhoneType(lead.telefono_raw ?? '')
    return [
      lead.nombre,
      lead.direccion ?? '',
      lead.telefono_raw ?? '',
      telTipo === 'movil' ? 'Móvil' : telTipo === 'fijo' ? 'Fijo' : 'Desconocido',
      lead.modelo_sugerido,
      lead.zona,
      lead.keyword,
      estados[id] ?? 'pendiente',
      lead.telefono_wa ? `https://wa.me/${lead.telefono_wa}` : '',
    ]
  })

  const escape = (v: string) => `"${v.replace(/"/g, '""')}"`
  const lines = [headers, ...rows].map(r => r.map(v => escape(String(v ?? ''))).join(','))
  // BOM + CRLF — Excel lo abre directamente con tildes correctas
  const csv = '﻿' + lines.join('\r\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `prospeccion_renault_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
