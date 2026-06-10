'use client'

interface Props {
  total: number
  conWa: number
  conMovil: number
  enviados: number
  interesados: number
}

export default function Header({ total, conWa, conMovil, enviados, interesados }: Props) {
  const pct = conWa > 0 ? Math.round((enviados / conWa) * 100) : 0

  return (
    <header className="bg-panel border-b border-brd px-6 py-4 sticky top-0 z-30
      backdrop-blur-xl">
      <div className="max-w-screen-xl mx-auto flex items-center justify-between gap-4 flex-wrap">

        {/* Logo + título */}
        <div className="flex items-center gap-3">
          <img
            src="/romina.jpg"
            alt="Romina"
            className="w-12 h-12 rounded-full object-cover ring-2 ring-y/20 shrink-0"
          />
          <div>
            <h1 className="text-base font-black tracking-tight
              bg-gradient-to-r from-wht to-y bg-clip-text text-transparent">
              Viper Prospector · Petraglia Renault
            </h1>
            <p className="text-[11px] text-muted mt-0.5 flex items-center gap-1.5">
              Panel WhatsApp ·
              <a
                href="https://wa.me/5492226512253"
                target="_blank"
                rel="noreferrer"
                className="text-y font-semibold hover:underline"
              >
                Romina +54 9 2226-512253
              </a>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full
                bg-gradient-to-r from-purple-600 to-blue-500 text-white uppercase tracking-wide">
                ⚡ IA
              </span>
            </p>
          </div>
        </div>

        {/* KPIs */}
        <div className="flex gap-2 flex-wrap">
          <Kpi label="Leads"       value={total}       />
          <Kpi label="Con WA"      value={conWa}       />
          <Kpi label="📱 Móviles" value={conMovil}    color="text-env" />
          <Kpi label="Enviados"    value={enviados}    color="text-env" />
          <Kpi label="Interesados" value={interesados} color="text-[#EAB308]" />
        </div>
      </div>

      {/* Progress bar */}
      <div className="max-w-screen-xl mx-auto mt-3">
        <div className="flex justify-between text-[11px] text-muted mb-1">
          <span>Progreso de contacto</span>
          <strong className="text-wht">{enviados} de {conWa} contactados ({pct}%)</strong>
        </div>
        <div className="h-1.5 bg-brd rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-env to-y rounded-full transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </header>
  )
}

function Kpi({ label, value, color = 'text-y' }: {
  label: string; value: number; color?: string
}) {
  return (
    <div className="bg-card border border-brd rounded-xl px-3 py-2 text-center min-w-[68px]">
      <div className={`text-xl font-black leading-none ${color}`}>{value}</div>
      <div className="text-[9px] text-muted uppercase tracking-wide mt-1">{label}</div>
    </div>
  )
}
