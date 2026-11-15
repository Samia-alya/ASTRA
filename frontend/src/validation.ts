// Plausibility limits for DATA ENTRY (catch typos and impossible values).
// They are NOT medical thresholds and never affect the analysis levels.
// Mirrors backend/app/validation.py; the backend stays the source of truth.
import type { IndicatorMeta } from './types'

const TOLERANCE = 1e-6

/** Limits as written in indicators.json: 0.1 steps keep one decimal (30.0), others as-is (0, 24, 0.25). */
function num(x: number, step: number): string {
  const dec = String(step).split('.')[1]?.length ?? 0
  return dec === 1 ? x.toFixed(1) : String(x)
}

/** Unit after a number; "/5" reads badly ("1–5 /5") so it is left out. */
function unitSuffix(unit: string): string {
  return unit.startsWith('/') ? '' : ` ${unit}`
}

/** "Allowed: 20–250 bpm" */
export function allowedText(meta: IndicatorMeta | undefined): string {
  const i = meta?.input
  if (!meta || !i) return ''
  return `Allowed: ${num(i.min, i.step)}–${num(i.max, i.step)}${unitSuffix(meta.unit)}`
}

/** Error message for a typed value, or '' when it is plausible. */
export function validateValue(meta: IndicatorMeta | undefined, value: number): string {
  if (!meta) return ''
  if (!Number.isFinite(value)) return `${meta.label} must be a finite number.`
  const i = meta.input
  if (!i) return ''
  const unit = unitSuffix(meta.unit)
  if (value < i.min - TOLERANCE || value > i.max + TOLERANCE) {
    return `${meta.label} must be between ${num(i.min, i.step)} and ${num(i.max, i.step)}${unit}.`
  }
  const k = (value - i.min) / i.step
  if (Math.abs(k - Math.round(k)) > TOLERANCE * Math.max(1, Math.abs(k))) {
    return i.step === 1 ? `${meta.label} must be a whole number.` : `${meta.label} must be in steps of ${i.step}${unit}.`
  }
  return ''
}
