import type { EnvironmentInfo } from './environments'
import type { IndicatorMeta, IndicatorStatus, StatusResponse } from './types'
import { fmt, LEVEL_LABEL, LEVEL_ORDER } from './types'

export const REPORT_TITLE = 'Houston Pulse — Crew health report'
export const REPORT_FOOTER = 'Simulated data. Monitoring aid, not a medical diagnosis.'

export interface ReportIndicator {
  key: string
  label: string
  value: string
  baseline: string
  level: IndicatorStatus['level']
  levelLabel: string
  reasons: string[]
}

/** Earth-independent mode: onboard steps already checked and when the report was sent. */
export interface OnboardLog {
  actions: { indicator: string; step: string; at: string }[]
  sentAt: string | null
}

export interface ReportSections {
  crew: string
  mission: string
  environment: string
  missionDay: number
  generated: string
  overallLevel: StatusResponse['overall_level']
  overallLabel: string
  flagged: ReportIndicator[]
  others: ReportIndicator[]
  onboard: OnboardLog | null
}

/** "2026-11-14 09:05 UTC" */
export function formatUtc(d: Date): string {
  return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC'
}

function withUnit(value: number | null, unit: string): string {
  return value === null ? '—' : `${fmt(value, unit)} ${unit}`
}

/** Structured report content, shared by the plain-text report and the dialog. */
export function reportSections(
  status: StatusResponse,
  meta: Record<string, IndicatorMeta>,
  env: EnvironmentInfo,
  generatedAt: Date = new Date(),
  onboard: OnboardLog | null = null,
): ReportSections {
  const toItem = (i: IndicatorStatus): ReportIndicator => ({
    key: i.indicator,
    label: meta[i.indicator]?.label ?? i.label,
    value: withUnit(i.value, i.unit),
    baseline: withUnit(i.baseline, i.unit),
    level: i.level,
    levelLabel: LEVEL_LABEL[i.level],
    reasons: i.reasons,
  })
  const isFlagged = (i: IndicatorStatus) => i.level === 'critical' || i.level === 'attention'
  const a = status.astronaut
  return {
    crew: a.name,
    mission: a.mission,
    environment: env.name,
    missionDay: a.mission_day,
    generated: formatUtc(generatedAt),
    overallLevel: status.overall_level,
    overallLabel: LEVEL_LABEL[status.overall_level],
    // Array.prototype.sort is stable, so equal levels keep the API order.
    flagged: status.indicators
      .filter(isFlagged)
      .sort((x, y) => LEVEL_ORDER[x.level] - LEVEL_ORDER[y.level])
      .map(toItem),
    others: status.indicators.filter((i) => !isFlagged(i)).map(toItem),
    onboard,
  }
}

/** Plain-text crew health report, ready to paste into a message to the flight surgeon. */
export function buildReport(
  status: StatusResponse,
  meta: Record<string, IndicatorMeta>,
  env: EnvironmentInfo,
  note: string,
  generatedAt: Date = new Date(),
  onboard: OnboardLog | null = null,
): string {
  const r = reportSections(status, meta, env, generatedAt, onboard)
  const lines: string[] = [
    REPORT_TITLE,
    '',
    `Crew member: ${r.crew}`,
    `Mission: ${r.mission}`,
    `Environment: ${r.environment}`,
    `Mission day: ${r.missionDay}`,
    `Generated: ${r.generated}`,
    `Overall level: ${r.overallLabel}`,
    '',
    'Flagged indicators',
  ]
  if (!r.flagged.length) {
    lines.push('All indicators nominal.')
  } else {
    for (const f of r.flagged) {
      lines.push(`- ${f.label}: ${f.value} (personal baseline ${f.baseline}) — ${f.levelLabel}`)
      for (const reason of f.reasons) lines.push(`    • ${reason}`)
    }
  }
  lines.push('', 'Other indicators')
  for (const o of r.others) lines.push(`- ${o.label}: ${o.value}`)
  if (r.onboard) {
    lines.push('', 'Onboard actions (Earth-independent mode)')
    if (!r.onboard.actions.length) lines.push('No onboard step checked yet.')
    for (const a of r.onboard.actions) lines.push(`- ${a.at} · ${a.indicator}: ${a.step}`)
    if (r.onboard.sentAt) lines.push(`Sent to Earth: ${r.onboard.sentAt}`)
  }
  const trimmed = note.trim()
  if (trimmed) lines.push('', 'Note from crew member', trimmed)
  lines.push('', REPORT_FOOTER)
  return lines.join('\n')
}
