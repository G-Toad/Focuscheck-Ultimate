#!/usr/bin/env python
"""Test challenge system."""

import sys
sys.path.insert(0, '.')

from focuscheck.ui.dialogs.challenge_system import ChallengeSystem

def test_studying_challenges():
    print("="*80)
    print("STUDYING CHALLENGES TEST")
    print("="*80)
    print()

    system = ChallengeSystem()

    # Test each studying challenge
    for challenge in system.studying_challenges:
        print(f"Challenge: {challenge['id']}")
        print(f"Question: {challenge['question']}")
        print(f"Hint: {system.get_challenge_hint(challenge)}")
        print()

        # Test valid response
        valid_responses = {
            "learning_specificity": "I'm learning how to solve quadratic equations in chapter 5",
            "goal_connection": "My goal is to pass the chemistry exam on Friday",
            "will_commitment": "I will finish reading chapter 3 and complete 10 practice problems",
            "output_expectation": "I'll have completed the essay introduction and first two paragraphs",
        }

        # Test invalid responses
        invalid_responses = {
            "learning_specificity": "studying stuff",  # Too vague, missing keyword
            "goal_connection": "to pass the test",  # Missing required word
            "will_commitment": "I will try to study",  # Contains banned weak word
            "output_expectation": "some work done",  # Missing required word, vague
        }

        if challenge['id'] in valid_responses:
            print("  Testing VALID response:")
            response = valid_responses[challenge['id']]
            is_valid, error = system.validate_challenge_response(response, challenge)
            print(f"    Input: '{response}'")
            print(f"    Result: {'PASS' if is_valid else 'FAIL'} {f'({error})' if error else ''}")
            print()

        if challenge['id'] in invalid_responses:
            print("  Testing INVALID response:")
            response = invalid_responses[challenge['id']]
            is_valid, error = system.validate_challenge_response(response, challenge)
            print(f"    Input: '{response}'")
            print(f"    Result: {'FAIL (correctly rejected)' if not is_valid else 'PASS (should have failed!)'}")
            print(f"    Error: {error}")
            print()

        print("-" * 80)
        print()

def test_wasting_challenges():
    print("="*80)
    print("WASTING TIME CHALLENGES TEST")
    print("="*80)
    print()

    system = ChallengeSystem()

    # Test each wasting challenge
    for challenge in system.wasting_challenges:
        print(f"Challenge: {challenge['id']}")
        print(f"Question: {challenge['question']}")
        print(f"Hint: {system.get_challenge_hint(challenge)}")
        print()

        # Test valid responses
        valid_responses = {
            "wasting_acknowledgment": "I'm wasting my last chance to prepare for tomorrow's test",
            "should_gap": "Scrolling Reddit instead of the essay I should be writing",
            "because_reasoning": "Because starting feels overwhelming and I'm afraid of failing",
            "hour_projection": "In another hour I'll have zero time left to finish the assignment",
            "tomorrow_regret": "Tomorrow I'll regret not using these free hours to study",
            "fear_acknowledgment": "I'm afraid the task is too hard and I'll fail anyway",
            "lying_confrontation": "I'm lying to myself that I'll start in 5 minutes",
        }

        # Test invalid responses
        invalid_responses = {
            "wasting_acknowledgment": "wasting time",  # Too generic (banned phrase)
            "should_gap": "watching videos",  # Missing 'should', no contrast
            "because_reasoning": "because reasons",  # Banned shallow phrase
            "hour_projection": "nothing will happen",  # Missing required word
            "tomorrow_regret": "no regrets",  # Denial pattern (banned)
            "fear_acknowledgment": "not scared",  # Denial pattern
            "lying_confrontation": "not lying",  # Denial pattern
        }

        if challenge['id'] in valid_responses:
            print("  Testing VALID response:")
            response = valid_responses[challenge['id']]
            is_valid, error = system.validate_challenge_response(response, challenge)
            print(f"    Input: '{response}'")
            print(f"    Result: {'PASS' if is_valid else 'FAIL'} {f'({error})' if error else ''}")
            print()

        if challenge['id'] in invalid_responses:
            print("  Testing INVALID response:")
            response = invalid_responses[challenge['id']]
            is_valid, error = system.validate_challenge_response(response, challenge)
            print(f"    Input: '{response}'")
            print(f"    Result: {'FAIL (correctly rejected)' if not is_valid else 'PASS (should have failed!)'}")
            print(f"    Error: {error}")
            print()

        print("-" * 80)
        print()

def main():
    test_studying_challenges()
    print("\n\n")
    test_wasting_challenges()

    # Test frequency
    print("="*80)
    print("CHALLENGE FREQUENCY TEST")
    print("="*80)
    print()

    system = ChallengeSystem()

    # Simulate 100 studying prompts
    studying_count = sum(1 for _ in range(100) if system.should_show_challenge("studying"))
    wasting_count = sum(1 for _ in range(100) if system.should_show_challenge("wasting"))

    print(f"Out of 100 prompts:")
    print(f"  Studying challenges appeared: {studying_count} times (~30% expected)")
    print(f"  Wasting challenges appeared: {wasting_count} times (~50% expected)")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
