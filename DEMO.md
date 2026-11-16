# Submission & demo plan

## Submission requirements (from the official Space Apps Project Submission Guide)

Checked against the 2025 guide: https://www.spaceappschallenge.org/resources/project-submission-guide/
→ **Re-check this year's version on your event page before submitting.**

- Every team must provide a **Project Demo**: a **video of up to 30 seconds** OR a **slide deck of up to 7 slides** (title slide included).
- Host it externally (YouTube, Google Drive, GitHub…) with a **public link**; it cannot be uploaded to the Space Apps site.
- **English**: slides must be in English; a video must have English subtitles.
- Show how **space agency data / resources** were used (here: NASA Human Research Program hazards and risks).
- Slides must include: team name, team members, the selected challenge.
- Fill every required field of the project page and tick the submission-requirements box.

## 30-second video script

Story: **the same Critical alert, two different responses**, depending on the distance to Earth
(inspired by NASA's Earth-Independent Medical Operations concept).

| Time | Screen | Voice-over / subtitle |
|---|---|---|
| 0:00–0:03 | Title card | "We're team SpaceMed3. This is Houston Pulse." |
| 0:03–0:07 | Tanaka on the ISS, vital ring all nominal | "Houston Pulse compares every signal with the astronaut's own baseline." |
| 0:07–0:13 | Log 38.4 °C for Tanaka → Critical, "Earth can respond in time" box | "On the ISS, a 38.4 °C fever crosses a CDC threshold. Earth is seconds away: contact the flight surgeon now." |
| 0:13–0:20 | Switch to Moreau, Mars transit → red "Earth cannot respond in time — act on board" panel | "Same alert on the way to Mars: 22 minutes of delay each way. A reply would take an hour, so the crew acts on board." |
| 0:20–0:26 | Tick two steps (times appear) → Send report to Earth → Demo speed ×60, countdown runs | "Monitoring steps, timed and logged, a re-check every 2 hours, and a report on its way to Earth." |
| 0:26–0:30 | SIMULATED reply appears → logo + "Built with NASA Human Research Program resources" | "Monitoring, not diagnosis. Houston Pulse: your mission control, on board." |

Tips: record the real app at 1440 px wide, slow mouse movements, add English subtitles.
Turn on **Demo speed ×60 before** clicking *Send report to Earth*; the full reply countdown then takes
about 1 minute, so cut the wait in editing (keep the "SIMULATED" label visible).

## 7-slide outline

1. **Houston Pulse** — one-line pitch, plus:
   - Team: **SpaceMed3** — Samia Al Yahiaoui, Nourhane Anani, Teddy Emmanuel Kana Boumkwo II
   - Challenge: *Create Health Monitoring Software for Astronauts on Space Missions*
2. **The problem** — 5 hazards of spaceflight (NASA HRP); the farther from Earth, the longer the signal delay (3–22 min one-way to Mars): the crew must manage alone.
3. **Our solution** — screenshot of the vital ring; personal baseline, explained alerts, guidance, documented thresholds.
4. **Same alert, two responses** — side by side: Tanaka on the ISS, 38.4 °C → "contact the flight surgeon now" | Moreau on the way to Mars → Earth-independent mode. Rule: Critical **and** round trip > 10 min.
5. **Earth-independent mode** — screenshot of the panel: onboard monitoring steps with times, re-measure every 2 h, report to Earth with countdown, SIMULATED reply. Inspired by NASA EIMO (sources in the README).
6. **Built responsibly** — every threshold sourced (AHA, NHLBI, ADA, CDC); simulated data clearly labelled; monitoring and communication only: no diagnosis, no medication, no treatment.
7. **Next steps** — radiation dose, SpO₂, exercise, vision (other NASA HRP risks); wearable sensors; real onboard procedures.

## Final checklist

- [ ] `python -m pytest -q` passes in `backend/`
- [ ] `python -m scripts.generate_data` re-run **just before** the demo (from `backend/`): fresh dates, and it erases the 38.4 °C fever logged by hand for Tanaka plus the onboard steps checked and reports sent during rehearsals (the backend only auto-seeds an empty database)
- [ ] App tested on the demo laptop (backend + frontend running)
- [ ] Demo video or slides uploaded, link public, opened in a private window
- [ ] GitHub repo public, README up to date
- [ ] Project page: all fields filled, space agency resources listed, box ticked
