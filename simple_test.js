// Simple test using the evaluation.js engine

const fs = require('fs');
const { exec } = require('child_process');

console.log('=== Testing Prana Priority with JavaScript Engine ===');

// Load the evaluation.js script
const evalScript = fs.readFileSync('evaluation.js', 'utf8');

// Create a simple test
function runTests() {
  console.log('\n1. Testing SpO2 84 -> Level 1...');
  
  const testCase = {
    patient_id: 'TEST1',
    description: 'Patient with shortness of breath, SpO2 82%',
    age: 45,
    gender: 'Male',
    spo2: 84,
    pulse: 95,
    sbp: 120,
    dbp: 80,
    temp: 98.6,
    true_level: 1
  };
  
  const input = {
    age: testCase.age,
    gender: testCase.gender,
    complaint: testCase.description,
    temp: testCase.temp,
    spo2: testCase.spo2,
    pulse: testCase.pulse,
    sbp: testCase.sbp,
    dbp: testCase.dbp
  };
  
  // Execute the triage function
  try {
    const evalScript = require('evaluation.js');
    const result = evalScript.triageWithCost(input);
    
    if (result.level === 1) {
      console.log('   ✅ PASS: SpO2 84 correctly gives Level 1');
    } else {
      console.log('   ❌ FAIL: SpO2 84 gave Level', result.level);
    }
  } catch (e) {
    console.log('   ❌ ERROR:', e.message);
  }
  
  console.log('\n2. Testing stroke case...');
  
  const testCase2 = {
    patient_id: 'TEST2',
    description: 'Patient with left facial droop, slurred speech, pakshavatham',
    age: 65,
    gender: 'Female',
    spo2: 97,
    pulse: 90,
    sbp: 195,
    dbp: 100,
    temp: 98.6,
    true_level: 2
  };
  
  const input2 = {
    age: testCase2.age,
    gender: testCase2.gender,
    complaint: testCase2.description,
    temp: testCase2.temp,
    spo2: testCase2.spo2,
    pulse: testCase2.pulse,
    sbp: testCase2.sbp,
    dbp: testCase2.dbp
  };
  
  try {
    const evalScript = require('evaluation.js');
    const result = evalScript.triageWithCost(input2);
    
    if (result.level === 2 && result.dept === 'Neurology') {
      console.log('   ✅ PASS: Stroke correctly gives Level 2, Neurology');
    } else {
      console.log('   ❌ FAIL: Stroke gave Level', result.level, 'Department:', result.dept);
    }
  } catch (e) {
    console.log('   ❌ ERROR:', e.message);
  }
  
  console.log('\n3. Testing evaluation engine...');
  
  // Test the full evaluation engine
  try {
    const { loadTestDataset, runEvaluation } = require('evaluation.js');
    
    // Load test dataset
    loadTestDataset();
    
    // Run evaluation
    const results = runEvaluation();
    
    console.log('   ✅ Evaluation engine working');
    console.log('   Total patients:', results.total_patients);
    console.log('   Emergency sensitivity:', results.metrics.emergency_sensitivity.toFixed(1), '%');
    console.log('   Critical miss rate:', results.metrics.critical_miss_rate.toFixed(1), '%');
    console.log('   Correct triage rate:', results.metrics.correct_triage_rate.toFixed(1), '%');
    
  } catch (e) {
    console.log('   ❌ Evaluation engine error:', e.message);
  }
}

runTests();
