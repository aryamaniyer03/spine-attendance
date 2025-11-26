"""Test script - running clock flows WITH BROWSER VISIBLE (not headless)."""

from automation import clock_in, clock_out

print("=" * 80)
print("TESTING CLOCK IN FLOW (NON-HEADLESS - BROWSER VISIBLE)")
print("=" * 80)
result = clock_in(headless=False)
print(f"\nResult: {result}")
print("\n")

print("=" * 80)
print("TESTING CLOCK OUT FLOW (NON-HEADLESS - BROWSER VISIBLE)")
print("=" * 80)
result = clock_out(headless=False)
print(f"\nResult: {result}")
print("\n")
