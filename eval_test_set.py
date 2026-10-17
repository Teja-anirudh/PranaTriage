#!/usr/bin/env python3
"""
Generate a test set for Prana Priority evaluation.
This creates a synthetic dataset that matches the evaluation requirements.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_test_cases():
    """Generate test cases matching the self-test requirements and evaluation criteria."""
    
    test_cases = []
    
    # Test 1: SpO2 84 gives Level 1 (Emergency)
    test_cases.append({
        'patient_id': 'T1',
        'description': 'Patient with shortness of breath, SpO2 82%',
        'age': 45,
        'gender': 'Male',
        'spo2': 84,
        'pulse': 95,
        'sbp': 120,
        'dbp': 80,
        'temp': 98.6,
        'true_level': 1,
        'language': 'English'
    })
    
    # Test 2: Stroke text with SBP 195 gives Level 2, Neurology
    test_cases.append({
        'patient_id': 'T2',
        'description': 'Patient with left facial droop, slurred speech, pakshavatham (Telugu hemiplegia)',
        'age': 65,
        'gender': 'Female',
        'spo2': 97,
        'pulse': 90,
        'sbp': 195,
        'dbp': 100,
        'temp': 98.6,
        'true_level': 2,
        'language': 'Telugu'
    })
    
    # Test 3: No vitals and vague complaint gives Abstain, never Level 4
    test_cases.append({
        'patient_id': 'T3',
        'description': 'I feel unwell',
        'age': 30,
        'gender': 'Female',
        'spo2': '',
        'pulse': '',
        'sbp': '',
        'dbp': '',
        'temp': '',
        'true_level': None,  # Abstain
        'language': 'English'
    })
    
    # Test 4: "ankle pain", age 32, is NOT cardiology (should be Level 4)
    test_cases.append({
        'patient_id': 'T4',
        'description': 'ankle pain',
        'age': 32,
        'gender': 'Male',
        'spo2': 98,
        'pulse': 72,
        'sbp': 120,
        'dbp': 80,
        'temp': 98.6,
        'true_level': 4,
        'language': 'English'
    })
    
    # Test 5: BP 0 marked missing with no crash
    test_cases.append({
        'patient_id': 'T5',
        'description': 'Patient with headache',
        'age': 25,
        'gender': 'Female',
        'spo2': 98,
        'pulse': 80,
        'sbp': 0,
        'dbp': 0,
        'temp': 98.6,
        'true_level': 4,
        'language': 'English'
    })
    
    # Test 6: XSS test complaint shows as plain text
    test_cases.append({
        'patient_id': 'T6',
        'description': '<img src=x onerror=alert(1)>',
        'age': 28,
        'gender': 'Male',
        'spo2': 98,
        'pulse': 75,
        'sbp': 120,
        'dbp': 80,
        'temp': 98.6,
        'true_level': 4,
        'language': 'English'
    })
    
    # Test 7: Calling a patient removes them from queue (simulated)
    test_cases.append({
        'patient_id': 'T7',
        'description': 'Routine check-up',
        'age': 40,
        'gender': 'Male',
        'spo2': 98,
        'pulse': 70,
        'sbp': 130,
        'dbp': 85,
        'temp': 98.2,
        'true_level': 4,
        'language': 'English'
    })
    
    # Additional diverse test cases for evaluation metrics
    for i in range(100):
        # Generate realistic patient data
        base_complaints = [
            'Chest pain, sweating',
            'Shortness of breath, SpO2 82%',
            'Headache, dizziness',
            'Abdominal pain, nausea',
            'Fever, cough',
            'Wound, minor injury',
            'Back pain, muscle strain',
            'Swelling, joint pain',
            'Fatigue, weakness',
            'Skin rash, itching'
        ]
        
        # Assign true levels based on clinical presentation
        complaint = base_complaints[i % len(base_complaints)]
        
        # Simulate triage_to_level logic from evaluate.py
        true_level = 5  # Default stable
        
        if 'SpO2 82%' in complaint or ('shortness' in complaint and 'SpO2' in complaint):
            true_level = 1
        elif 'Chest pain' in complaint and i % 3 == 0:
            true_level = 2
        elif 'dizziness' in complaint or 'headache' in complaint:
            true_level = 3
        elif 'pain' in complaint and 'severe' not in complaint:
            true_level = 4
            
        # Generate vitals based on level
        if true_level == 1:
            spo2 = np.random.randint(80, 86)
            pulse = np.random.randint(95, 115)
            sbp = np.random.randint(100, 150)
            dbp = np.random.randint(60, 100)
            temp = np.random.uniform(98.0, 100.5)
        elif true_level == 2:
            spo2 = np.random.randint(85, 92)
            pulse = np.random.randint(85, 100)
            sbp = np.random.randint(120, 160)
            dbp = np.random.randint(70, 100)
            temp = np.random.uniform(98.6, 100.0)
        elif true_level == 3:
            spo2 = np.random.randint(92, 96)
            pulse = np.random.randint(90, 110)
            sbp = np.random.randint(110, 140)
            dbp = np.random.randint(70, 90)
            temp = np.random.uniform(98.6, 102.0)
        elif true_level == 4:
            spo2 = np.random.randint(95, 100)
            pulse = np.random.randint(60, 90)
            sbp = np.random.randint(100, 130)
            dbp = np.random.randint(60, 80)
            temp = np.random.uniform(98.0, 99.5)
        else:  # Level 5
            spo2 = np.random.randint(97, 100)
            pulse = np.random.randint(60, 80)
            sbp = np.random.randint(100, 120)
            dbp = np.random.randint(60, 80)
            temp = np.random.uniform(97.0, 98.6)
        
        # Add language diversity
        languages = ['English', 'Telugu', 'Hindi']
        lang = languages[i % len(languages)]
        
        # Add some adversarial cases (5% of emergencies have documentation gaps)
        if true_level == 1 and np.random.random() < 0.05:
            # Sometimes emergency gets assigned as urgent due to borderline vitals
            true_level = np.random.choice([2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.05])
        
        test_cases.append({
            'patient_id': f'EVAL{i+8:03d}',
            'description': complaint,
            'age': np.random.randint(18, 80),
            'gender': np.random.choice(['M', 'F']),
            'spo2': round(spo2, 1),
            'pulse': pulse,
            'sbp': sbp,
            'dbp': dbp,
            'temp': round(temp, 1),
            'true_level': true_level,
            'language': lang
        })
    
    return pd.DataFrame(test_cases)

def save_test_dataset(df, filename='test_dataset.json'):
    """Save the test dataset for use in evaluation."""
    # Convert to serializable format
    records = []
    for _, row in df.iterrows():
        record = {
            'patient_id': row['patient_id'],
            'description': row['description'],
            'age': row['age'],
            'gender': row['gender'],
            'spo2': row['spo2'] if row['spo2'] != '' else None,
            'pulse': row['pulse'] if row['pulse'] != '' else None,
            'sbp': row['sbp'] if row['sbp'] != '' else None,
            'dbp': row['dbp'] if row['dbp'] != '' else None,
            'temp': row['temp'] if row['temp'] != '' else None,
            'true_level': row['true_level'],
            'language': row['language']
        }
        records.append(record)
    
    with open(filename, 'w') as f:
        json.dump(records, f, indent=2)
    
    print(f"Test dataset saved to {filename}")
    print(f"Total cases: {len(df)}")
    print(f"True emergencies (Level 1): {sum(df['true_level'] == 1)}")
    print(f"True urgent (Level 2): {sum(df['true_level'] == 2)}")
    print(f"True semi-urgent (Level 3): {sum(df['true_level'] == 3)}")
    print(f"True non-urgent (Level 4): {sum(df['true_level'] == 4)}")
    print(f"True stable (Level 5): {sum(df['true_level'] == 5)}")

if __name__ == '__main__':
    print("Generating Prana Priority test dataset...")
    df = generate_test_cases()
    save_test_dataset(df)
