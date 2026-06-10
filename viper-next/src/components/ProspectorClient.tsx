'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import type { Lead, EstadoType, FilterState, ToastItem } from '@/lib/types'
import { detectPhoneType } from '@/lib/phone'
import { exportCSV } from '@/lib/csv'
import Header from './Header'
import FilterBar from './FilterBar'
import LeadCard from './LeadCard'
import StatsTable from './StatsTable'
import Toast from './Toast'

const STORE = 'viper_v2_'
const PAGE_SIZE = 60

export default function ProspectorClient() {
  const [leads, setLeads]     = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [estados, setEstados] = useState<Record<string, EstadoType>>({})
  const [filter, setFilter]   = useState<FilterState>({
    zona: '', tipo: '', keyword: '', estado: '', onlyMovil: false, search: '',
  })
  const [page, setPage]     = useState(1)
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const [toastSeq, setToastSeq] = useState(0)

  // Fetch leads + rehydrate localStorage
  useEffect(() => {
    fetch('/leads.json')
      .then(r => r.json())
      .then((data: Lead[]) => {
        setLeads(data)
        const saved: Record<string, EstadoType> = {}
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i)
          if (key?.startsWith(STORE))
            saved[key.slice(STORE.length)] = localStorage.getItem(key) as EstadoType
        }
        setEstados(saved)
        setLoading(false)
      })
  }, [])

  const showToast = useCallback((state: EstadoType | 'csv') => {
    setToastSeq(s => {
      const id = s + 1
      setToasts(t => [...t, { id, state }])
      return id
    })
  }, [])

  const markState = useCallback((id: string, state: EstadoType) => {
    setEstados(prev => ({ ...prev, [id]: state }))
    localStorage.setItem(STORE + id, state)
    showToast(state)
  }, [showToast])

  // Stats
  const conWa      = useMemo(() => leads.filter(l => l.telefono_wa).length, [leads])
  const conMovil   = useMemo(() => leads.filter(l => detectPhoneType(l.telefono_raw ?? '') === 'movil').length, [leads])
  const enviados   = useMemo(() => Object.values(estados).filter(e => e === 'enviado').length, [estados])
  const interesados = useMemo(() => Object.values(estados).filter(e => e === 'interesado').length, [estados])

  // Filter options
  const zonas    = useMemo(() => Array.from(new Set(leads.map(l => l.zona))).sort(), [leads])
  const keywords = useMemo(() => Array.from(new Set(leads.map(l => l.keyword))).sort(), [leads])

  // Filtered list
  const filtered = useMemo(() => {
    return leads.filter((lead, i) => {
      const id = `c${i}`
      const estado  = estados[id] ?? 'pendiente'
      const telTipo = detectPhoneType(lead.telefono_raw ?? '')

      if (filter.zona     && lead.zona    !== filter.zona)    return false
      if (filter.tipo     && lead.tipo    !== filter.tipo)    return false
      if (filter.keyword  && lead.keyword !== filter.keyword) return false
      if (filter.estado   && estado       !== filter.estado)  return false
      if (filter.onlyMovil && telTipo !== 'movil')            return false
      if (filter.search   && !lead.nombre.toLowerCase().includes(filter.search.toLowerCase())) return false
      return true
    })
  }, [leads, estados, filter])

  const visible = filtered.slice(0, page * PAGE_SIZE)
  const hasMore = filtered.length > visible.length

  const handleFilter = useCallback((patch: Partial<FilterState>) => {
    setFilter(f => ({ ...f, ...patch }))
    setPage(1)
  }, [])

  const handleExport = useCallback(() => {
    exportCSV(filtered, estados)
    showToast('csv')
  }, [filtered, estados, showToast])

  if (loading) return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center gap-4">
      <div className="w-10 h-10 border-4 border-brd border-t-y rounded-full animate-spin" />
      <p className="text-muted text-sm">Cargando leads...</p>
    </div>
  )

  return (
    <div className="min-h-screen bg-bg text-wht">
      <Header
        total={leads.length}
        conWa={conWa}
        conMovil={conMovil}
        enviados={enviados}
        interesados={interesados}
      />

      <FilterBar
        filter={filter}
        zonas={zonas}
        keywords={keywords}
        visCount={filtered.length}
        total={leads.length}
        onChange={handleFilter}
        onExport={handleExport}
      />

      <main className="max-w-screen-xl mx-auto px-4 py-6">
        {filtered.length === 0 ? (
          <div className="text-center py-20 text-muted">
            <p className="text-2xl font-bold text-wht mb-2">Sin resultados</p>
            <p>Probá con otros filtros.</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {visible.map((lead) => {
                const globalIdx = leads.indexOf(lead)
                const id = `c${globalIdx}`
                return (
                  <LeadCard
                    key={id}
                    lead={lead}
                    id={id}
                    estado={estados[id] ?? 'pendiente'}
                    onMark={markState}
                  />
                )
              })}
            </div>

            {hasMore && (
              <div className="text-center mt-8">
                <button
                  onClick={() => setPage(p => p + 1)}
                  className="px-6 py-2.5 bg-card border border-brd rounded-xl
                    text-sm font-bold text-muted hover:border-y hover:text-y transition-all"
                >
                  Ver más ({filtered.length - visible.length} restantes)
                </button>
              </div>
            )}
          </>
        )}

        <StatsTable leads={leads} />

        <footer className="text-center mt-10 pb-8 text-dim text-xs flex items-center justify-center gap-2">
          <span>Petraglia Renault</span>
          <span className="px-2 py-0.5 rounded-full bg-purple-900/30 border border-purple-700/30
            text-purple-300 font-bold text-[9px] uppercase tracking-wide">
            ⚡ Viper Prospector IA
          </span>
        </footer>
      </main>

      <Toast toasts={toasts} onRemove={id => setToasts(t => t.filter(x => x.id !== id))} />
    </div>
  )
}
