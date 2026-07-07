import sys
import os
import json
from relic_parser import RelicLegalityChecker, VALID_DEEP_DEBUFFS

def run_tests():
    print("Initializing Legality Checker...")
    checker = RelicLegalityChecker(data_dir=".")
    
    if not checker.enabled:
        print("Error: Legality checker could not be initialized. Check game parameter CSV files.")
        sys.exit(1)
        
    print("Loading dictionary.json...")
    dictionary = json.load(open("dictionary.json", 'r', encoding='utf-8')) if os.path.exists("dictionary.json") else {}

    def get_name(idx):
        if idx is None or idx <= 0: return "-"
        e = dictionary.get(str(idx), {})
        return e.get("en", str(idx)) if isinstance(e, dict) else str(idx)

    # List of test cases
    # Each test case: (name, relic_id, buffs, curses, expected_status)
    test_cases = [
        (
            "Test 1: Official Preset Matching (Should be Official)",
            1000, 
            [7121100],  # Fire Pots in possession
            [], 
            "Official"
        ),
        (
            "Test 2: Modified Official Preset (Should be Illegal)",
            1000, 
            [7121100, 7120000],  # Fire Pots + Extra Buff
            [], 
            "Illegal"
        ),
        (
            "Test 3: Valid Standard Relic (Should be Legal)",
            100, 
            [7000000],  # HP Restoration on Curved Sword attacks
            [], 
            "Legal"
        ),
        (
            "Test 4: Exclusivity/Tier Stacking Conflict (Should be Illegal)",
            100, 
            [7000000, 7000000],  # Stacking duplicate buffs
            [], 
            "Illegal"
        ),
        (
            "Test 5: Deep Relic with Valid Deep Curse (Should be Legal)",
            2000000, 
            [6001500], 
            [8760000],  # Valid deep relic curse
            "Legal"
        ),
        (
            "Test 6: Effect-only automatic discovery of 3-slot combination (Should be Legal)",
            0, 
            [7220000, 7370900, 7060200], 
            [], 
            "Legal"
        ),
        (
            "Test 7: Grand Tranquil Scene with 3 Buffs (Should be Legal)",
            229, 
            [7220000, 7370900, 7060200], 
            [], 
            "Legal"
        ),
        (
            "Test 8: Grand Tranquil Scene with 3 Buffs with wrong order (Should be Legal)",
            229, 
            [7370900, 7220000, 7060200], 
            [], 
            "Legal"
        ),
        (
            "Test 9: Deep Grand Tranquil Scene with Out-of-Pool Buff (Should be Illegal)",
            2000302, 
            [7220000, 6840100, 7060200], 
            [], 
            "Illegal"
        ),
        (
            "Test 10: Grand Tranquil Scene with Duplicate Exclusivity Buffs (Should be Illegal)",
            2010112, 
            [7000090, 7000090, 7000090], 
            [], 
            "Illegal"
        ),
        (
            "Test 11: Duplicate Exclusivity Buffs with different effects (Should be Illegal)",
            2010112,
            [7010700, 7031300, 7220000],
            [],
            "Illegal"
        ),
        (
            "Test 12: Wrong order for first level classification (Should be Illegal)",
            2010112,
            [7001402, 7090000, 7043300],
            [],
            "Illegal"
        ),
        (
            "Test 13: Wrong order for first level classification (Should be Illegal)",
            2010112,
            [7001402, 7043300, 7090000],
            [],
            "Illegal"
        ),
        (
            "Test 14: Correct order for first level classification (Should be Legal)",
            2010112,
            [7043300, 7090000, 7001402],
            [],
            "Legal"
        ),
        (
            "Test 15: Wrong order for first level classification",
            2010112,
            [7002600, 7001402, 7000000],
            [],
            "Illegal"
        ),
        (
            "Test 16: Standard Relic with Curses (Should be Illegal)",
            100,
            [7000000],
            [8760000],
            "Illegal"
        ),
        (
            "Test 17: Deep Relic with valid Curse (Should be Legal)",
            2010112,
            [6001500, 7002600],
            [8760000, -1],
            "Legal"
        ),
        (
            "Test 18: Deep Relic with duplicate Curses (Should be Illegal)",
            2000000,
            [6001500, 6001500],
            [8760000, 8760000],
            "Illegal"
        ),
        (
            "Test 19: Correct order (Should be legal)",
            2010112,
            [7240000, 6001500, 7002600],
            [-1,6820200,-1],
            "Legal"
        ),
        (
            "Test 20: Standard HP Buff paired with Curse (Should be Illegal)",
            2000000,
            [7000000],
            [8760000],
            "Illegal"
        ),
        (
            "Test 21: Paired Buff without Curse (Should be Illegal)",
            2000000,
            [6001500],
            [],
            "Illegal"
        )
    ]

    print("\nRunning test cases...")
    print("=" * 80)
    
    passed_count = 0
    for title, relic_id, buffs, curses, expected in test_cases:
        # Build 4 raw slots format
        raw_slots = []
        for i in range(4):
            b_val = buffs[i] if i < len(buffs) else 0
            c_val = curses[i] if i < len(curses) else 0
            raw_slots.append({'pos': b_val, 'neg': c_val})
            
        res = checker.check(relic_id, raw_slots)
        status = res["status"]
        reason = res["reason"]
        
        is_pass = (status == expected)
        if is_pass:
            passed_count += 1
            result_str = "PASS"
        else:
            result_str = f"FAIL (Expected {expected}, got {status})"
            
        print(f"{title}")
        print(f"  Configuration: Relic ID {relic_id} | Buffs: {buffs} | Curses: {curses}")
        print(f"  Result: {status} ({reason}) -> {result_str}")
        print("-" * 80)

    print(f"\nTest Summary: {passed_count}/{len(test_cases)} tests passed.")
    if passed_count == len(test_cases):
        print("All tests passed successfully!")
    else:
        print("Some tests failed.")

if __name__ == "__main__":
    run_tests()
