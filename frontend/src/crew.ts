// Which figure the vital ring shows for each crew member of the SIMULATED demo crew.
// Front-end only for now: the astronaut profile in the database has no such field yet.
// Unknown names get the neutral figure.
import type { BodyBuild } from './components/body/humanoid'

const CREW_BUILD: Record<string, BodyBuild> = {
  'Cmdr. A. Rivera': 'female',
  'Dr. K. Tanaka': 'male',
  'Eng. L. Moreau': 'female',
}

export function buildFor(name: string | undefined): BodyBuild {
  return (name && CREW_BUILD[name]) || 'neutral'
}
