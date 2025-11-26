"""Test script to run clock in and clock out flows in headless mode."""

from automation import clock_in, clock_out

print("=" * 80)
print("TESTING CLOCK IN FLOW (HEADLESS)")
print("=" * 80)
result = clock_in(headless=True)
print(f"\nResult: {result}")
print("\n")

print("=" * 80)
print("TESTING CLOCK OUT FLOW (HEADLESS)")
print("=" * 80)
result = clock_out(headless=True)
print(f"\nResult: {result}")
print("\n")
