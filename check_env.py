"""Check environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

print("Environment Variables Check:")
print("=" * 80)
print(f"SPINE_URL: {os.getenv('SPINE_URL', 'Not Set')}")
print(f"SPINE_USERNAME: {os.getenv('SPINE_USERNAME', 'Not Set')}")
print(f"SPINE_PASSWORD: {'***' if os.getenv('SPINE_PASSWORD') else 'Not Set'}")
print(f"CHROMEDRIVER_PATH: {os.getenv('CHROMEDRIVER_PATH', 'Not Set')}")
print(f"CHROME_HEADLESS: {os.getenv('CHROME_HEADLESS', 'Not Set')}")
print("=" * 80)

# Check if USERNAME or PASSWORD is None
username = os.getenv('SPINE_USERNAME')
password = os.getenv('SPINE_PASSWORD')

if username is None:
    print("\n⚠️  ERROR: SPINE_USERNAME is None!")
if password is None:
    print("\n⚠️  ERROR: SPINE_PASSWORD is None!")

# Test iteration
if username is None:
    print("\nTesting iteration on None USERNAME:")
    try:
        for char in username:
            pass
    except TypeError as e:
        print(f"  TypeError: {e}")

if password is None:
    print("\nTesting iteration on None PASSWORD:")
    try:
        for char in password:
            pass
    except TypeError as e:
        print(f"  TypeError: {e}")
