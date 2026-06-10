export function getWAMessage(
  keyword: string,
  modelo: string,
  tipo: string,
): string {
  const kw = keyword.toLowerCase()

  if (['distribuidora', 'mayorista', 'frigorífico'].some(x => kw.includes(x)))
    return `¡Hola! Soy Romina de Petraglia Renault. Trabajamos con distribuidoras de la zona y tenemos el ${modelo} disponible en 12 cuotas sin interés. ¿Están evaluando renovar o ampliar la flota?`

  if (kw.includes('mudanza'))
    return `¡Hola! Soy Romina de Petraglia Renault. Para mudanzas tenemos la ${modelo} con financiación en cuotas. ¿Les interesaría conocer la propuesta?`

  if (['transporte', 'logística', 'fletes', 'distribuci'].some(x => kw.includes(x)))
    return `¡Hola! Soy Romina de Petraglia Renault. Trabajamos con empresas de transporte de la zona. Tenemos el ${modelo} con 0% de interés en 12 cuotas. ¿Están pensando sumar o renovar algún vehículo?`

  if (tipo === 'alta_gama')
    return `¡Hola! Soy Romina de Petraglia Renault. Tenemos el ${modelo} disponible con financiación exclusiva. ¿Les gustaría recibir más información?`

  return `¡Hola! Soy Romina de Petraglia Renault. Tenemos el ${modelo} disponible con 12 cuotas sin interés. ¿Les interesaría?`
}
