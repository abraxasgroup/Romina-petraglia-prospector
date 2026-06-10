'use client'

import { memo } from 'react'
import type { Lead, EstadoType } from '@/lib/types'
import { detectPhoneType } from '@/lib/phone'
import { getWAMessage } from '@/lib/messages'

const ESTADO_STYLES: Record<EstadoType, string> = {
  pendiente:  '',
  enviado:    'border-l-env bg-gradient-to-br from-card to-[#052E1608]',
  interesado: 'border-l-[#EAB308] bg-gradient-to-br from-card to-[#1C140008]',
  descartado: 'opacity-40 grayscale border-l-[#374151]',
}

const ESTADO_BADGE: Record<EstadoType, { label: string; cls: string }> = {
  pendiente:  { label: '', cls: '' },
  enviado:    { label: '✓ Mensaje enviado', cls: 'bg-[#052E16] text-env border border-[#22C55E40]' },
  interesado: { label: '⭐ Interesado',      cls: 'bg-[#1C1400] text-[#EAB308] border border-[#EAB30840]' },
  descartado: { label: '✕ Descartado',       cls: 'bg-[#37415130] text-[#9CA3AF] border border-[#6B728040]' },
}

interface Props {
  lead: Lead
  id: string
  estado: EstadoType
  onMark: (id: string, state: EstadoType) => void
}

function LeadCard({ lead, id, estado, onMark }: Props) {
  const telTipo = detectPhoneType(lead.telefono_raw ?? '')
  const msg = getWAMessage(lead.keyword, lead.modelo_sugerido, lead.tipo)
  const msgEnc = encodeURIComponent(msg)

  const telBadge =
    telTipo === 'movil' ? (
      <span className="badge bg-[#052E16] text-env border border-[#22C55E40]">📱 Móvil</span>
    ) : telTipo === 'fijo' ? (
      <span className="badge bg-[#1C1C2A] text-muted border border-[#6B728040]">☎️ Fijo</span>
    ) : null

  const tipoBadge =
    lead.tipo === 'utilitario' ? (
      <span className="badge bg-[#3A1800] text-util border border-[#FF6B3540]">🚛 Utilitario</span>
    ) : (
      <span className="badge bg-[#2A0A3A] text-ag border border-[#A855F740]">⭐ Alta Gama</span>
    )

  const estadoBadge = ESTADO_BADGE[estado]

  return (
    <div
      className={`flex flex-col rounded-2xl border border-brd border-l-4
        overflow-hidden transition-all duration-200
        hover:-translate-y-1 hover:shadow-[0_12px_32px_rgba(0,0,0,.4)] hover:border-brd2
        ${ESTADO_STYLES[estado]}`}
    >
      {/* Header */}
      <div className="bg-card2 px-4 py-3 flex justify-between items-start gap-2 border-b border-brd">
        <p className="text-wht font-bold text-sm leading-snug flex-1">{lead.nombre}</p>
        <div className="flex flex-col gap-1 items-end shrink-0">
          {tipoBadge}
          <span className="badge bg-y text-bg font-black">{lead.modelo_sugerido}</span>
          {telBadge}
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 flex-1 flex flex-col gap-2">
        <Row icon="📍" text={lead.direccion || 'Dirección no disponible'} />
        <Row icon="📞" text={lead.telefono_raw ?? 'Sin teléfono'} bold />
        {lead.categoria_gmaps && <Row icon="🏷️" text={lead.categoria_gmaps} />}
        {lead.rating && (
          <Row
            icon="⭐"
            text={`${lead.rating}${lead.reviews ? ` · ${lead.reviews} reseñas` : ''}`}
          />
        )}
        <div className="flex items-center gap-2">
          <span className="text-xs opacity-60">🔍</span>
          <span className="text-[10px] italic bg-[#1E1E40] text-[#818CF8] px-2 py-0.5 rounded">
            {lead.keyword}
          </span>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-brd bg-card2 flex flex-col gap-2">
        {lead.telefono_wa ? (
          <a
            href={`https://wa.me/${lead.telefono_wa}?text=${msgEnc}`}
            target="_blank"
            rel="noreferrer"
            onClick={() => onMark(id, 'enviado')}
            className="flex items-center justify-center gap-2 w-full text-center
              bg-gradient-to-br from-wa to-wad text-white
              py-2.5 px-3 rounded-xl font-bold text-sm
              hover:opacity-90 active:scale-95 transition-all
              shadow-[0_4px_12px_#25D36630]"
          >
            💬 Enviar WhatsApp
          </a>
        ) : (
          <span className="block text-center py-2.5 text-dim text-xs border border-dashed border-brd rounded-xl">
            📵 Teléfono no disponible
          </span>
        )}

        {/* Status buttons */}
        <div className="flex gap-1.5">
          <BtnEst
            active={estado === 'interesado'}
            onClick={() => onMark(id, estado === 'interesado' ? 'pendiente' : 'interesado')}
            activeClass="bg-[#EAB30820] border-[#EAB308] text-[#EAB308]"
          >
            ⭐ Interesado
          </BtnEst>
          <BtnEst
            active={estado === 'descartado'}
            onClick={() => onMark(id, estado === 'descartado' ? 'pendiente' : 'descartado')}
            activeClass="bg-[#37415130] border-[#6B7280] text-[#9CA3AF]"
          >
            ✕ Descartar
          </BtnEst>
          <BtnEst
            active={false}
            onClick={() => onMark(id, 'pendiente')}
            activeClass=""
            className="w-9 shrink-0"
            title="Resetear"
          >
            ↩
          </BtnEst>
        </div>

        {/* Estado badge */}
        {estadoBadge.label && (
          <p className={`text-center text-xs font-bold py-1 px-3 rounded-full ${estadoBadge.cls}`}>
            {estadoBadge.label}
          </p>
        )}
      </div>
    </div>
  )
}

function Row({ icon, text, bold }: { icon: string; text: string; bold?: boolean }) {
  return (
    <div className="flex gap-2 items-start text-xs text-muted">
      <span className="shrink-0 w-4 text-center opacity-70">{icon}</span>
      <span className={bold ? 'text-wht font-semibold' : 'text-[#C0C0E0]'}>{text}</span>
    </div>
  )
}

function BtnEst({
  children,
  active,
  onClick,
  activeClass,
  className = '',
  title,
}: {
  children: React.ReactNode
  active: boolean
  onClick: () => void
  activeClass: string
  className?: string
  title?: string
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`flex-1 py-1.5 px-1 text-[11px] font-bold rounded-lg border
        transition-all cursor-pointer
        ${active ? activeClass : 'border-brd text-muted hover:border-brd2 hover:text-wht hover:bg-brd'}
        ${className}`}
    >
      {children}
    </button>
  )
}

export default memo(LeadCard)
