import type { Astronaut, IndicatorMeta, Measurement, StatusResponse, TrendResponse } from './types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Error ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  astronauts: () => request<Astronaut[]>('/astronauts'),
  status: (id: number) => request<StatusResponse>(`/astronauts/${id}/status`),
  indicators: () => request<Record<string, IndicatorMeta>>('/indicators'),
  measurements: (id: number, indicator: string) =>
    request<Measurement[]>(`/astronauts/${id}/measurements?indicator=${encodeURIComponent(indicator)}`),
  trend: (id: number, indicator: string) =>
    request<TrendResponse>(`/astronauts/${id}/trend?indicator=${encodeURIComponent(indicator)}`),
  report: (id: number) => request<Record<string, unknown>>(`/astronauts/${id}/report`),
  addMeasurement: (id: number, indicator: string, value: number) =>
    request<Measurement>(`/astronauts/${id}/measurements`, {
      method: 'POST',
      body: JSON.stringify({ indicator, value }),
    }),
}
