// Every reference used in the app, for the "Sources" dialog in the footer.
// The URLs mirror the backend config (thresholds.json, devices.json, environments.json) and
// bodyZones.ts: keep them in sync there, never add a source that the app does not use.

export interface SourceLink {
  label: string
  detail: string
  url: string
}

export interface SourceGroup {
  title: string
  items: SourceLink[]
}

export const SOURCE_GROUPS: SourceGroup[] = [
  {
    title: 'Space context',
    items: [
      { label: 'NASA Human Research Program', detail: 'Spaceflight hazards and risks, including distance from Earth, isolation, sleep, immune and cardiovascular changes', url: 'https://www.nasa.gov/hrp/risks/' },
      { label: 'NASA NSSDCA Mars Fact Sheet', detail: 'Earth–Mars distance, used for the 3–22 min one-way signal delay', url: 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html' },
      { label: 'NASA NSSDCA Moon Fact Sheet', detail: 'Earth–Moon distance, used for the 1.3 s one-way signal delay', url: 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html' },
      { label: 'Canadian Space Agency — Bio-Monitor', detail: 'Smart shirt that the simulated shirt is modeled on', url: 'https://www.asc-csa.gc.ca/eng/sciences/bio-monitor.asp' },
      { label: 'NASA — Artemis II crew health research', detail: 'Actigraphy wrist monitors that the simulated sleep band is modeled on', url: 'https://www.nasa.gov/humans-in-space/artemis-ii-crew-to-advance-human-spaceflight-research/' },
    ],
  },
  {
    title: 'Medical thresholds',
    items: [
      { label: 'American Heart Association — heart rate', detail: 'Normal resting range 60–100 bpm', url: 'https://www.heart.org/en/health-topics/high-blood-pressure/the-facts-about-high-blood-pressure/all-about-heart-rate-pulse' },
      { label: 'American Heart Association — blood pressure', detail: 'Hypertensive crisis above 180/120 mm Hg', url: 'https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings' },
      { label: 'NHLBI — low blood pressure', detail: 'Lower than 90/60 mm Hg', url: 'https://www.nhlbi.nih.gov/health/low-blood-pressure' },
      { label: 'American Diabetes Association — hyperglycemia', detail: 'Above 240 mg/dL, check for ketones', url: 'https://diabetes.org/living-with-diabetes/treatment-care/hyperglycemia' },
      { label: 'ADA / EASD, Diabetes Care 2017', detail: 'Below 54 mg/dL, level 2 hypoglycemia', url: 'https://doi.org/10.2337/dc16-2215' },
      { label: 'CDC — fever', detail: 'Measured temperature of at least 38 °C', url: 'https://www.cdc.gov/port-health/php/definitions-symptoms-reportable-illness/index.html' },
      { label: 'CDC — hypothermia', detail: 'Below 35 °C is an emergency', url: 'https://www.cdc.gov/winter-weather/prevention/index.html' },
    ],
  },
  {
    title: 'Sleep',
    items: [
      { label: 'CDC / AASM', detail: 'Adults need at least 7 hours of sleep per night', url: 'https://archive.cdc.gov/www_cdc_gov/media/releases/2016/p0215-enough-sleep.html' },
    ],
  },
]
