import type { Lead } from '@/lib/types'
import { detectPhoneType } from '@/lib/phone'

interface ZonaStat {
  total: number
  util: number
  ag: number
  conWa: number
  movil: number
}

export default function StatsTable({ leads }: { leads: Lead[] }) {
  const stats: Record<string, ZonaStat> = {}

  for (const lead of leads) {
    const z = lead.zona || 'Sin zona'
    if (!stats[z]) stats[z] = { total: 0, util: 0, ag: 0, conWa: 0, movil: 0 }
    stats[z].total++
    if (lead.tipo === 'utilitario') stats[z].util++
    else stats[z].ag++
    if (lead.telefono_wa) stats[z].conWa++
    if (detectPhoneType(lead.telefono_raw ?? '') === 'movil') stats[z].movil++
  }

  const zonas = Object.keys(stats).sort()
  const totals = Object.values(stats).reduce(
    (acc, s) => ({
      total: acc.total + s.total,
      util: acc.util + s.util,
      ag: acc.ag + s.ag,
      conWa: acc.conWa + s.conWa,
      movil: acc.movil + s.movil,
    }),
    { total: 0, util: 0, ag: 0, conWa: 0, movil: 0 },
  )

  return (
    <div className="mt-10 bg-panel rounded-2xl border border-brd overflow-hidden">
      <div className="bg-card2 border-b border-brd px-5 py-3.5">
        <h2 className="text-y font-extrabold text-sm">📊 Resumen por Zona</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-card">
              {['Zona','Total','🚛 Util.','⭐ AG','📞 Con WA','📱 Móviles'].map(h => (
                <th key={h}
                  className="px-4 py-2.5 text-left text-[10px] font-bold uppercase
                    tracking-wide text-muted border-b border-brd">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {zonas.map(z => (
              <tr key={z} className="border-t border-brd hover:bg-card2 transition-colors">
                <td className="px-4 py-2.5 font-semibold text-wht">{z}</td>
                <td className="px-4 py-2.5 text-center text-wht">{stats[z].total}</td>
                <td className="px-4 py-2.5 text-center text-util font-semibold">{stats[z].util}</td>
                <td className="px-4 py-2.5 text-center text-ag font-semibold">{stats[z].ag}</td>
                <td className="px-4 py-2.5 text-center text-env font-semibold">{stats[z].conWa}</td>
                <td className="px-4 py-2.5 text-center text-env font-semibold">{stats[z].movil}</td>
              </tr>
            ))}
            {/* Total row */}
            <tr className="border-t-2 border-brd2 bg-[#1C140020] font-bold">
              <td className="px-4 py-2.5 text-y">TOTAL</td>
              <td className="px-4 py-2.5 text-center text-y">{totals.total}</td>
              <td className="px-4 py-2.5 text-center text-util">{totals.util}</td>
              <td className="px-4 py-2.5 text-center text-ag">{totals.ag}</td>
              <td className="px-4 py-2.5 text-center text-env">{totals.conWa}</td>
              <td className="px-4 py-2.5 text-center text-env">{totals.movil}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
