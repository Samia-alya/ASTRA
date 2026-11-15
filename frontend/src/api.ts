import type {
  Astronaut, AutonomyResponse, ChecksResponse, EnvironmentConfig, IndicatorMeta, Measurement, StatusResponse,
} from './types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (res.status === 204) return undefined as T
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Error ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  astronauts: () => request<Astronaut[]>('/astronauts'),
  status: (id: number) => request<StatusResponse>(`/astronauts/${id}/status`),
  checks: (id: number) => request<ChecksResponse>(`/astronauts/${id}/checks`),
  indicators: () => request<Record<string, IndicatorMeta>>('/indicators'),
  measurements: (id: number, indicator: string) =>
    request<Measurement[]>(`/astronauts/${id}/measurements?indicator=${encodeURIComponent(indicator)}`),
  addMeasurement: (id: number, indicator: string, value: number) =>
    request<Measurement>(`/astronauts/${id}/measurements`, {
      method: 'POST',
      body: JSON.stringify({ indicator, value }),
    }),
  environments: () => request<{ environments: Record<string, EnvironmentConfig> }>('/environments'),
  autonomy: (id: number) => request<AutonomyResponse>(`/astronauts/${id}/autonomy`),
  setStep: (id: number, indicator: string, step: number, checked: boolean) =>
    request<unknown>(`/astronauts/${id}/autonomy/actions/${encodeURIComponent(indicator)}/${step}`, {
      method: checked ? 'PUT' : 'DELETE',
    }),
  sendReport: (id: number) =>
    request<{ report_sent_at: string }>(`/astronauts/${id}/autonomy/report`, { method: 'POST' }),
}
