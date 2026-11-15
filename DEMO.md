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

| Time | Screen | Voice-over / subtitle |
|---|---|---|
| 0:00–0:04 | Title card | "We're team [TEAM NAME]. This is Houston Pulse." |
| 0:04–0:09 | Rivera on the lunar base, vital ring | "Far from Earth, astronauts must spot health changes themselves. Houston Pulse compares every signal with *their own* baseline." |
| 0:09–0:15 | Click the Sleep arc → chart + reasons | "Day 87: Rivera's sleep is slipping and resting heart rate is up. The app says why, and what to do now." |
| 0:15–0:22 | Switch to Moreau, Mars transit, Critical | "On the way to Mars, a 38.4 °C fever crosses a documented CDC threshold: contact the flight surgeon — with a 22-minute signal delay." |
| 0:22–0:27 | Log a measurement → ring updates | "Every alert is explained, sourced, and never presented as a diagnosis." |
| 0:27–0:30 | Logo + "Built with NASA Human Research Program resources" | "Houston Pulse: your mission control, on board." |

Tips: record the real app at 1440 px wide, slow mouse movements, add English subtitles.

## 7-slide outline

1. **Houston Pulse** — team name, members, challenge name, one-line pitch.
2. **The problem** — 5 hazards of spaceflight (NASA HRP); long missions = astronauts assess their own health, far from Earth.
3. **Our solution** — screenshot of the vital ring; personal baseline, explained alerts, guidance.
4. **How it works** — data → personal baseline + trend → documented thresholds → Nominal / Watch / Critical with reasons.
5. **Demo story** — Tanaka (nominal), Rivera (watch: sleep, mood, heart rate), Moreau (critical: fever on a Mars transit).
6. **Built responsibly** — every threshold sourced (AHA, NHLBI, ADA, CDC); simulated data clearly labelled; not a diagnosis.
7. **Next steps** — radiation dose, SpO₂, exercise, vision (other NASA HRP risks); wearable sensors.

## Final checklist

- [ ] `python -m pytest -q` passes in `backend/`
- [ ] `python -m scripts.generate_data` run just before the demo (fresh dates)
- [ ] App tested on the demo laptop (backend + frontend running)
- [ ] Demo video or slides uploaded, link public, opened in a private window
- [ ] GitHub repo public, README up to date
- [ ] Project page: all fields filled, space agency resources listed, box ticked
