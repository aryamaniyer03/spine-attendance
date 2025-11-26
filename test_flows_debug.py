"""Debug test script to get full traceback."""

import traceback
from automation import clock_in, clock_out

print("=" * 80)
print("TESTING CLOCK IN FLOW (HEADLESS) - WITH FULL TRACEBACK")
print("=" * 80)
try:
    result = clock_in(headless=True)
    print(f"\nResult: {result}")
except Exception as e:
    print(f"\nException caught: {e}")
    print("\nFull traceback:")
    traceback.print_exc()

print("\n" * 2)
print("=" * 80)
print("TESTING CLOCK OUT FLOW (HEADLESS) - WITH FULL TRACEBACK")
print("=" * 80)
try:
    result = clock_out(headless=True)
    print(f"\nResult: {result}")
except Exception as e:
    print(f"\nException caught: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
