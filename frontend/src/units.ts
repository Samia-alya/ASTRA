// Display-only conversions shown under the measurement field. Values are always stored in the
// indicator's own unit (°C, hours); these never change what is sent to the backend.

/** 36.8 -> "36.8 °C = 98.2 °F" */
export function celsiusText(c: number): string {
  return `${c.toFixed(1)} °C = ${((c * 9) / 5 + 32).toFixed(1)} °F`
}

/** 7.5 -> "7.5 h = 7 h 30 min", 8 -> "8 h = 8 h", 0.25 -> "0.25 h = 15 min" */
export function hoursText(h: number): string {
  const total = Math.round(h * 60)
  const hh = Math.floor(total / 60)
  const mm = total % 60
  const parts = [hh ? `${hh} h` : '', mm ? `${mm} min` : ''].filter(Boolean)
  return `${h} h = ${parts.join(' ') || '0 h'}`
}
