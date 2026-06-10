'use client'

import type { FilterState, EstadoType } from '@/lib/types'

const ESTADO_CHIPS: { label: string; value: string; cls: string }[] = [
  { label: 'Todos',          value: '',           cls: 'border-y text-y bg-[#1C140020]' },
  { label: 'Pendiente',      value: 'pendiente',  cls: 'border-brd2 text-wht bg-card2' },
  { label: '✓ Enviado',      value: 'enviado',    cls: 'border-env text-env bg-[#052E1620]' },
  { label: '⭐ Interesado',  value: 'interesado', cls: 'border-[#EAB308] text-[#EAB308] bg-[#1C140020]' },
  { label: '✕ Descartado',  value: 'descartado', cls: 'border-[#6B7280] text-[#9CA3AF] bg-[#37415120]' },
]

interface Props {
  filter: FilterState
  zonas: string[]
  keywords: string[]
  visCount: number
  total: number
  onChange: (patch: Partial<FilterState>) => void
  onExport: () => void
}

export default function FilterBar({
  filter, zonas, keywords, visCount, total, onChange, onExport,
}: Props) {
  return (
    <div className="sticky top-[89px] z-20 bg-panel border-b border-brd
      px-6 py-3 flex flex-wrap items-center gap-3">

      {/* Search */}
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted text-sm">🔍</span>
        <input
          type="text"
          placeholder="Buscar empresa..."
          value={filter.search}
          onChange={e => onChange({ search: e.target.value })}
          className="bg-card border border-brd rounded-lg pl-8 pr-3 py-1.5
            text-sm text-wht placeholder:text-muted outline-none
            focus:border-y w-48 transition-colors"
        />
      </div>

      {/* Zona */}
      <Select
        label="Zona"
        value={filter.zona}
        onChange={v => onChange({ zona: v })}
      >
        <option value="">Todas las zonas</option>
        {zonas.map(z => <option key={z} value={z}>{z}</option>)}
      </Select>

      {/* Tipo */}
      <Select label="Tipo" value={filter.tipo} onChange={v => onChange({ tipo: v })}>
        <option value="">Todos</option>
        <option value="utilitario">🚛 Utilitarios</option>
        <option value="alta_gama">⭐ Alta Gama</option>
      </Select>

      {/* Keyword */}
      <Select label="Rubro" value={filter.keyword} onChange={v => onChange({ keyword: v })}>
        <option value="">Todos los rubros</option>
        {keywords.map(k => <option key={k} value={k}>{k}</option>)}
      </Select>

      {/* Estado chips */}
      <div className="hidden md:flex items-center gap-1.5">
        {ESTADO_CHIPS.map(chip => (
          <button
            key={chip.value}
            onClick={() => onChange({ estado: chip.value })}
            className={`px-3 py-1 rounded-full text-[11px] font-bold border transition-all
              ${filter.estado === chip.value ? chip.cls : 'border-brd text-muted bg-card hover:border-brd2 hover:text-wht'}`}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Solo Móviles toggle */}
      <button
        onClick={() => onChange({ onlyMovil: !filter.onlyMovil })}
        className={`px-3 py-1 rounded-full text-[11px] font-bold border transition-all
          ${filter.onlyMovil
            ? 'border-env text-env bg-[#052E1620]'
            : 'border-brd text-muted bg-card hover:border-env hover:text-env'}`}
      >
        📱 Solo Móviles
      </button>

      {/* Spacer + count + export */}
      <div className="ml-auto flex items-center gap-3">
        <span className="text-xs text-muted hidden sm:block">
          Mostrando <strong className="text-wht">{visCount}</strong> de <strong className="text-wht">{total}</strong>
        </span>
        <button
          onClick={onExport}
          className="px-3 py-1.5 text-xs font-bold rounded-lg border border-brd
            text-muted bg-card hover:border-y hover:text-y transition-all"
        >
          📥 Exportar CSV
        </button>
      </div>
    </div>
  )
}

function Select({
  label, value, onChange, children,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-1.5">
      <label className="text-[10px] font-bold text-muted uppercase tracking-wide hidden sm:block">
        {label}
      </label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="bg-card border border-brd rounded-lg px-3 py-1.5 text-sm text-wht
          outline-none focus:border-y cursor-pointer min-w-[130px] transition-colors
          [&>option]:bg-card2"
      >
        {children}
      </select>
    </div>
  )
}
