import { parseUtc } from './time'
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

// --- Whole-mission view -------------------------------------------------------------------------
// Mission day of a timestamp: the latest measurement is on day `missionDay` (today), one day per
// 24 h before it. Fractional, so several readings within a day keep their order.

export interface DayValue {
  day: number
  value: number
}

export function missionDayAt(ts: string, latest: number, missionDay: number): number {
  return missionDay - (latest - parseUtc(ts)) / DAY_MS
}

function latestTs(measurements: Measurement[]): number {
  return Math.max(...measurements.map((m) => parseUtc(m.timestamp)))
}

/** One mean per mission day (so many device readings in one day count as one day). */
export function dailyMeans(measurements: Measurement[], missionDay: number): DayValue[] {
  if (!measurements.length) return []
  const latest = latestTs(measurements)
  const byDay = new Map<number, number[]>()
  for (const m of measurements) {
    const day = Math.round(missionDayAt(m.timestamp, latest, missionDay))
    if (day < 1) continue // before the mission started
    byDay.set(day, [...(byDay.get(day) ?? []), m.value])
  }
  return [...byDay.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([day, vs]) => ({ day, value: vs.reduce((x, y) => x + y, 0) / vs.length }))
}

/** Trailing rolling mean over `window` mission days (days without data are skipped). */
export function rollingMean(daily: DayValue[], window = 7): DayValue[] {
  return daily.map(({ day }) => {
    const inWindow = daily.filter((d) => d.day > day - window && d.day <= day)
    return { day, value: inWindow.reduce((x, d) => x + d.value, 0) / inWindow.length }
  })
}

export interface MissionStats {
  average: number | null
  /** Days 1–14. */
  firstTwoWeeks: number | null
  /** The last 14 mission days. */
  lastTwoWeeks: number | null
  /** lastTwoWeeks − firstTwoWeeks, or null when either is missing. */
  change: number | null
}

export function missionStats(measurements: Measurement[], missionDay: number): MissionStats {
  const daily = dailyMeans(measurements, missionDay)
  const mean = (xs: DayValue[]) => (xs.length ? xs.reduce((a, d) => a + d.value, 0) / xs.length : null)
  const firstTwoWeeks = mean(daily.filter((d) => d.day <= 14))
  const lastTwoWeeks = mean(daily.filter((d) => d.day > missionDay - 14))
  return {
    average: mean(daily),
    firstTwoWeeks,
    lastTwoWeeks,
    change: firstTwoWeeks !== null && lastTwoWeeks !== null ? lastTwoWeeks - firstTwoWeeks : null,
  }
}
