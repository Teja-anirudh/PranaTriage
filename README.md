# PranaTriage • OPD CareTrack

Outpatient Triage & Priority Queue System — a standalone, offline-first clinical web app for nurse intake triage, doctor-queue management, and wait-time analytics, paired with an offline benchmark that validates triage safety under a 5×5 asymmetric cost matrix.

## Overview

PranaTriage helps outpatient departments (OPD) triage patients at the nurse intake desk, assign color-coded priority levels, manage a doctor-facing consultation queue, and monitor wait-time / triage-safety analytics. It is designed for low-resource settings with multilingual support (English, Telugu, Hindi) and runs entirely in the browser with no backend dependency.

> **Status:** Firebase backend integrated (Firestore persistence + real-time sync). Offline benchmark included.

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
- **Search / filter:** type in the search box to filter patients by age, gender, or language
- **Discharge / mark-as-seen:** each queue item has a ✓ button to discharge the patient and renumber remaining rooms
- **Wait-time estimates:** per-priority-level estimated wait times that update dynamically as the queue changes
- Call-next consultation with automatic room-number renumbering
- Empty-state handling when the queue drains
- Print-friendly output via the browser's print dialog (`@media print` styles)
- **Firebase persistence:** queue is saved to Firestore and synced in real-time across devices

### 3. Wait-Time Analytics (`index.html` → "Wait-Time Analytics" tab)
- Mean asymmetric loss and critical-miss-rate indicators
- **Priority Level Reference card:** visual legend for all 5 levels (Red/Emergency through Blue/Stable) with room assignments
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



## Firebase Backend Integration

PranaTriage now uses **Firebase Firestore** as its backend for persistent, multi-device queue synchronization.

### What's stored in Firestore
The `patients` collection stores one document per triaged patient:

| Field | Type | Description |
|-------|------|-------------|
| `age` | number | Patient age in years |
| `gender` | string | Patient gender |
| `language` | string | Language preference (English/Telugu/Hindi) |
| `vitals` | object | Sanitized vitals (tempC, systolic, diastolic, shockIndex, pulse, spo2, age, bpDisconnected) |
| `symptoms` | array | Selected symptom chips |
| `level` | number | Triage priority level (1–5) |
| `room` | string | Assisted room/department |
| `color` | string | Priority color (red/orange/yellow/green/blue) |
| `status` | string | `waiting`, `called`, or `discharged` |
| `createdAt` | timestamp | Server timestamp when triaged |
| `calledAt` | timestamp | Server timestamp when called for consultation |

### How it works
1. **Add patient:** When a patient is triaged, the record is written to Firestore and immediately rendered in the local queue
2. **Real-time sync:** An `onSnapshot` listener keeps the queue in sync across all connected devices — patients added, called, or discharged on one device appear on all others
3. **Call next:** Updates the patient's `status` to `called` in Firestore and removes from the active queue
4. **Discharge:** Deletes the patient document from Firestore
5. **Offline resilience:** Firebase offline persistence caches writes locally and syncs when connectivity returns

### Connection indicator
A status badge in the header shows the current Firebase connection state:
- 🟢 **Connected** — Firestore is reachable, reads/writes are live
- 🔴 **Offline** — Firestore is unreachable; app continues working locally with cached data

## Browser & Accessibility

- Works in Chrome, Edge, Firefox, Safari (mobile and desktop)
- Responsive grid layout (single-column on mobile, two-column on lg+)
- **Dark mode toggle:** 🌓 button in the header switches between light and dark themes (persists via `data-theme="dark"`)
- **Print-friendly:** browser print dialog produces a clean queue/token view (UI controls hidden via `@media print`)
- **Firebase connection status:** live indicator in the header shows Connected / Offline state
- Keyboard: Enter key submits the triage form from any input

## Roadmap / Future Work

- ✅ Firebase / backend integration — complete (Firestore persistence + real-time sync)
- Unit tests for `sanitizeVitals` / `determinePriority` / `assign_triage_level`
- CI safety gate that fails the build if sensitivity < 98% or miss rate > 2%
- Additional clinical parameters (respiratory rate, GCS, pain score)

## License

MIT
