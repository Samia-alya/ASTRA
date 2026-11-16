/**
 * Procedural human figure for the holographic view.
 *
 * The body is one continuous surface: a signed distance field made of rounded
 * limbs and ellipsoids blended together (smooth union), then turned into a mesh
 * with marching cubes. No external model file is needed.
 *
 * Coordinates: y up, the figure faces +z, its left side is +x. Height is about
 * 1.9 units (feet at y = -0.95, top of the head at y = +0.93).
 */
import { MarchingCubes } from 'three/examples/jsm/objects/MarchingCubes.js'
import type { Material } from 'three'

/** Half-extent of the sampled volume on each axis (the figure is tall and thin). */
export const BODY_SCALE = { x: 0.4, y: 1.0, z: 0.22 }

// [cx, cy, cz, rx, ry, rz]
type Ellipsoid = [number, number, number, number, number, number]
// [ax, ay, az, bx, by, bz, ra, rb]
type Limb = [number, number, number, number, number, number, number, number]

export type BodyBuild = 'male' | 'female' | 'neutral'

// Shapes are defined for the left half only (x >= 0); the field is mirrored with |x|.
// Three builds share the same height and pose, so hotspots stay in place.
interface Build { ellipsoids: Ellipsoid[]; limbs: Limb[] }

// Limbs and extremities for a given shoulder position, arm thickness, hip position and thigh radius.
// Arms hang relaxed, slightly away from the body.
const LIMBS_FOR = (shoulderX: number, arm: number, hipX: number, thigh: number): Limb[] => [
  [shoulderX, 0.615, 0, shoulderX + 0.045, 0.36, -0.005, 0.05 * arm, 0.04 * arm],                // upper arm
  [shoulderX + 0.045, 0.36, -0.005, shoulderX + 0.085, 0.125, 0.02, 0.04 * arm, 0.027 * arm],    // forearm
  [hipX, 0.17, 0, 0.1, -0.33, 0.01, thigh, 0.054],                                               // thigh
  [0.1, -0.33, 0.01, 0.102, -0.85, -0.005, 0.053, 0.034],                                        // shin
  [0.102, -0.9, -0.01, 0.11, -0.92, 0.12, 0.036, 0.026],                                         // foot
]
const EXTREMITIES = (shoulderX: number): Ellipsoid[] => [
  [0, 0.835, 0.01, 0.078, 0.1, 0.088],                    // skull
  [0, 0.775, 0.03, 0.055, 0.05, 0.056],                   // jaw
  [shoulderX + 0.093, 0.04, 0.03, 0.026, 0.065, 0.02],    // hand
  [0.1, -0.48, -0.02, 0.048, 0.11, 0.05],                 // calf
]

// Standard adult proportions (about 8 head-heights tall). Male and female differ only modestly:
// shoulder width about 23% vs 21% of height, hips about 18% vs 19.5%, a slightly narrower waist.
const BUILDS: Record<BodyBuild, Build> = {
  neutral: {
    ellipsoids: [...EXTREMITIES(0.175),
      [0, 0.53, 0.0, 0.145, 0.15, 0.1],     // chest
      [0, 0.37, 0.005, 0.12, 0.13, 0.086],  // abdomen
      [0, 0.23, 0.0, 0.155, 0.1, 0.1],      // pelvis
    ],
    limbs: [
      [0, 0.69, 0, 0, 0.77, 0.005, 0.043, 0.04],     // neck
      [0, 0.635, 0, 0.155, 0.625, 0, 0.055, 0.05],   // shoulder line
      ...LIMBS_FOR(0.175, 0.94, 0.092, 0.078),
    ],
  },
  male: {
    ellipsoids: [...EXTREMITIES(0.188),
      [0, 0.53, 0.0, 0.152, 0.15, 0.104],   // chest
      [0, 0.37, 0.005, 0.126, 0.13, 0.09],  // abdomen
      [0, 0.23, 0.0, 0.15, 0.098, 0.098],   // pelvis
    ],
    limbs: [
      [0, 0.69, 0, 0, 0.77, 0.005, 0.046, 0.043],    // neck
      [0, 0.637, 0, 0.168, 0.627, 0, 0.057, 0.053],  // shoulder line
      ...LIMBS_FOR(0.188, 1, 0.09, 0.077),
    ],
  },
  female: {
    ellipsoids: [...EXTREMITIES(0.162),
      [0, 0.53, 0.0, 0.136, 0.145, 0.094],       // chest
      [0.056, 0.545, 0.064, 0.04, 0.04, 0.034],  // bust
      [0, 0.375, 0.005, 0.112, 0.125, 0.082],    // abdomen
      [0, 0.228, 0.0, 0.162, 0.103, 0.101],      // pelvis
    ],
    limbs: [
      [0, 0.69, 0, 0, 0.77, 0.005, 0.04, 0.038],     // neck
      [0, 0.633, 0, 0.143, 0.623, 0, 0.051, 0.046],  // shoulder line
      ...LIMBS_FOR(0.162, 0.88, 0.095, 0.08),
    ],
  },
}
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
export function bodyDistance(x: number, y: number, z: number, build: BodyBuild = 'neutral'): number {
  const { ellipsoids, limbs } = BUILDS[build]
  const ax = Math.abs(x)
  let d = 1e9
  for (const e of ellipsoids) d = smin(d, sdEllipsoid(ax, y, z, e), BLEND)
  for (const l of limbs) d = smin(d, sdLimb(ax, y, z, l), BLEND)
  return d
}

/** Builds the body mesh at the given grid resolution. */
export function buildBody(resolution: number, material: Material, maxPolys: number, build: BodyBuild = 'neutral'): MarchingCubes {
  const mc = new MarchingCubes(resolution, material, false, false, maxPolys)
  mc.isolation = 0
  const n = resolution, half = n / 2
  // Sampling the field is the slow part (about half a second): keep it per build and resolution,
  // so switching back to a crew member already seen is instant.
  const key = `${build}:${resolution}`
  const cached = FIELD_CACHE.get(key)
  if (cached) {
    mc.field.set(cached)
    return finish(mc)
  }
  const field = mc.field
  let i = 0
  for (let zi = 0; zi < n; zi++) {
    const z = ((zi - half) / half) * BODY_SCALE.z
    for (let yi = 0; yi < n; yi++) {
      const y = ((yi - half) / half) * BODY_SCALE.y
      for (let xi = 0; xi < n; xi++) {
        const x = ((xi - half) / half) * BODY_SCALE.x
        field[i++] = -bodyDistance(x, y, z, build)   // marching cubes expects "inside" to be higher
      }
    }
  }
  FIELD_CACHE.set(key, field.slice())
  return finish(mc)
}

const FIELD_CACHE = new Map<string, Float32Array>()

function finish(mc: MarchingCubes): MarchingCubes {
  mc.update()
  mc.scale.set(BODY_SCALE.x, BODY_SCALE.y, BODY_SCALE.z)
  mc.frustumCulled = false
  return mc
}
