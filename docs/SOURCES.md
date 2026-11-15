# Sources and assumptions

Every number the software uses, where it comes from, and what is our own assumption.
Checked online on 14 November 2026. Re-open each link before the final submission.

## Published findings used

| What we use | Value | Source |
|---|---|---|
| Resting core temperature in flight | about +1 °C, developing gradually over 2.5 months | Stahn et al., Scientific Reports 7:16180 (2017). https://pmc.ncbi.nlm.nih.gov/articles/PMC5701078/ |
| Core temperature that can be life-threatening | above 40 °C | Same paper, introduction |
| 24-h ambulatory blood pressure in flight | systolic -8 ± 2, diastolic -9 ± 2 mmHg (8 astronauts, flight days 85-192) | Norsk et al., J Physiol 593:573-584 (2015). https://pmc.ncbi.nlm.nih.gov/articles/PMC4324706/ |
| Sleep in flight | 6.09 h per night on ISS, 5.96 h on Shuttle, for 8.5 h scheduled | Barger et al., Lancet Neurology (2014). https://www.eurekalert.org/news-releases/595450 |
| PVT-B reaction test | 3 minutes, 1-4 s between stimuli, lapse = response of 355 ms or more | Basner, Mollicone & Dinges, Acta Astronautica 69:949-959 (2011). https://pmc.ncbi.nlm.nih.gov/articles/PMC3197786 ; intervals also in https://pmc.ncbi.nlm.nih.gov/articles/PMC3190077 |
| People do not feel their own deficit | under chronic sleep restriction, subjects were largely unaware of increasing cognitive deficits | Van Dongen et al., Sleep 26(2):117-126 (2003). https://ntrs.nasa.gov/citations/20040087752 |
| Latent virus reactivation | herpes viruses reactivated in more than half of Shuttle and ISS crew | Rooney, Crucian, Pierson, Laudenslager & Mehta, Frontiers in Microbiology (2019). https://www.sciencedaily.com/releases/2019/03/190316162211.htm |
| Mars communication delay | 4 to 24 minutes one way | NASA. https://www.nasa.gov/missions/tech-demonstration/space-communications-7-things-you-need-to-know |

## Earth clinical references used as thresholds

| Indicator | Threshold | Source |
|---|---|---|
| Heart rate | attention at 100 bpm at rest (tachycardia) | American Heart Association. https://www.heart.org/svt |
| Blood pressure | attention at 140/90; critical above 180 and/or 120 | American Heart Association. https://heart.org/bplevels |
| Glucose | attention below 70 mg/dL; critical below 54 mg/dL | American Diabetes Association classification of hypoglycemia. https://ada.silverchair.com/view-large/3051584 |
| Temperature | attention at 38 °C (fever); critical above 40 °C | MedlinePlus https://medlineplus.gov/ency/article/003090.htm ; Stahn et al. 2017 |
| Sleep | attention below 6 h | AASM / Sleep Research Society. https://aasm.org/seven-or-more-hours-of-sleep-per-night-a-health-necessity-for-adults/ |

No universally accepted in-flight thresholds exist; these are Earth references.

## Our own assumptions (say so when asked)

- The linear shape of the temperature rise, and the linear onset of the blood-pressure drop up to flight day 85. The sources give the size of the change, not its exact time course.
- Shifting the Earth *reference* values (fever at 38 °C, blood pressure 140/90) by the expected in-flight change. Critical limits are never shifted.
- The statistical rules (2.5 standard deviations; 5-day trend).
- The three cross-indicator rules and their parameters (3 nights below 6 h, heart rate +10%, self-rated alertness of 6 or more).
- The GO / CAUTION / NO-GO logic.
- Every simulated value.

## To verify before citing

- The fever reference is taken from MedlinePlus; add the primary CDC page if you quote "CDC".
- The Barger and Rooney/Mehta figures are quoted from press releases; link the journal articles if time allows.
- The research document gives 2-5 s intervals for the PVT-B; the papers above give 1-4 s. The code uses 1-4 s.
