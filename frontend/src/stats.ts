import type { Measurement } from './types'

const DAY_MS = 24 * 60 * 60 * 1000

export interface PeriodSummary {
  average: number | null
  min: number | null
  max: number | null
  count: number
}

export interface PeriodStats {
  /** The last `days` days, ending at the latest measurement. */
  current: PeriodSummary
  /** The `days` days just before the current period. */
  previous: PeriodSummary
  /** current.average − previous.average, or null when either period is empty. */
  change: number | null
}

export interface PeriodWindow {
  start: number
  end: number
}

/**
 * Window of `days` days ending at the latest measurement (not at "now", so the
 * demo works whenever the data was generated). Points with start < t ≤ end belong to it.
 */
export function periodWindow(measurements: Measurement[], days: number): PeriodWindow | null {
  if (!measurements.length) return null
  const end = Math.max(...measurements.map((m) => Date.parse(m.timestamp)))
  return { start: end - days * DAY_MS, end }
}

/** Measurements inside the selected period. */
export function inPeriod(measurements: Measurement[], days: number): Measurement[] {
  const w = periodWindow(measurements, days)
  if (!w) return []
  return measurements.filter((m) => {
    const t = Date.parse(m.timestamp)
    return t > w.start && t <= w.end
  })
}

function summarize(values: number[]): PeriodSummary {
  if (!values.length) return { average: null, min: null, max: null, count: 0 }
  return {
    average: values.reduce((a, b) => a + b, 0) / values.length,
    min: Math.min(...values),
    max: Math.max(...values),
    count: values.length,
  }
}

/** Stats for the selected period and the previous period of the same length. */
export function periodStats(measurements: Measurement[], days: number): PeriodStats {
  const w = periodWindow(measurements, days)
  if (!w) {
    const empty = summarize([])
    return { current: empty, previous: empty, change: null }
  }
  const prevStart = w.start - days * DAY_MS
  const cur: number[] = []
  const prev: number[] = []
  for (const m of measurements) {
    const t = Date.parse(m.timestamp)
    if (t > w.start && t <= w.end) cur.push(m.value)
    else if (t > prevStart && t <= w.start) prev.push(m.value)
  }
  const current = summarize(cur)
  const previous = summarize(prev)
  const change =
    current.average !== null && previous.average !== null ? current.average - previous.average : null
  return { current, previous, change }
}
