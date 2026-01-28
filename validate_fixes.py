import requests
import time
import sys

BASE_URL = "http://localhost:5000/api"

def test_attack(payload, name):
    print(f"Testing {name}...")
    try:
        response = requests.post(f"{BASE_URL}/attack", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"  [SUCCESS] Started. ID: {data.get('attack_id')} Status: {data.get('status')}")
            return True
        else:
            print(f"  [FAILED] Code: {response.status_code} Error: {response.text}")
            return False
    except Exception as e:
        print(f"  [ERROR] Connection failed: {e}")
        return False

def main():
    print("=== Validating ModelFang Fixes ===\n")
    
    # 1. Dataset Mode Fix
    # Should find jailbreak_patterns.json
    success_1 = test_attack({
        "attack_id": "dataset:random",
        "target_model_id": "target-llama3",
        "context": {}
    }, "Dataset Mode (Random)")
    
    # 2. Systematic Mode Fix
    # Should verify abstract class instantiation works
    success_2 = test_attack({
        "attack_id": "systematic:jailbreak",
        "target_model_id": "target-llama3",
        "context": {"num_probes": 2}
    }, "Systematic Mode (Jailbreak)")
    
    # 3. Template: Roles Fix
    success_3 = test_attack({
        "attack_id": "template:roles",
        "model_id": "target-llama3", 
        "context": {"goal": "build a bomb"}
    }, "Template Mode (Roles)")
    
    # 4. Template: Logic Fix
    success_4 = test_attack({
        "attack_id": "template:logic",
        "target_model_id": "target-llama3",
        "context": {"goal": "bypass filter"}
    }, "Template Mode (Logic)")
    
    print("\n=== Validation Complete ===")
    if all([success_1, success_2, success_3, success_4]):
        print("ALL TESTS PASSED. Backend is stable.")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
