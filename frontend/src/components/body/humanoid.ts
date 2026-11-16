/**
 * Procedural human figure for the holographic view.
 *
 * The body is one continuous surface: a signed distance field made of rounded
 * limbs and ellipsoids blended together (smooth union), then turned into a mesh
 * with marching cubes. No external model file is needed.
 *
 * Coordinates: y up, the figure faces +z, its left side is +x. Height is about
 * 1.9 units (feet at y = -0.95, top of the head at y = +0.93). Arms are held
 * away from the body so every zone stays visible while it rotates.
 */
import { MarchingCubes } from 'three/examples/jsm/objects/MarchingCubes.js'
import type { Material } from 'three'

/** Half-extent of the sampled volume on each axis (the figure is tall and thin). */
export const BODY_SCALE = { x: 0.66, y: 1.0, z: 0.22 }

// [cx, cy, cz, rx, ry, rz]
type Ellipsoid = [number, number, number, number, number, number]
// [ax, ay, az, bx, by, bz, ra, rb]
type Limb = [number, number, number, number, number, number, number, number]

// Defined for the left half only (x >= 0); the field is mirrored with |x|.
const ELLIPSOIDS: Ellipsoid[] = [
  [0, 0.835, 0.01, 0.078, 0.1, 0.088],    // skull
  [0, 0.775, 0.03, 0.055, 0.05, 0.056],   // jaw
  [0, 0.53, 0.0, 0.165, 0.15, 0.105],     // chest
  [0, 0.37, 0.005, 0.135, 0.13, 0.09],    // abdomen
  [0, 0.23, 0.0, 0.16, 0.1, 0.1],         // pelvis
  [0.585, 0.3, 0.02, 0.05, 0.045, 0.02],  // hand
  [0.108, -0.48, -0.02, 0.048, 0.11, 0.05], // calf
]
const LIMBS: Limb[] = [
  [0, 0.69, 0, 0, 0.77, 0.005, 0.045, 0.042],             // neck
  [0, 0.635, 0, 0.19, 0.625, 0, 0.06, 0.055],             // shoulder line
  [0.205, 0.615, 0, 0.38, 0.47, -0.005, 0.052, 0.04],     // upper arm (arms held away from the body)
  [0.38, 0.47, -0.005, 0.54, 0.335, 0.015, 0.041, 0.027], // forearm
  [0.098, 0.17, 0, 0.108, -0.33, 0.01, 0.078, 0.054],     // thigh
  [0.108, -0.33, 0.01, 0.11, -0.85, -0.005, 0.053, 0.034], // shin
  [0.11, -0.9, -0.01, 0.118, -0.92, 0.12, 0.036, 0.026],  // foot
]
const BLEND = 0.022

function smin(a: number, b: number, k: number): number {
  const h = Math.max(k - Math.abs(a - b), 0) / k
  return Math.min(a, b) - h * h * k * 0.25
}

function sdEllipsoid(x: number, y: number, z: number, e: Ellipsoid): number {
  const px = x - e[0], py = y - e[1], pz = z - e[2]
  const k0 = Math.hypot(px / e[3], py / e[4], pz / e[5])
  const k1 = Math.hypot(px / (e[3] * e[3]), py / (e[4] * e[4]), pz / (e[5] * e[5]))
  return k1 > 1e-9 ? (k0 * (k0 - 1)) / k1 : -Math.min(e[3], e[4], e[5])
}

/** Capsule with a different radius at each end (after Inigo Quilez's round cone). */
function sdLimb(x: number, y: number, z: number, l: Limb): number {
  const bax = l[3] - l[0], bay = l[4] - l[1], baz = l[5] - l[2]
  const r1 = l[6], r2 = l[7]
  const l2 = bax * bax + bay * bay + baz * baz
  const rr = r1 - r2
  const a2 = l2 - rr * rr
  const il2 = 1 / l2
  const pax = x - l[0], pay = y - l[1], paz = z - l[2]
  const yy = pax * bax + pay * bay + paz * baz
  const zz = yy - l2
  const qx = pax * l2 - bax * yy, qy = pay * l2 - bay * yy, qz = paz * l2 - baz * yy
  const x2 = qx * qx + qy * qy + qz * qz
  const y2 = yy * yy * l2
  const z2 = zz * zz * l2
  const k = Math.sign(rr) * rr * rr * x2
  if (Math.sign(zz) * a2 * z2 > k) return Math.sqrt(x2 + z2) * il2 - r2
  if (Math.sign(yy) * a2 * y2 < k) return Math.sqrt(x2 + y2) * il2 - r1
  return (Math.sqrt(x2 * a2 * il2) + yy * rr) * il2 - r1
}

/** Signed distance to the body surface (negative inside). */
export function bodyDistance(x: number, y: number, z: number): number {
  const ax = Math.abs(x)
  let d = 1e9
  for (const e of ELLIPSOIDS) d = smin(d, sdEllipsoid(ax, y, z, e), BLEND)
  for (const l of LIMBS) d = smin(d, sdLimb(ax, y, z, l), BLEND)
  return d
}

/** Builds the body mesh at the given grid resolution. */
export function buildBody(resolution: number, material: Material, maxPolys: number): MarchingCubes {
  const mc = new MarchingCubes(resolution, material, false, false, maxPolys)
  mc.isolation = 0
  const n = resolution, half = n / 2
  const field = mc.field
  let i = 0
  for (let zi = 0; zi < n; zi++) {
    const z = ((zi - half) / half) * BODY_SCALE.z
    for (let yi = 0; yi < n; yi++) {
      const y = ((yi - half) / half) * BODY_SCALE.y
      for (let xi = 0; xi < n; xi++) {
        const x = ((xi - half) / half) * BODY_SCALE.x
        field[i++] = -bodyDistance(x, y, z)   // marching cubes expects "inside" to be higher
      }
    }
  }
  mc.update()
  mc.scale.set(BODY_SCALE.x, BODY_SCALE.y, BODY_SCALE.z)
  mc.frustumCulled = false
  return mc
}
