"""
evaluate_care_helper.py
Simple evaluation harness for the PawPal Care Coach helper.
Run with: python evaluate_care_helper.py
"""

from pawpal_ai import create_default_care_advisor
from pawpal_system import Pet


CASES = [
    {
        "pet": Pet(name="Luna", species="cat", age=5),
        "query": "My cat had loose stool after a sudden food change but is still active.",
        "expected_condition": "Digestive Issues",
        "expected_urgent": False,
    },
    {
        "pet": Pet(name="Mochi", species="dog", age=3),
        "query": "My dog's ear smells bad and he keeps scratching it.",
        "expected_condition": "Ear Infections",
        "expected_urgent": False,
    },
    {
        "pet": Pet(name="Rex", species="dog", age=7),
        "query": "I found worms in my dog's stool and now he seems itchy.",
        "expected_condition": "Parasites",
        "expected_urgent": False,
    },
    {
        "pet": Pet(name="Milo", species="dog", age=9),
        "query": "My dog has sudden severe abdominal distension and keeps vomiting.",
        "expected_condition": "Digestive Issues",
        "expected_urgent": True,
    },
]


def main():
    advisor = create_default_care_advisor()
    passed = 0

    print("PawPal Care Coach Evaluation")
    print("-" * 34)

    for index, case in enumerate(CASES, start=1):
        result = advisor.advise(case["pet"], case["query"])
        condition_ok = result.condition == case["expected_condition"]
        urgent_ok = result.is_urgent == case["expected_urgent"]
        case_passed = condition_ok and urgent_ok
        passed += int(case_passed)

        print(f"Case {index}: {'PASS' if case_passed else 'FAIL'}")
        print(f"  Query: {case['query']}")
        print(f"  Expected condition: {case['expected_condition']}")
        print(f"  Actual condition:   {result.condition}")
        print(f"  Expected urgent:    {case['expected_urgent']}")
        print(f"  Actual urgent:      {result.is_urgent}")
        print(f"  Confidence:         {result.confidence:.2f}")
        print(f"  Sources used:       {len(result.citations)}")
        print()

    print(f"Summary: {passed}/{len(CASES)} cases passed.")


if __name__ == "__main__":
    main()
