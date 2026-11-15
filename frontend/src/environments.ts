// Mission environment -> display name and one-way signal delay to Earth.
// Values come from the API (backend/app/config/environments.json); nothing is hard-coded here.
import { ref } from 'vue'
import { api } from './api'
import type { EnvironmentConfig } from './types'

export interface EnvironmentInfo {
  name: string
  /** Human-readable one-way delay, e.g. "3–22 min one-way". */
  delay: string
  one_way_delay_s: number | null
}

const configs = ref<Record<string, EnvironmentConfig>>({})

/** Fetch the environments once at startup. */
export async function loadEnvironments(): Promise<void> {
  configs.value = (await api.environments()).environments
}

function duration(s: number): string {
  return s < 60 ? `${s} s` : `${Math.round(s / 60)} min`
}

export function delayLabel(c: EnvironmentConfig): string {
  if (c.delay_range_s) {
    const [lo, hi] = c.delay_range_s
    return `${Math.round(lo / 60)}–${Math.round(hi / 60)} min one-way`
  }
  return `${duration(c.one_way_delay_s)} one-way`
}

/** Look up an environment, falling back to its raw key for unknown ones. Reactive. */
export function envFor(key: string): EnvironmentInfo {
  const c = configs.value[key]
  if (!c) return { name: key, delay: '—', one_way_delay_s: null }
  return { name: c.name, delay: delayLabel(c), one_way_delay_s: c.one_way_delay_s }
}
