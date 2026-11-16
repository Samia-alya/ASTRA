// Body parts shown on the vital ring silhouette. General information only, no medical advice.
// Space context: NASA Human Research Program, https://www.nasa.gov/hrp/risks/
// (listed with every other reference in the footer "Sources" dialog, see sources.ts)

export interface BodyZone {
  key: string
  name: string
  /** Short name for buttons. */
  short: string
  function: string
  inSpace: string
  /** false = shown for information only, no indicator in this prototype. */
  monitored: boolean
}

export const BODY_ZONES: Record<string, BodyZone> = {
  brain: {
    key: 'brain', name: 'Brain & mind', short: 'Brain', monitored: true,
    function: 'Controls thinking, mood and the sleep–wake cycle.',
    inSpace: "NASA's Human Research Program lists behavioral changes and inadequate sleep / irregular schedules among spaceflight risks, driven by isolation, confinement and distance from Earth.",
  },
  eyes: {
    key: 'eyes', name: 'Eyes', short: 'Eyes', monitored: false,
    function: 'Capture light and send images to the brain.',
    inSpace: 'The structure of the eyes and brain can change during spaceflight (NASA HRP: Spaceflight Associated Neuro-ocular Syndrome, SANS).',
  },
  head: {
    key: 'head', name: 'Body temperature', short: 'Temperature', monitored: true,
    function: 'Body temperature reflects how the body regulates heat, and can rise when fighting an infection.',
    inSpace: 'NASA HRP lists altered immune responses: the stress of spaceflight can reactivate dormant viruses.',
  },
  heart: {
    key: 'heart', name: 'Heart & blood vessels', short: 'Heart', monitored: true,
    function: 'Pumps blood to deliver oxygen and nutrients to the whole body.',
    inSpace: 'Weightlessness changes blood circulation and how the heart and blood vessels work (NASA HRP: cardiovascular adaptations).',
  },
  abdomen: {
    key: 'abdomen', name: 'Metabolism & nutrition', short: 'Metabolism', monitored: true,
    function: 'Digestion turns food into energy; blood glucose shows how much sugar is available in the blood.',
    inSpace: 'A balanced diet is essential on long missions (NASA HRP: inadequate food and nutrition).',
  },
  bones: {
    key: 'bones', name: 'Bones & muscles', short: 'Bones & muscles', monitored: false,
    function: 'Support the body, protect organs and, with muscles, allow movement.',
    inSpace: 'Without gravity, bones lose density and become more brittle; astronauts exercise daily to limit bone and muscle loss (NASA HRP).',
  },
}

/** Display order, top to bottom. */
export const ZONE_ORDER = ['brain', 'eyes', 'head', 'heart', 'abdomen', 'bones']
