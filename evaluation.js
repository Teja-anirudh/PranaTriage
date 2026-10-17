// ============================================================================
// PRANA PRIORITY EVALUATION ENGINE
// ============================================================================

// Load test dataset
let TEST_DATASET = null;

// Cost matrix (asymmetric safety)
const COST_MATRIX = [
  [0,   1,   5,  20,  50],   // True L1 Emergency
  [1,   0,   1,   5,  20],   // True L2 Urgent
  [5,   1,   0,   1,   5],   // True L3 Semi-urgent
  [20,  5,   1,   0,   1],   // True L4 Non-urgent
  [50, 20,   5,   1,   0]    // True L5 Stable
];

const COST_ABSTAIN = 1.5;

// ============================================================================
// Core Functions (from index.html)
// ============================================================================

function shockIndex(pulse, sbp) {
  if (pulse == null || sbp == null || sbp === 0) return null;
  return (pulse / sbp).toFixed(2);
}

function wholeWordMatch(text, term) {
  const t = text.toLowerCase().trim();
  const termLower = term.toLowerCase().trim();
  const escaped = termLower.replace(/[.*+?^${}()|[\]\]/g, '\\$&');
  const regex = new RegExp('(^|\\s)' + escaped + '(\\s|$)', 'i');
  return regex.test(t);
}

const SYMPTOM_LEXICON = {
  chest_pain: {
    terms: ['chest pain', 'seene mein dard', 'chhati dard', 'gundelo noppi', 'గుండె నొప్పి', 'గుండే నొప్పి'],
    context: ['chest', 'heart', 'cardiac', 'left arm', 'గుండె', 'seene', 'chhati'],
    level: 2
  },
  breathlessness: {
    terms: ['breathlessness', 'dyspnea', 'shortness of breath', 'saans phoolna', 'saans nahi aa rahi', 'saans nahi', 'ಆಯಾಸం', 'ఆయాసం', 'aayasam'],
    level: 2
  },
  stroke: {
    terms: ['stroke', 'hemiplegia', 'one-sided weakness', 'facial droop', 'slurred speech', 'లక్వా', 'పక్షవాతం', 'ఒక వైపు చేయి', 'ఒక వైపు కాలు', 'మాట ముద్దగా', 'లకవా'],
    level: 2
  },
  snakebite: {
    terms: ['snakebite', 'snake bite', 'సర్ప దంచు', 'సార్పు కాటు'],
    level: 1
  },
  poisoning: {
    terms: ['poisoning', 'poison', 'విషం'],
    level: 1
  },
  severe_bleeding: {
    terms: ['severe bleeding', 'heavy bleeding'],
    level: 1
  },
  seizure: {
    terms: ['seizure', 'convulsion', 'fits'],
    level: 1
  },
  severe_abdominal_pain: {
    terms: ['severe abdominal pain', 'stomach pain severe'],
    level: 2
  },
  pregnancy_bleeding: {
    terms: ['pregnancy bleeding', 'vaginal bleeding'],
    level: 1
  },
  high_fever_stiff_neck: {
    terms: ['high fever with stiff neck', 'fever stiff neck'],
    level: 2
  },
  diabetic_emergency: {
    terms: ['diabetic emergency', 'hypoglycaemia', 'low blood sugar'],
    level: 2
  },
  unconscious: {
    terms: ['unconscious', 'unresponsive', 'collapsed', 'not breathing'],
    level: 1
  }
};

function detectSymptoms(complaint) {
  const detected = [];
  const c = complaint.toLowerCase();
  for (const [key, def] of Object.entries(SYMPTOM_LEXICON)) {
    for (const term of def.terms) {
      if (wholeWordMatch(complaint, term)) {
        detected.push({ key: key, term: term, level: def.level });
        break;
      }
    }
  }
  return detected;
}

function sanitizeVitals(input) {
  const result = {
    tempC: null,
    tempSource: null,
    spo2: null,
    pulse: null,
    sbp: null,
    dbp: null,
    missing: [],
    suspect: [],
    warnings: []
  };

  // Temperature
  if (input.temp !== undefined && input.temp !== '' && input.temp != null) {
    const t = parseFloat(String(input.temp).replace(/[°cf]/gi, '').trim());
    if (!isNaN(t)) {
      if (t > 80) {
        result.tempC = ((t - 32) * 5 / 9).toFixed(1);
        result.tempSource = 'fahrenheit';
      } else {
        result.tempC = t.toFixed(1);
        result.tempSource = 'celsius';
      }
    } else {
      result.missing.push('temperature');
    }
  } else {
    result.missing.push('temperature');
  }

  // SpO2
  if (input.spo2 !== undefined && input.spo2 !== '' && input.spo2 != null) {
    const s = parseFloat(input.spo2);
    if (!isNaN(s)) {
      if (s < 50 || s > 100) {
        result.suspect.push('spo2');
        result.warnings.push('SpO2 ' + s + '% is implausible (<50 or >100). Re-measure.');
      } else {
        result.spo2 = s;
      }
    } else {
      result.missing.push('spo2');
    }
  } else {
    result.missing.push('spo2');
  }

  // Pulse
  if (input.pulse !== undefined && input.pulse !== '' && input.pulse != null) {
    const p = parseFloat(input.pulse);
    if (!isNaN(p)) {
      if (p < 20 || p > 250) {
        result.suspect.push('pulse');
        result.warnings.push('Pulse ' + p + ' BPM is implausible (<20 or >250). Re-measure.');
      } else {
        result.pulse = p;
      }
    } else {
      result.missing.push('pulse');
    }
  } else {
    result.missing.push('pulse');
  }

  // SBP
  if (input.sbp !== undefined && input.sbp !== '' && input.sbp != null) {
    const s = parseFloat(input.sbp);
    if (!isNaN(s)) {
      if (s === 0) {
        result.missing.push('sbp');
      } else if (s < 50 || s > 300) {
        result.suspect.push('sbp');
        result.warnings.push('SBP ' + s + ' mmHg is implausible. Re-measure.');
      } else {
        result.sbp = s;
      }
    } else {
      result.missing.push('sbp');
    }
  } else {
    result.missing.push('sbp');
  }

  // DBP
  if (input.dbp !== undefined && input.dbp !== '' && input.dbp != null) {
    const d = parseFloat(input.dbp);
    if (!isNaN(d)) {
      if (d === 0) {
        result.missing.push('dbp');
      } else if (d < 30 || d > 200) {
        result.suspect.push('dbp');
        result.warnings.push('DBP ' + d + ' mmHg is implausible. Re-measure.');
      } else {
        result.dbp = d;
      }
    } else {
      result.missing.push('dbp');
    }
  } else {
    result.missing.push('dbp');
  }

  return result;
}

function triage(input) {
  const result = {
    level: null,
    dept: null,
    room: null,
    flags: [],
    decision: null,
    confidence: null,
    abstain: false,
    reason: '',
    missingVitals: [],
    suspectVitals: []
  };

  // 1. Sanitize vitals
  const vitals = sanitizeVitals(input);
  result.missingVitals = vitals.missing;
  result.suspectVitals = vitals.suspect;
  result.flags = vitals.warnings.slice();

  const age = input.age != null ? parseFloat(input.age) : null;
  const isChild = age != null && age < 12;
  const complaint = String(input.complaint || '').trim();
  const complaintLower = complaint.toLowerCase();

  // 2. Hard overrides (instant Level 1)
  let hardOverride = false;
  let overrideReason = '';

  if (vitals.spo2 != null && vitals.spo2 <= 85) {
    hardOverride = true;
    overrideReason = 'SpO2 ' + vitals.spo2 + '% ≤ 85%';
  }
  if (!hardOverride && vitals.pulse != null && vitals.sbp != null && vitals.sbp > 0 && !isChild) {
    const si = shockIndex(vitals.pulse, vitals.sbp);
    if (si != null && parseFloat(si) >= 1.4) {
      hardOverride = true;
      overrideReason = 'Shock Index ' + si + ' ≥ 1.4';
    }
  }
  if (!hardOverride) {
    for (const kw of ['unconscious', 'not breathing', 'collapsed', 'seizure']) {
      if (complaintLower.includes(kw)) {
        hardOverride = true;
        overrideReason = 'Patient reports: ' + kw;
        break;
      }
    }
  }
  if (!hardOverride && vitals.sbp != null && vitals.sbp < 80 && !isChild) {
    hardOverride = true;
    overrideReason = 'SBP ' + vitals.sbp + ' < 80 mmHg';
  }

  if (hardOverride) {
    result.level = 1;
    result.dept = 'Emergency / Casualty';
    result.room = 'Room 1';
    result.decision = 'LEVEL 1 — Emergency';
    result.confidence = 'High';
    result.abstain = false;
    result.reason = 'HARD OVERRIDE: ' + overrideReason + '. Immediate emergency care required.';
    result.flags.push(overrideReason);
    return result;
  }

  // 3. Multilingual symptom detection
  const symptoms = detectSymptoms(complaint);

  // Chest pain: requires chest/heart/left-arm context OR (age>=40 AND sweating)
  let chestPainConfirmed = false;
  for (const s of symptoms) {
    if (s.key === 'chest_pain') {
      const hasContext = SYMPTOM_LEXICON.chest_pain.context.some(c => complaintLower.includes(c.toLowerCase()));
      const ageSweat = age != null && age >= 40 && complaintLower.includes('sweat');
      if (hasContext || ageSweat) {
        chestPainConfirmed = true;
        result.flags.push('Chest pain with cardiac context');
      } else {
        result.flags.push('Chest pain mentioned without cardiac context');
      }
    }
  }

  // Stroke pattern
  let strokeDetected = false;
  for (const s of symptoms) {
    if (s.key === 'stroke') {
      strokeDetected = true;
      result.flags.push('Stroke symptoms detected');
    }
  }

  // Life-threatening (Level 1 from symptoms)
  let lifeThreatening = false;
  for (const s of symptoms) {
    if (s.level === 1 && s.key !== 'chest_pain') {
      lifeThreatening = true;
      break;
    }
  }

  if (lifeThreatening) {
    result.level = 1;
    result.dept = 'Emergency / Casualty';
    result.room = 'Room 1';
    result.decision = 'LEVEL 1 — Emergency';
    result.confidence = 'High';
    result.abstain = false;
    result.reason = 'Life-threatening symptom detected via multilingual lexicon.';
    return result;
  }

  // 4. Level 2 rules
  let level2 = false;
  let level2Reason = '';

  if (chestPainConfirmed) {
    level2 = true;
    level2Reason = 'ACS pattern: chest pain with cardiac context';
    result.dept = 'Cardiology';
    result.room = 'Room 2';
  }
  else if (strokeDetected) {
    level2 = true;
    level2Reason = 'Stroke pattern detected';
    result.dept = 'Neurology';
    result.room = 'Room 2';
  }
  else if (vitals.spo2 != null && vitals.spo2 <= 90) {
    level2 = true;
    level2Reason = 'Respiratory distress: SpO2 ' + vitals.spo2 + '% ≤ 90%';
    result.dept = 'Respiratory';
    result.room = 'Room 2';
  }
  else if (vitals.sbp != null && vitals.sbp >= 180 && strokeDetected) {
    level2 = true;
    level2Reason = 'SBP ' + vitals.sbp + ' ≥ 180 with neuro symptoms';
    result.dept = 'Neurology';
    result.room = 'Room 2';
  }
  else {
    for (const s of symptoms) {
      if (s.key === 'diabetic_emergency') {
        level2 = true;
        level2Reason = 'Diabetic emergency / hypoglycaemia';
        result.dept = 'General Medicine';
        result.room = 'Room 2';
        break;
      }
    }
  }

  if (level2) {
    result.level = 2;
    result.decision = 'LEVEL 2 — Urgent';
    result.confidence = 'Medium-High';
    result.abstain = false;
    result.reason = level2Reason;
    return result;
  }

  // 5. Level 3 vs 4
  let level = 4;
  let dept = 'General Medicine';
  let room = 'Room 4';
  let reason = 'Mild presentation — routine care';
  let confidence = 'Medium';

  const hasFever = vitals.tempC != null && parseFloat(vitals.tempC) >= 38.0;
  const highFever = vitals.tempC != null && parseFloat(vitals.tempC) >= 39.5;
  const hasVomiting = complaintLower.includes('vomit');
  const hasDehydration = complaintLower.includes('dehydration');
  const extremeAge = age != null && (age < 5 || age > 65);
  const abnormalVitals = vitals.suspect.length > 0 || (vitals.spo2 != null && vitals.spo2 <= 94);

  if (hasFever) {
    if (highFever || hasVomiting || hasDehydration || extremeAge || abnormalVitals) {
      level = 3;
      dept = 'General Medicine';
      room = 'Room 3';
      reason = 'Fever ' + vitals.tempC + '°C with escalation factors';
      confidence = 'Medium';
    } else {
      level = 4;
      reason = 'Mild fever ' + vitals.tempC + '°C — routine care';
      confidence = 'Medium';
    }
  } else {
    const mildKeywords = ['cold', 'cough', 'rash', 'headache mild', 'sore throat'];
    const isMild = mildKeywords.some(k => complaintLower.includes(k));
    if (isMild) {
      level = 4;
      reason = 'Mild symptoms — routine OPD';
      confidence = 'Medium';
    } else {
      level = 3;
      reason = 'Symptoms present — semi-urgent assessment';
      confidence = 'Low-Medium';
    }
  }

  result.level = level;
  result.dept = dept;
  result.room = room;
  result.decision = 'LEVEL ' + level + ' — ' + (level === 1 ? 'Emergency' : level === 2 ? 'Urgent' : level === 3 ? 'Semi-urgent' : level === 4 ? 'Non-urgent' : 'Stable');
  result.confidence = confidence;
  result.abstain = false;
  result.reason = reason;
  return result;
}

function triageWithCost(input) {
  const base = triage(input);
  const complaint = String(input.complaint || '').trim();
  const criticalMissing = base.missingVitals.includes('spo2') || base.missingVitals.includes('sbp') || base.missingVitals.includes('pulse');
  const vagueComplaint = complaint.length < 10 || !/[a-zA-Z0-9]/.test(complaint);

  if (base.level === 4 && criticalMissing && vagueComplaint) {
    base.abstain = true;
    base.level = null;
    base.dept = 'Triage Nurse STAT Desk';
    base.room = 'Nurse Station';
    base.decision = 'ABSTAIN — Nurse Review';
    base.confidence = 'Low';
    base.reason = 'Critical vitals missing and complaint is vague. Abstaining to nurse for manual assessment.';
    base.flags.push('ABSTAIN: missing vitals + vague complaint');
  }

  return base;
}

function calculateAsymmetricLoss(trueLevel, assignedLevel) {
  if (trueLevel === null) return COST_ABSTAIN;
  if (assignedLevel === null) return COST_ABSTAIN;
  
  const ti = trueLevel - 1;
  const ai = assignedLevel - 1;
  return COST_MATRIX[ti][ai];
}

function runEvaluation() {
  if (!TEST_DATASET) {
    console.error('Test dataset not loaded');
    return;
  }

  const results = {
    total_patients: TEST_DATASET.length,
    true_emergencies: TEST_DATASET.filter(row => row.true_level === 1).length,
    assignments: [],
    metrics: {}
  };

  // Process each patient
  TEST_DATASET.forEach((row, index) => {
    const input = {
      age: row.age,
      gender: row.gender,
      complaint: row.description,
      temp: row.temp,
      spo2: row.spo2,
      pulse: row.pulse,
      sbp: row.sbp,
      dbp: row.dbp
    };

    const triageResult = triageWithCost(input);
    
    const assignedLevel = triageResult.level || null;
    const trueLevel = row.true_level;
    
    results.assignments.push({
      patient_id: row.patient_id,
      true_level: trueLevel,
      assigned_level: assignedLevel,
      complaint: row.description,
      language: row.language,
      vitals_complete: !!(row.spo2 && row.pulse && row.sbp),
      cost: calculateAsymmetricLoss(trueLevel, assignedLevel)
    });
  });

  // Calculate metrics
  const assignments = results.assignments;
  const trueLevels = assignments.map(a => a.true_level).filter(l => l !== null);
  const assignedLevels = assignments.map(a => a.assigned_level).filter(l => l !== null);
  
  // Emergency sensitivity (recall)
  const tp = assignments.filter(a => a.true_level === 1 && a.assigned_level === 1).length;
  const fn = assignments.filter(a => a.true_level === 1 && a.assigned_level !== 1).length;
  results.metrics.emergency_sensitivity = tp / (tp + fn) * 100 || 0;
  
  // Critical miss rate
  const total_emergencies = assignments.filter(a => a.true_level === 1).length;
  const critical_misses = assignments.filter(a => a.true_level === 1 && a.assigned_level !== 1).length;
  results.metrics.critical_miss_rate = critical_misses / total_emergencies * 100 || 0;
  
  // Over-triage rate
  const over_triage_count = assignments.filter(a => a.true_level < a.assigned_level).length;
  results.metrics.over_triage_rate = over_triage_count / assignments.length * 100 || 0;
  
  // Under-triage rate
  const under_triage_count = assignments.filter(a => a.true_level > a.assigned_level).length;
  results.metrics.under_triage_rate = under_triage_count / assignments.length * 100 || 0;
  
  // Correct triage rate
  const correct_count = assignments.filter(a => a.true_level === a.assigned_level).length;
  results.metrics.correct_triage_rate = correct_count / assignments.length * 100 || 0;
  
  // Mean asymmetric loss
  const total_cost = assignments.reduce((sum, a) => sum + a.cost, 0);
  results.metrics.mean_asymmetric_loss = total_cost / assignments.length || 0;
  
  // Abstain rate
  const abstain_count = assignments.filter(a => a.assigned_level === null).length;
  results.metrics.abstain_rate = abstain_count / assignments.length * 100 || 0;
  
  // Per-level accuracy
  results.metrics.level_accuracy = {};
  for (let level = 1; level <= 5; level++) {
    const level_mask = assignments.filter(a => a.true_level === level);
    if (level_mask.length > 0) {
      const level_correct = level_mask.filter(a => a.assigned_level === level).length;
      results.metrics.level_accuracy[level] = level_correct / level_mask.length * 100;
    } else {
      results.metrics.level_accuracy[level] = 0;
    }
  }

  // Save results to localStorage
  localStorage.setItem('pranapriority_evaluation_results', JSON.stringify(results));
  
  return results;
}

function loadTestDataset() {
  fetch('test_dataset.json')
    .then(response => response.json())
    .then(data => {
      // Convert array to DataFrame-like structure
      TEST_DATASET = data.map(row => {
        const input = {
          age: row.age,
          gender: row.gender,
          complaint: row.description,
          temp: row.temp,
          spo2: row.spo2,
          pulse: row.pulse,
          sbp: row.sbp,
          dbp: row.dbp
        };
        return {
          patient_id: row.patient_id,
          description: row.description,
          age: row.age,
          gender: row.gender,
          spo2: row.spo2,
          pulse: row.pulse,
          sbp: row.sbp,
          dbp: row.dbp,
          temp: row.temp,
          true_level: row.true_level,
          language: row.language
        };
      });
      console.log('Test dataset loaded:', TEST_DATASET.length, 'patients');
    })
    .catch(error => {
      console.error('Error loading test dataset:', error);
      // Try localStorage as fallback
      const saved = localStorage.getItem('test_dataset_backup');
      if (saved) {
        TEST_DATASET = JSON.parse(saved);
        console.log('Test dataset loaded from localStorage:', TEST_DATASET.length, 'patients');
      }
    });
}

// Export functions
window.evaluation = {
  loadTestDataset,
  runEvaluation,
  calculateAsymmetricLoss,
  COST_MATRIX,
  COST_ABSTAIN
};

console.log('Prana Priority evaluation engine loaded');
