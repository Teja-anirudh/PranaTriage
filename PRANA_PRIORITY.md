# Prana Priority - Implementation Plan

## Overview
Rebuild the existing PranaTriage HTML into a cleaner app called "Prana Priority" with 3 tabs: Triage (nurse), Queue (doctor), Results (judges). Based on the existing triage engine but simplified for phone screens.

## Requirements

### Basic Structure
- Self-contained index.html only
- Vanilla JS and Tailwind CDN (pinned 3.4.17)
- Works on 360px phone screen
- Big buttons, high contrast
- 3 tabs: Nurse, Doctor, Results

### Header & Footer
- Header: "Prana Priority", tagline "The sickest patient is seen first."
- Language toggle: English/Telugu
- Counter: waiting, emergencies
- Footer: "Decision support only. Nurse can override."

### Tab 1: Triage (Nurse)
- Form: age, sex, SpO2, pulse, BP, temperature, complaint (En/Te)
- Preset buttons ONLY fill form, not run triage
- "Run triage" button required to trigger
- Result card with level color, department, red flags, reason, response time
- Purple "Cannot assess, send to nurse now" card for missing vitals/vague complaint
- Nurse override button with reason logging
- Print slip button with real date/time, token, color, icon, room

### Tab 2: Queue (Doctor)
- List sorted by level then arrival time
- Level 3 & 4 aging (not stuck forever)
- Each row: level (color), token, age/sex, vitals, complaint, wait time
- "Call patient" removes from queue, updates counters
- Header counters from real data

### Tab 3: Results (Judges)
- Big card: Emergency recall headline
- Metrics computed from test set (no hardcoded numbers):
  - Missed-emergency rate
  - Total safety cost
  - Chart: wait time FCFS vs priority queue (simulation)
  - Level 4 & 5 waits shown
  - Table of hard rules and caught cases
  - Confusion matrix by language
- Every number computed by code from test set

### Core Logic
- Pure triage() function for testing
- Cost-based decision: cost = {missEmergency: 20, overTriage: 1, abstain: 1.5}
- 6-step triage process:
  1. Clean data (temp conversion, BP=0=missing, impossible values → warning)
  2. Hard rules (raise level only, never lower)
  3. Symptom word lists (Te, transliterated Te, Hindi, English)
  4. Cost-based decision with config object
  5. Abstain when unsure
  6. Return plain-language reason

### Other Requirements
- Escape all user text (no innerHTML)
- Use real symbols (≤, ≥) in JS strings
- Telugu toggle must translate all labels
- Voice input: Web Speech API (te-IN, hi-IN, en-IN)
- PA announcement uses real room
- Save queue in localStorage with try/catch

### Self-Test Panel (visible, all must pass)
1. SpO2 84 gives Level 1
2. Stroke text with SBP 195 gives Level 2, Neurology
3. No vitals and vague complaint gives Abstain, never Level 4
4. "ankle pain", age 32, is NOT cardiology
5. BP 0 marked missing with no crash
6. "<img src=x onerror=alert(1)>" shows as plain text
7. Calling a patient removes them from queue

## Testing Strategy
1. Create self-test panel with 7 test cases
2. Run tests on triage engine
3. Verify queue functionality
4. Check Results tab calculations
5. Ensure all requirements met

## File Structure
- index.html (single file, all-in-one)
- No backend, no external dependencies
- Fully self-contained