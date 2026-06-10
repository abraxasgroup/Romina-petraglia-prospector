import type { TelType } from './types'

export function detectPhoneType(raw: string): TelType {
  if (!raw) return 'desconocido'
  const clean = raw.replace(/[\s\-().+]/g, '')

  if (clean.startsWith('0800') || clean.startsWith('0810')) return 'fijo'
  if (/^\+?549/.test(clean)) return 'movil'
  if (/0\d{3,4}[\s-]?15[\s-]/.test(raw)) return 'movil'
  if (/^15\d{7,8}$/.test(clean)) return 'movil'
  if (/^\+?54[^9]/.test(clean)) return 'fijo'

  // Fallback: normalise and check for leading 549
  const norm = normalizePhone(raw)
  if (norm?.startsWith('549')) return 'movil'
  if (norm?.startsWith('54') && norm.length >= 10) return 'fijo'

  return 'desconocido'
}

function normalizePhone(raw: string): string | null {
  const clean = raw.replace(/[\s\-().+]/g, '')
  if (!clean || !/\d/.test(clean)) return null
  if (clean.startsWith('54') && clean.length >= 10) return clean
  if (clean.startsWith('0') && clean.length >= 8) return '54' + clean.slice(1)
  if (clean.startsWith('15') && clean.length === 10) return '54911' + clean.slice(2)
  if (clean.length >= 8) return '54' + clean
  return null
}
