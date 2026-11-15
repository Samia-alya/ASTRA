// Must stay in sync with backend/app/models.py, routers/astronauts.py and config/indicators.json
export type Level = 'normal' | 'attention' | 'critical' | 'no_data'

export interface Astronaut {
  id: number
  name: string
  mission: string
  environment: string
  mission_day: number
}

export interface Measurement {
  id: number
  astronaut_id: number
  indicator: string
  value: number
  timestamp: string
  source: 'simulated' | 'manual' | 'device'
  device_id: number | null
  device_name: string | null
}

/** Where the latest value of an indicator comes from. */
export interface LastSource {
  type: 'simulated' | 'manual' | 'device'
  device_name: string | null
}

/** A paired device. Every device in this app is SIMULATED; the API never returns its token. */
export interface Device {
  id: number
  kind: string
  name: string
  simulated: boolean
  last_seen: string | null
  /** live: < 2 min · synced: < 24 h · stale: ≥ 24 h · never: no reading yet */
  status: 'live' | 'synced' | 'stale' | 'never'
  indicators: string[]
  /** Latest reading this device sent for each indicator it supports. */
  latest: DeviceReading[]
}

export interface DeviceReading {
  indicator: string
  label: string
  unit: string
  value: number
  timestamp: string
}

export interface IndicatorStatus {
  indicator: string
  label: string
  unit: string
  body_zone: string
  value: number | null
  baseline: number | null
  level: Level
  trend: 'up' | 'down' | 'stable'
  reasons: string[]
  last_timestamp: string | null
  last_source: LastSource | null
}

export interface StatusResponse {
  astronaut: Astronaut
  overall_level: Level
  indicators: IndicatorStatus[]
  disclaimer: string
}

export interface CheckItem {
  indicator: string
  label: string
  unit: string
  done: boolean
  last_timestamp: string | null
  hours_since_last: number | null
}

export interface ChecksResponse {
  done_count: number
  total: number
  items: CheckItem[]
}

export interface IndicatorMeta {
  label: string
  short?: string
  unit: string
  body_zone: string
  what: string
  why_in_space: string
  watch_direction: string
  guidance?: Partial<Record<Level, string>>
  sources: string[]
  /**
   * Data-entry settings. min/max/step are plausibility limits, NOT medical thresholds, and are never
   * used by the analysis. placeholder/help are examples for the form, not reference values.
   */
  input?: { min: number; max: number; step: number; note: string; placeholder?: string; help?: string }
}

/** Display a measurement with a sensible precision for its unit. */
export function fmt(value: number | null, unit: string): string {
  if (value === null) return '—'
  const whole = ['bpm', 'mmHg', 'mg/dL', '/5'].includes(unit)
  return whole ? String(Math.round(value)) : value.toFixed(1)
}

/** "Blood pressure (systolic)" -> "blood pressure", for sentences. */
export function plainName(label: string): string {
  return label.replace(/\s*\(.*\)\s*/, '').toLowerCase()
}

export const LEVEL_ORDER: Record<Level, number> = { critical: 0, attention: 1, normal: 2, no_data: 3 }
export const LEVEL_LABEL: Record<Level, string> = {
  normal: 'Nominal',
  attention: 'Watch',
  critical: 'Critical',
  no_data: 'No data',
}
export const LEVEL_COLOR: Record<Level, string> = {
  normal: '#2dd4bf',
  attention: '#fbbf24',
  critical: '#fb7185',
  no_data: '#2a4a50',
}
