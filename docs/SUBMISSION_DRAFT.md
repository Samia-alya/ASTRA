# Space Apps submission draft (edit before posting)

Field names follow the 2025 project submission guide; check the 2026 form.
The page and linked material must be in English.

## High-level project summary

AstroVitals is health monitoring software for astronauts on long missions. A healthy body in weightlessness settles on values that tools calibrated on Earth read as illness: resting core temperature about 1 °C higher, blood pressure 8-10 mmHg lower. AstroVitals learns each astronaut's own baseline, removes the expected in-flight change before judging a value, and only alerts on what adaptation does not explain. It adds a 3-minute reaction test (PVT-B) and compares it with how alert the astronaut says they feel, catching fatigue the person does not notice. Several weak signals are combined into one explained alert with suggested next steps and sources, and a GO / CAUTION / NO-GO status for critical operations. Because a question from Mars takes 8 to 48 minutes to come back answered, guidance is written to be acted on by the crew, and a report can be exported for Mission Control.

## Seven-slide outline

1. Title: team name, members, challenge.
2. The problem: Earth-calibrated tools cry wolf in space (38 °C is normal at flight day 100).
3. Our answer: the space-adapted baseline (temperature chart with the expected band).
4. Masked fatigue: feeling alert vs. the reaction test (screenshot of the alert).
5. Live product: dashboard with GO / NO-GO and explained alerts.
6. Validity: what is published, what is our assumption, what is simulated.
7. What is next: real data (NASA OSDR), partial gravity, hardware inputs.

## 30-second video script

- 0-5 s: "On day 100 in orbit, a healthy astronaut runs at 38 °C. Earth software calls it a fever. Every day."
- 5-15 s: Temperature chart: the expected band rises; "AstroVitals knows what is normal in space."
- 15-24 s: Reaction test, then the alert: "You feel alert. Your reaction time disagrees." NO-GO appears.
- 24-30 s: "Mars is up to 24 minutes away. AstroVitals helps the crew decide now." Team name.

## NASA data and resources

- NASA Human Research Program hazards and risks (framing of the indicators).
- NASA-funded and NASA co-authored studies used to build the adaptation model and rules: Stahn et al. 2017 (core temperature, with NASA JSC authors), Barger et al. 2014 (sleep in flight), Basner, Mollicone & Dinges 2011 (PVT-B), Van Dongen et al. 2003 (NASA NTRS record), Rooney, Crucian, Mehta et al. 2019 (virus reactivation).
- NASA communications figures for the Mars delay.
- State clearly: all astronaut values in the demo are simulated. If time allows, add one real NASA Open Science Data Repository dataset (for example the Inspiration4 metabolic panel) to calibrate a range, and list it here.

## Space agency partner and other data

- Norsk et al. 2015 (blood pressure on the ISS). Clinical references: American Heart Association, American Diabetes Association, AASM, U.S. National Library of Medicine.

## Use of artificial intelligence

State where and how AI was used. To adapt to what your team actually did:
- A research document was compiled with an AI research tool; the figures used in the software were then checked against the original sources (docs/SOURCES.md).
- Parts of the code, the documentation and this draft were written with an AI coding assistant (Claude) and reviewed by the team.
- No AI-generated image, audio or video is used. (Add watermarks if that changes.)
