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
  source: 'simulated' | 'manual'
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
}

/** Earth-independent mode block (backend/app/analysis/autonomy.py). */
export interface AutonomyState {
  active: boolean
  one_way_delay_s: number
  /** 2 × one-way delay + assumed ground response time. */
  earliest_reply_s: number
  reason: string
}

export interface StatusResponse {
  astronaut: Astronaut
  overall_level: Level
  indicators: IndicatorStatus[]
  autonomy: AutonomyState
  disclaimer: string
}

export interface AutonomyStep {
  index: number
  text: string
  checked_at: string | null
}

export interface AutonomyResponse {
  autonomy: AutonomyState
  groups: { indicator: string; label: string; steps: AutonomyStep[] }[]
  report_sent_at: string | null
}

export interface EnvironmentConfig {
  name: string
  one_way_delay_s: number
  delay_range_s?: [number, number]
  source: string
}

export interface CheckItem {
  indicator: string
  label: string
  unit: string
  done: boolean
  last_timestamp: string | null
  hours_since_last: number | null
  /** Only on indicators re-measured more often in Earth-independent mode. */
  interval_hours?: number
  next_due_in_s?: number
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
  autonomy_steps?: string[]
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
