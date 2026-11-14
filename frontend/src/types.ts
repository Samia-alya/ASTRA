// Must stay in sync with backend/app/models.py and routers/astronauts.py
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

export interface StatusResponse {
  astronaut: Astronaut
  overall_level: Level
  indicators: IndicatorStatus[]
  disclaimer: string
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
