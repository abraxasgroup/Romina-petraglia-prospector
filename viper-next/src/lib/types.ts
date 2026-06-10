export interface Lead {
  nombre: string
  categoria_gmaps: string
  direccion: string
  telefono_raw: string | null
  telefono_wa: string | null
  rating: string
  reviews: string
  keyword: string
  tipo: 'utilitario' | 'alta_gama'
  zona: string
  modelo_sugerido: string
  scraped_at: string
}

export type EstadoType = 'pendiente' | 'enviado' | 'interesado' | 'descartado'
export type TelType = 'movil' | 'fijo' | 'desconocido'

export interface FilterState {
  zona: string
  tipo: string
  keyword: string
  estado: string
  onlyMovil: boolean
  search: string
}

export interface ToastItem {
  id: number
  state: EstadoType | 'csv'
}
