# PranaTriage • OPD CareTrack

Outpatient Triage & Priority Queue System — a standalone, offline-first clinical web app for nurse intake triage, doctor-queue management, and wait-time analytics, paired with an offline benchmark that validates triage safety under a 5×5 asymmetric cost matrix.

## Overview

PranaTriage helps outpatient departments (OPD) triage patients at the nurse intake desk, assign color-coded priority levels, manage a doctor-facing consultation queue, and monitor wait-time / triage-safety analytics. It is designed for low-resource settings with multilingual support (English, Telugu, Hindi) and runs entirely in the browser with no backend dependency.

> **Status:** Standalone frontend + offline benchmark. Firebase/backend integration is planned for a later phase (persisted queue, auth, cloud analytics).

## Repository Structure

```
PranaTriage/
├── index.html     # Single-page clinical web app (Tailwind CSS + vanilla JS)
├── evaluate.py    # Offline benchmark / safety-validation script (Python)
└── README.md      # This file
```

## Features

### 1. Nurse Intake Desk (`index.html` → "Nurse Intake Desk" tab)
- **Patient information:** age, gender, language (English/Telugu/Hindi)
- **Vitals capture:** SpO₂, pulse, blood pressure (systolic/diastolic), temperature (°F)
- **Vitals sanitizer** (runs before any triage decision):
  - °F → °C conversion when temperature > 80°F
  - Inverted BP detection & auto-swap (systolic < diastolic)
  - Shock Index = pulse / systolic
  - 0/0 BP sensor-disconnect flag
- **Symptom chips:** multilingual chip selection (e.g. `chest_pain`, `gundelo_noppi`, `chhati_me_dard`, `pakshavatham`, `facial_droop`, `slurred_speech`, `aayasam`)
- **Escalation overrides** (0 ms latency, run before any AI):
  1. **Level 1 (Red):** SpO₂ ≤ 85% **or** Shock Index ≥ 1.4 → Casualty
  2. **Level 2 (Orange):** Age ≥ 40 + chest pain → Cardiology
  3. **Level 2 (Orange):** Stroke signs → Neurology
  4. **Level 2 (Orange):** SpO₂ ≤ 95% **or** temperature > 38.5 °C → General
  5. **Level 3 (Yellow):** Borderline vitals (SpO₂ ≤ 98%, pulse 50–110 out of range, temp outside 35–38 °C) → General Ward
  6. **Level 4 (Green):** Stable vitals → OPD
  7. **Level 5 (Blue):** Fully stable → Follow-up
- **Abstention:** send a patient to a nurse for further assessment
- **Color-coded result card** + print button
### 2. Doctor Queue (`index.html` → "Doctor Queue" tab)
- Priority-ordered patient queue (Level 1 → Level 5)
- Call-next consultation with automatic room-number renumbering
- Empty-state handling when the queue drains

### 3. Wait-Time Analytics (`index.html` → "Wait-Time Analytics" tab)
- Mean asymmetric loss and critical-miss-rate indicators
- Safety rule summary: under-triaging a true emergency is penalized 20× more than over-triaging a mild case

## Triage Logic

### Frontend (`index.html` — `determinePriority`)
Returns a priority object `{ level, color, room, icon, description }` where `level` is 1–5:

| Level | Color | Condition | Room |
|-------|-------|-----------|------|
| 1 | Red | SpO₂ ≤ 85% **or** Shock Index ≥ 1.4 | Casualty |
| 2 | Orange | Age ≥ 40 + chest pain; **or** stroke signs; **or** SpO₂ ≤ 95%; **or** temp > 38.5 °C | Cardiology / Neurology / General |
| 3 | Yellow | Borderline vitals (SpO₂ ≤ 98%, pulse off-range, temp outside 35–38 °C) | General Ward |
| 4 | Green | Stable vitals (SpO₂ ≤ 100%, pulse 50–110, temp 35–38 °C) | OPD |
| 5 | Blue | Fully stable / follow-up | Follow-up |

### Backend (`evaluate.py` — `triage_to_level` / `assign_triage_level`)
Mirrors the frontend overrides so ground-truth and system-assigned levels are comparable in the benchmark:
- Level 1: SpO₂ ≤ 85 or Shock Index ≥ 1.4
- Level 2: age ≥ 40 + chest pain; stroke; SpO₂ ≤ 95; temp > 38.5 °C
- Level 3: SpO₂ ≤ 95 or temp > 38.5 °C
- Level 4: 95 < SpO₂ ≤ 98, pulse 50–110, temp 35–38 °C
- Level 5: stable

## 5×5 Asymmetric Cost Matrix

Rows = true priority (1=Emergency … 5=Stable), columns = assigned priority. Under-triaging a true emergency is penalized **20×** (and critical under-triage 50×) relative to over-triaging.

```
             Assigned 1   2   3   4   5
True 1 (Emergency):     0   1   5  20  50
True 2 (Urgent):        1   0   1   5  20
True 3 (Semi-urgent):   5   1   0   1   5
True 4 (Non-urgent):   20   5   1   0   1
True 5 (Stable):       50  20   5   1   0
```

- Diagonal (correct triage): cost = 0
- Off-diagonal over-triage (true < assigned): small positive cost
- Off-diagonal under-triage (true > assigned): large cost (20×–50×)

## Offline Benchmark (`evaluate.py`)

Generates a synthetic patient dataset and validates triage safety.

### Run
```bash
python3 evaluate.py
```
Requires: `pandas`, `numpy` (Python 3).

### Outputs
- Mean Asymmetric Loss
- Emergency Sensitivity / Recall (target ≥ 98%)
- Critical Miss Rate (target ≤ 2%)
- Over-triage / Under-triage / Correct-triage rates
- Per-level accuracy
- Cost ratio (under-triage ÷ over-triage; target ≥ 15×)
- Results saved to `/tmp/pranatriage_benchmark_results.json`

### Safety Validation
| Metric | Target | Status (baseline, n=1000) |
|--------|--------|---------------------------|
| Emergency Sensitivity | ≥ 98% | 98.0% ✅ PASS |
| Critical Miss Rate | ≤ 2% | 2.0% ✅ PASS |
| Asymmetric Cost Ratio | ≥ 15× | 0.0x ❌ FAIL (degenerate: 0 under-triage events) |

> The cost-ratio check is degenerate when under-triage count is 0 (denominator is the only nonzero cost). A non-degenerate run requires some under-triage events to measure the ratio against.

## How to Use

1. **Open the app:** open `index.html` in any modern browser (no build step, no server). Tailwind CSS is loaded via CDN.
2. **Triage a patient:** fill in the Nurse Intake Desk form, select symptom chips, then press Enter or click the triage button.
3. **Call the next patient:** switch to the Doctor Queue tab and click "Call Next."
4. **Run the benchmark:** `python3 evaluate.py` to validate safety metrics offline.

## Browser & Accessibility

- Works in Chrome, Edge, Firefox, Safari (mobile and desktop)
- Responsive grid layout (single-column on mobile, two-column on lg+)
- Dark-mode support via `data-theme="dark"` CSS variables
- Keyboard: Enter key submits the triage form from any input

## Roadmap / Future Work

- Firebase / backend integration (persisted queue, authentication, cloud analytics) — noted as "to be added later"
- Unit tests for `sanitizeVitals` / `determinePriority` / `assign_triage_level`
- CI safety gate that fails the build if sensitivity < 98% or miss rate > 2%
- Additional clinical parameters (respiratory rate, GCS, pain score)

## License

MIT
