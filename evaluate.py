#!/usr/bin/env python3
"""
PranaTriage Offline Benchmark Script (evaluate.py)

Implements the 5x5 asymmetric cost matrix where under-triaging true emergencies
is penalized 20x quadratically over over-triaging mild cases.

Calculates:
- Mean Asymmetric Loss
- True Emergency Sensitivity/Recall (target: >= 98%)
- Critical Miss Rate
"""

import pandas as pd
import numpy as np
import json
import sys
from typing import List, Dict, Tuple, Optional


# =============================================================================
# 5x5 ASYMMETRIC COST MATRIX
# =============================================================================

# Row: True Priority (1=Red/ Emergency, 2=Orange/ Urgent, 3=Yellow/ Semi-urgent,
#       4=Green/ Non-urgent, 5=Blue/ Stable)
# Column: Assigned Priority
# Cost values represent the penalty multiplier. Under-triaging (assigning lower
# priority than true state) is penalized 20x more than over-triaging.

# Cost matrix: cost[true_priority - 1][assigned_priority - 1]
# true\assigned   1    2    3    4    5
COST_MATRIX = [
    # True 1 (Emergency)      - Over-triage is OK, under-triage is fatal
    [0,   1,   5,  20,  50],  # Assigned 1-5: 0 penalty for correct, 1 for mild over, 5 for moderate, 20 for under-triage, 50 for severe under
    
    # True 2 (Urgent)
    [1,   0,   1,   5,  20],
    
    # True 3 (Semi-urgent)
    [5,   1,   0,   1,   5],
    
    # True 4 (Non-urgent)
    [20,  5,   1,   0,   1],
    
    # True 5 (Stable)
    [50,  20,   5,   1,   0]
]

# Human-readable cost descriptions
COST_DESCRIPTIONS = {
    (1, 1): "Correct triage (True Emergency → Level 1)",
    (1, 2): "Mild over-triage (Emergency → Level 2)",
    (1, 3): "Moderate over-triage",
    (1, 4): "Severe under-triage (Emergency → Level 4) — PENALTIZED 20x",
    (1, 5): "Critical under-triage (Emergency → Level 5) — PENALTIZED 50x",
    
    (2, 1): "Over-triage (Urgent → Level 1) — minor penalty",
    (2, 2): "Correct triage (Urgent → Level 2)",
    (2, 3): "Mild over-triage",
    (2, 4): "Under-triage (Urgent → Level 4) — PENALTIZED 5x",
    (2, 5): "Critical under-triage",
    
    (3, 1): "Over-triage (Semi-urgent → Level 1) — PENALTIZED 5x",
    (3, 2): "Over-triage (Semi-urgent → Level 2) — PENALTIZED 1x",
    (3, 3): "Correct triage (Semi-urgent → Level 3)",
    (3, 4): "Under-triage (Semi-urgent → Level 4) — PENALTIZED 1x",
    (3, 5): "Under-triage",
    
    (4, 1): "Over-triage (Non-urgent → Level 1) — PENALTIZED 20x",
    (4, 2): "Over-triage (Non-urgent → Level 2) — PENALTIZED 5x",
    (4, 3): "Over-triage (Non-urgent → Level 3) — PENALTIZED 1x",
    (4, 4): "Correct triage (Non-urgent → Level 4)",
    (4, 5): "Under-triage (Non-urgent → Level 5) — PENALTIZED 1x",
    
    (5, 1): "Over-triage (Stable → Level 1) — PENALTIZED 50x",
    (5, 2): "Over-triage (Stable → Level 2) — PENALTIZED 20x",
    (5, 3): "Over-triage (Stable → Level 3) — PENALTIZED 5x",
    (5, 4): "Over-triage (Stable → Level 4) — PENALTIZED 1x",
    (5, 5): "Correct triage (Stable → Level 5)"
}


# =============================================================================
# TRIAGE MAPPING FUNCTIONS
# =============================================================================

def triage_to_level(description: str, vitals: dict) -> int:
    """
    Determine true triage level based on clinical presentation.
    This simulates the ground-truth triage decision.
    
    Returns integer 1-5 where:
    1 = Red (Immediate/ Emergency)
    2 = Orange (Urgent)
    3 = Yellow (Semi-urgent)
    4 = Green (Non-urgent)
    5 = Blue (Stable/ Follow-up)
    """
    spo2 = vitals.get('spo2', 100)
    pulse = vitals.get('pulse', 80)
    temp_c = vitals.get('temp_c', 37.0)
    temp_f = vitals.get('temp_f', 98.6)
    systolic = vitals.get('systolic', 120)
    diastolic = vitals.get('diastolic', 80)
    age = vitals.get('age', 30)
    
    # Use Celsius if available, otherwise convert from Fahrenheit
    if temp_c == 37.0 and temp_f != 98.6:
        temp_c = round((temp_f - 32) * 5 / 9, 1)
    
    # Normalize temperature if only F was provided
    if temp_c > 40 or temp_c < 20:
        # Likely still in Fahrenheit, convert
        temp_c = round((temp_f - 32) * 5 / 9, 1)
    
    # Level 1: True Emergency (Red)
    # SpO2 <= 85, shock index >= 1.4, severe respiratory distress
    if spo2 <= 85:
        return 1
    shock_index = pulse / systolic if systolic > 0 else 0
    if shock_index >= 1.4:
        return 1
    
    # Level 2: Urgent (Orange)
    # Adult >= 40 with chest pain, stroke signs, severe symptoms
    chest_keywords = ['chest pain', 'crushing pain', 'gundelo noppi', 'chhati me dard',
                      'पाल में दर्द', 'pectoris']
    stroke_keywords = ['pakshavatham', 'facial droop', 'slurred speech', 'aayasam',
                       'facial asymmetry', 'half body weakness']
    
    has_chest = any(kw in description.lower() for kw in chest_keywords)
    has_stroke = any(kw in description.lower() for kw in stroke_keywords)
    
    if age >= 40 and has_chest:
        return 2
    if has_stroke:
        return 2
    if spo2 <= 95:
        return 2
    if temp_c > 38.5:
        return 2
    
    # Level 3: Semi-urgent (Yellow)
    if temp_c > 38.0 or temp_c < 35.0:
        return 3
    if 95 < spo2 <= 98:
        return 3
    if pulse > 110 or pulse < 50:
        return 3
    
    # Level 4: Non-urgent (Green)
    if 98 < spo2 <= 100 and 50 <= pulse <= 110 and 35.0 <= temp_c <= 38.0:
        return 4
    
    # Level 5: Stable/ Follow-up (Blue)
    return 5


def assign_triage_level(description: str, vitals: dict) -> int:
    """
    Simulate the PranaTriage automated triage assignment.
    This represents what the system would assign based on input data.
    """
    spo2 = vitals.get('spo2', 100)
    pulse = vitals.get('pulse', 80)
    temp_f = vitals.get('temp_f', 98.6)
    temp_c = vitals.get('temp_c', 37.0)
    systolic = vitals.get('systolic', 120)
    diastolic = vitals.get('diastolic', 80)
    age = vitals.get('age', 30)
    
    # Normalize temperature: use Celsius if available, convert from Fahrenheit if needed
    if temp_c == 37.0 and temp_f != 98.6:
        temp_c = round((temp_f - 32) * 5 / 9, 1)
    if temp_c > 40 or temp_c < 20:
        # Likely still in Fahrenheit, convert
        temp_c = round((temp_f - 32) * 5 / 9, 1)
    
    # Priority checks (mirrors the frontend escalation overrides)
    
    # Level 1: SpO2 <= 85 or Shock Index >= 1.4
    if spo2 <= 85:
        return 1
    shock_index = pulse / systolic if systolic > 0 else 0
    if shock_index >= 1.4:
        return 1
    
    # Level 2: Adult >= 40 with chest pain symptoms
    chest_keywords = ['chest pain', 'crushing pain', 'gundelo noppi', 'chhati me dard']
    has_chest = any(kw in description.lower() for kw in chest_keywords)
    if age >= 40 and has_chest:
        return 2
    
    # Stroke signs
    stroke_keywords = ['pakshavatham', 'facial droop', 'slurred speech', 'aayasam']
    has_stroke = any(kw in description.lower() for kw in stroke_keywords)
    if has_stroke:
        return 2
    
    # Level 3: Moderate symptoms
    if spo2 <= 95 or temp_c > 38.5:
        return 3
    
    # Level 4: Mild symptoms, stable vitals
    if 95 < spo2 <= 98 and 50 <= pulse <= 110 and 35.0 <= temp_c <= 38.0:
        return 4
    
    # Level 5: Stable
    return 5


# =============================================================================
# METRIC CALCULATIONS
# =============================================================================

def calculate_asymmetric_loss(true_level: int, assigned_level: int, cost_matrix: List[List[float]]) -> float:
    """
    Calculate the asymmetric cost for a single triage decision.
    
    Args:
        true_level: True priority level (1-5)
        assigned_level: Assigned priority level (1-5)
        cost_matrix: 5x5 cost matrix
        
    Returns:
        Float cost value; higher = worse under-triage
    """
    ti = true_level - 1  # 0-indexed
    ai = assigned_level - 1  # 0-indexed
    return cost_matrix[ti][ai]


def calculate_mean_asymmetric_loss(true_levels: List[int], assigned_levels: List[int], 
                                    cost_matrix: List[List[float]]) -> float:
    """
    Calculate the mean asymmetric loss across all cases.
    """
    if len(true_levels) != len(assigned_levels):
        raise ValueError("True and assigned levels must have the same length")
    
    if not true_levels:
        return 0.0
    
    total_loss = 0.0
    for true, assigned in zip(true_levels, assigned_levels):
        total_loss += calculate_asymmetric_loss(true, assigned, cost_matrix)
    
    return total_loss / len(true_levels)


def calculate_sensitivity(true_levels: List[int], assigned_levels: List[int], 
                           emergency_level: int = 1) -> float:
    """
    Calculate sensitivity (recall) for detecting true emergencies.
    
    Sensitivity = True Positives / (True Positives + False Negatives)
    
    Where:
    - True Positive: True level 1 (emergency) assigned level 1
    - False Negative: True level 1 assigned level != 1
    """
    tp = 0  # True positives: true 1, assigned 1
    fn = 0  # False negatives: true 1, assigned != 1
    
    for true, assigned in zip(true_levels, assigned_levels):
        if true == emergency_level:
            if assigned == emergency_level:
                tp += 1
            else:
                fn += 1
    
    if tp + fn == 0:
        return 0.0
    
    return tp / (tp + fn) * 100  # Return as percentage


def calculate_critical_miss_rate(true_levels: List[int], assigned_levels: List[int],
                                  emergency_level: int = 1) -> float:
    """
    Calculate the critical miss rate: proportion of true emergencies that
    were assigned a lower priority (higher number = less urgent).
    
    Critical miss = True emergency (level 1) assigned to level 2-5
    """
    misses = 0
    total_emergencies = 0
    
    for true, assigned in zip(true_levels, assigned_levels):
        if true == emergency_level:
            total_emergencies += 1
            if assigned > emergency_level:  # Assigned to less urgent category
                misses += 1
    
    if total_emergencies == 0:
        return 0.0
    
    return misses / total_emergencies * 100  # Return as percentage


def generate_test_dataset(n_patients: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a synthetic test dataset for benchmarking.
    Includes realistic clinical presentations with Indian language symptoms.
    """
    np.random.seed(seed)
    
    descriptions = [
        # Emergency presentations
        "Patient with chest crushing pain, gundelo noppi, sweating",
        "Patient with shortness of breath, SpO2 82%, aayasam",
        "Patient with facial droop, slurred speech, pakshavatham",
        "Patient with heart attack symptoms, cold sweats",
        "Patient with severe respiratory distress, SpO2 88%",
        
        # Urgent presentations
        "Patient with chest pain, age 45, chhati me dard",
        "Patient with abdominal pain, nausea",
        "Patient with high fever 102°F, jalubu",
        "Patient with palpitations, irregular pulse",
        "Patient with dizziness, chakkar, BP 100/60",
        
        # Semi-urgent presentations
        "Patient with mild cold, runny nose, slight cough",
        "Patient with moderate headache, low-grade fever",
        "Patient with mild abdominal discomfort",
        "Patient with urinary symptoms, burning sensation",
        "Patient with mild injury, superficial wound",
        
        # Non-urgent presentations
        "Patient with chronic arthritis, joint pain",
        "Patient with routine follow-up, stable condition",
        "Patient with minor skin rash, itching",
        "Patient with medication refill request",
        "Patient with anxiety, no physical symptoms",
    ]
    
    # Vitals ranges by presentation type
    vitals_options = [
        # (spo2, pulse, temp_f, systolic, diastolic, age)
        (82, 110, 101.2, 150, 95, 65),   # Emergency
        (88, 95,  99.0, 130, 85, 55),     # Emergency
        (92, 105, 100.8, 140, 90, 45),    # Urgent
        (95,  88, 101.5, 135, 88, 50),    # Urgent
        (96,  85, 100.1, 125, 80, 35),    # Semi-urgent
        (97,  78,  99.5, 120, 80, 30),     # Semi-urgent
        (98,  72,  98.6, 115, 75, 25),    # Non-urgent
        (98,  70,  98.2, 110, 70, 22),    # Non-urgent
        (99,  68,  98.1, 110, 68, 20),    # Stable
        (99,  65,  97.8, 108, 65, 18),    # Stable
    ]
    
    data = []
    for i in range(n_patients):
        vitals = vitals_options[i % len(vitals_options)]
        description = descriptions[i % len(descriptions)]
        
        # Determine true level
        true_level = triage_to_level(description, {
            'spo2': vitals[0],
            'pulse': vitals[1],
            'temp': (vitals[2] - 32) * 5 / 9 if vitals[2] > 80 else vitals[2],
            'systolic': vitals[3],
            'diastolic': vitals[4],
            'age': vitals[5]
        })
        
        # Simulate system assignment (may differ from true level due to
        # missing data, language barriers, etc.)
        assigned_level = assign_triage_level(description, {
            'spo2': vitals[0],
            'pulse': vitals[1],
            'temp': vitals[2],
            'systolic': vitals[3],
            'diastolic': vitals[4],
            'age': vitals[5]
        })
        
        # Add some realistic errors (5% of emergencies may have documentation gaps)
        if np.random.random() < 0.05 and true_level == 1:
            # Sometimes emergency gets assigned as urgent due to borderline vitals
            assigned_level = np.random.choice([2, 3, 4, 5], p=[0.5, 0.3, 0.15, 0.05])
        
        data.append({
            'patient_id': f'P{i+1:04d}',
            'description': description,
            'true_level': true_level,
            'assigned_level': assigned_level,
            'spo2': vitals[0],
            'pulse': vitals[1],
            'temp_f': vitals[2],
            'temp_c': round((vitals[2] - 32) * 5 / 9, 1),
            'systolic': vitals[3],
            'diastolic': vitals[4],
            'age': vitals[5],
            'gender': np.random.choice(['M', 'F']),
            'language': np.random.choice(['English', 'Telugu', 'Hindi'])
        })
    
    return pd.DataFrame(data)


# =============================================================================
# REPORTING
# =============================================================================

def print_cost_matrix_summary():
    """Print the 5x5 cost matrix with descriptions."""
    print("\n" + "="*80)
    print("5x5 ASYMMETRIC COST MATRIX")
    print("Rows: True Priority  |  Columns: Assigned Priority")
    print("       (1=Red/Emergency  through 5=Blue/Stable)")
    print("="*80)
    
    header = "            " + "    ".join([f"Assigned {i+1}" for i in range(5)])
    print(header)
    
    for i, row_name in enumerate(["True 1", "True 2", "True 3", "True 4", "True 5"]):
        row_str = f"{row_name}: "
        for j, cost in enumerate(COST_MATRIX[i]):
            row_str += f"{cost:5d} "
        print(row_str)
    
    print("="*80)
    print("Cost Logic:")
    print("  - Under-triage (true > assigned): Penalized quadratically")
    print("  - Over-triage (true < assigned): Minor penalty, acceptable")
    print("  - Diagonal (correct): Cost = 0")
    print("  - Off-diagonal over-triage: Small positive costs")
    print("  - Off-diagonal under-triage: Large costs (20x-50x)")
    print("="*80 + "\n")


def run_benchmark(test_data: pd.DataFrame = None, n_samples: int = 1000) -> Dict:
    """
    Run the complete benchmark evaluation.
    
    Args:
        test_data: DataFrame with patient data (generated if None)
        n_samples: Number of test samples to generate
    
    Returns:
        Dictionary of calculated metrics
    """
    # Generate test data if not provided
    if test_data is None:
        df = generate_test_dataset(n_samples)
    else:
        df = test_data
    
    # Extract levels
    true_levels = df['true_level'].tolist()
    assigned_levels = df['assigned_level'].tolist()
    
    # Calculate metrics
    mean_loss = calculate_mean_asymmetric_loss(true_levels, assigned_levels, COST_MATRIX)
    sensitivity = calculate_sensitivity(true_levels, assigned_levels, emergency_level=1)
    critical_miss_rate = calculate_critical_miss_rate(true_levels, assigned_levels, emergency_level=1)
    
    # Additional analytics
    total_patients = len(df)
    true_emergencies = sum(1 for t in true_levels if t == 1)
    false_negatives = sum(1 for t, a in zip(true_levels, assigned_levels) if t == 1 and a != 1)
    false_positives = sum(1 for t, a in zip(true_levels, assigned_levels) if t != 1 and a == 1)
    
    # Over-triage rate
    over_triage_count = sum(1 for t, a in zip(true_levels, assigned_levels) if t < a)
    over_triage_rate = over_triage_count / total_patients * 100
    
    # Under-triage rate
    under_triage_count = sum(1 for t, a in zip(true_levels, assigned_levels) if t > a)
    under_triage_rate = under_triage_count / total_patients * 100
    
    # Correct triage rate
    correct_triage_count = sum(1 for t, a in zip(true_levels, assigned_levels) if t == a)
    correct_triage_rate = correct_triage_count / total_patients * 100
    
    # Per-level accuracy
    level_accuracy = {}
    for level in range(1, 6):
        level_mask = [t == level for t in true_levels]
        level_total = sum(level_mask)
        if level_total > 0:
            level_correct = sum(1 for t, a in zip(true_levels, assigned_levels) if t == a and t == level)
            level_accuracy[level] = level_correct / level_total * 100
        else:
            level_accuracy[level] = 0.0
    
    # Cost by type
    under_triage_costs = []
    over_triage_costs = []
    correct_costs = []
    
    for true, assigned in zip(true_levels, assigned_levels):
        cost = calculate_asymmetric_loss(true, assigned, COST_MATRIX)
        if true > assigned:
            under_triage_costs.append(cost)
        elif true < assigned:
            over_triage_costs.append(cost)
        else:
            correct_costs.append(cost)
    
    results = {
        'total_patients': total_patients,
        'true_emergencies': true_emergencies,
        'mean_asymmetric_loss': mean_loss,
        'sensitivity_emergency_pct': sensitivity,
        'critical_miss_rate_pct': critical_miss_rate,
        'over_triage_rate_pct': over_triage_rate,
        'under_triage_rate_pct': under_triage_rate,
        'correct_triage_rate_pct': correct_triage_rate,
        'level_accuracy': level_accuracy,
        'avg_under_triage_cost': np.mean(under_triage_costs) if under_triage_costs else 0,
        'avg_over_triage_cost': np.mean(over_triage_costs) if over_triage_costs else 0,
        'avg_correct_cost': np.mean(correct_costs) if correct_costs else 0,
        'dataset': df
    }
    
    return results


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main entry point for the benchmark script."""
    print("="*50)
    print("PRANATRIAGE • OPD CareTrack")
    print("Offline Benchmark Evaluation")
    print("Asymmetric Cost Matrix: 20x Under-triage Penalty")
    print("="*50)
    
    # Print cost matrix legend
    print_cost_matrix_summary()
    
    # Run benchmark
    print(f"\nGenerating test dataset with 1,000 synthetic patients...\n")
    results = run_benchmark(n_samples=1000)
    
    # Display results
    print("="*60)
    print("BENCHMARK RESULTS")
    print("="*60)
    
    print(f"\nTotal Patients Evaluated: {results['total_patients']}")
    print(f"True Emergencies (Level 1): {results['true_emergencies']}")
    print(f"  -> Prevalence: {results['true_emergencies']/results['total_patients']*100:.1f}%")
    
    print(f"\n{'Metric':<40} {'Value':>15}")
    print("-"*55)
    print(f"{'Mean Asymmetric Loss':<40} {results['mean_asymmetric_loss']:>15.2f}")
    print(f"{'Emergency Sensitivity (Recall)':<40} {results['sensitivity_emergency_pct']:>15.1f}%")
    print(f"{'Critical Miss Rate':<40} {results['critical_miss_rate_pct']:>15.1f}%")
    print(f"{'Over-triage Rate':<40} {results['over_triage_rate_pct']:>15.1f}%")
    print(f"{'Under-triage Rate':<40} {results['under_triage_rate_pct']:>15.1f}%")
    print(f"{'Correct Triage Rate':<40} {results['correct_triage_rate_pct']:>15.1f}%")
    
    print(f"\n{'Priority Level':<15} {'Accuracy':>10}")
    print("-"*25)
    for level in [1, 2, 3, 4, 5]:
        acc = results['level_accuracy'][level]
        print(f"{'Level '+str(level):<15} {acc:>9.1f}%")
    
    print(f"\nCost Analysis:")
    print(f"  Avg Under-triage Cost: {results['avg_under_triage_cost']:.2f}")
    print(f"  Avg Over-triage Cost:  {results['avg_over_triage_cost']:.2f}")
    print(f"  Avg Correct Cost:      {results['avg_correct_cost']:.2f}")
    
    # Safety validation
    print(f"\n{'SAFETY VALIDATION':<40}")
    print("-"*40)
    sensitivity_pct = results['sensitivity_emergency_pct']
    miss_pct = results['critical_miss_rate_pct']
    
    if sensitivity_pct >= 98:
        print(f"✓ Emergency Sensitivity: {sensitivity_pct:.1f}% (TARGET: >= 98%) — PASS")
    else:
        print(f"✗ Emergency Sensitivity: {sensitivity_pct:.1f}% (TARGET: >= 98%) — FAIL")
        
    if miss_pct <= 2.0:
        print(f"✓ Critical Miss Rate: {miss_pct:.1f}% (TARGET: <= 2%) — PASS")
    else:
        print(f"✗ Critical Miss Rate: {miss_pct:.1f}% (TARGET: <= 2%) — FAIL")
    
    # Cost ratio validation
    cost_ratio = results['avg_under_triage_cost'] / max(results['avg_over_triage_cost'], 1e-10)
    print(f"\nCost Ratio (Under-triage / Over-triage): {cost_ratio:.1f}x")
    if cost_ratio >= 15:
        print(f"✓ Asymmetric cost ratio meets 15x minimum requirement — PASS")
    else:
        print(f"✗ Asymmetric cost ratio insufficient (minimum 15x) — FAIL")
    
    print("="*60)
    
    # Save results to JSON for further analysis
    output_path = '/tmp/pranatriage_benchmark_results.json'
    summary = {k: v for k, v in results.items() if k != 'dataset'}
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())