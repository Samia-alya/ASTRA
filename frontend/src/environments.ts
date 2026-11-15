// Mission environment -> display name and one-way signal delay to Earth.
export interface EnvironmentInfo {
  name: string
  delay: string
}

export const ENVIRONMENTS: Record<string, EnvironmentInfo> = {
  station: { name: 'Low Earth orbit', delay: 'near real-time' },
  lunar_base: { name: 'Lunar base', delay: '1.3 s one-way' },
  mars_transit: { name: 'Mars transit', delay: '3–22 min one-way' },
}

/** Look up an environment, falling back to its raw key for unknown ones. */
export function envFor(key: string): EnvironmentInfo {
  return ENVIRONMENTS[key] ?? { name: key, delay: '—' }
}
