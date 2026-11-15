// Must stay in sync with backend/app/models.py and routers/astronauts.py
export type Level = 'normal' | 'attention' | 'critical' | 'no_data'

export interface Astronaut {
  id: number
  name: string
  mission: string
  environment: string
  mission_day: number
  launch_date: string | null
}

export interface Measurement {
  id: number
  astronaut_id: number
  indicator: string
  value: number
  timestamp: string
  source: 'simulated' | 'manual'
}

/** Expected normal in-flight change of an indicator (config/space_adaptation.json). */
export interface Adaptation {
  shift: number
  ramp_days: number
  ramp_basis: string
  summary: string
  source: string
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
  // space-adapted context
  flight_day: number | null
  preflight: number | null
  expected: number | null
  band_low: number | null
  band_high: number | null
  deviation_pct: number | null
  space_adjusted: boolean
  slope_per_day: number | null
  adaptation: Adaptation | null
  // what an Earth-calibrated tool would have said
  earth_level: Level
  earth_reasons: string[]
  earth_false_alarms: number
}

export interface Alert {
  rule: string
  title: string
  level: Level
  indicators: string[]
  blocks_critical_ops: boolean
  explanation: string
  evidence: string[]
  actions: string[]
  sources: string[]
  validation: string
}

export interface Mission {
  flight_day: number
  environment: string
  environment_label: string
  comm_delay: string | null
  one_way_delay_min: [number, number] | null
  autonomy: 'earth_independent' | 'ground_supported'
  comm_source: string | null
  adaptation_model_applies: boolean
}

export interface Readiness {
  status: 'GO' | 'CAUTION' | 'NO_GO'
  label: string
  reasons: string[]
}

export interface StatusResponse {
  astronaut: Astronaut
  mission: Mission
  overall_level: Level
  readiness: Readiness
  alerts: Alert[]
  indicators: IndicatorStatus[]
  disclaimer: string
}

export interface TrendPoint {
  timestamp: string
  flight_day: number | null
  value: number
  source: 'simulated' | 'manual'
  expected: number | null
}

export interface TrendResponse {
  indicator: string
  points: TrendPoint[]
  preflight: number | null
  half_band: number | null
  space_adjusted: boolean
  slope_per_day: number | null
  adaptation: Adaptation | null
  earth_reference_high: number | null
  earth_reference_low: number | null
  critical_high: number | null
  critical_low: number | null
}

export interface IndicatorMeta {
  label: string
  unit: string
  body_zone: string
  what: string
  why_in_space: string
  watch_direction: string
  sources: string[]
}
