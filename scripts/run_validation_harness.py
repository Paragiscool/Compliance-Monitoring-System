import json
import csv
import time
from core.orchestrator import build_orchestrator

def run_harness():
    print("[START] Initializing Automated Validation Harness...")
    
    # 1. Compile a test version of the graph WITHOUT the HITL interrupt
    test_app = build_orchestrator(enable_hitl=False)

    # 2. Load the Golden Dataset
    try:
        with open("data/validation_suite.json", "r") as f:
            scenarios = json.load(f)
    except FileNotFoundError:
        print("Error: validation_suite.json not found. Check the data directory.")
        return

    results = []
    correct_predictions = 0

    print(f"[INFO] Processing {len(scenarios)} scenarios...\n")

    for i, scenario in enumerate(scenarios):
        print(f"[{i+1}/{len(scenarios)}] Testing Scenario: {scenario['scenario_id']}")
        
        initial_state = {
            "raw_transactions": scenario.get("transactions", []),
            "raw_communications": scenario.get("communications", []),
            "active_regulatory_rules": [],
            "alerts": [],
            "requires_human_review": False,
            "human_decision": "AUTO_APPROVED", 
            "final_audit_report": ""
        }

        try:
            # 3. Execute the full multi-agent pipeline
            final_state = test_app.invoke(initial_state)
            
            # 4. Determine the highest severity alert generated
            alerts = final_state.get("alerts", [])
            actual_result = "CLEAN"
            
            if alerts:
                severities = [a.get("risk_level", "LOW").upper() for a in alerts]
                if "CRITICAL" in severities:
                    actual_result = "CRITICAL"
                elif "HIGH" in severities:
                    actual_result = "HIGH"
                elif "MEDIUM" in severities:
                    actual_result = "MEDIUM"
                elif "LOW" in severities:
                    actual_result = "LOW"

            # 5. Score the system's accuracy
            expected = scenario["expected_result"].upper()
            is_match = (actual_result == expected)
            if is_match:
                correct_predictions += 1

            print(f"   -> Expected: {expected} | Actual: {actual_result} | {'[PASS]' if is_match else '[FAIL]'}")

            results.append({
                "Scenario ID": scenario["scenario_id"],
                "Description": scenario["description"],
                "Expected": expected,
                "Actual": actual_result,
                "Pass": is_match
            })

            # Sleep briefly to respect the 15 RPM rate limit
            time.sleep(20)

        except Exception as e:
            print(f"   -> [WARNING] Pipeline Error: {e}")
            results.append({
                "Scenario ID": scenario["scenario_id"],
                "Description": scenario["description"],
                "Expected": scenario["expected_result"],
                "Actual": "ERROR",
                "Pass": False
            })

    # 6. Generate the Final CSV Report
    csv_file = "validation_results.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Scenario ID", "Description", "Expected", "Actual", "Pass"])
        writer.writeheader()
        writer.writerows(results)

    accuracy = (correct_predictions / len(scenarios)) * 100
    print("\n" + "="*50)
    print(f"[DONE] VALIDATION COMPLETE: {accuracy:.1f}% Accuracy")
    print(f"[FILE] Full report saved to {csv_file}")
    print("="*50)

if __name__ == "__main__":
    run_harness()
