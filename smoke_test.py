#!/usr/bin/env python3
"""
Smoke test for Triumph OS deployment
Tests that all main routes are accessible and working
"""
import requests
import sys

# Base URL - update this to your Render URL
BASE_URL = "https://triumph-os.onrender.com"

# Routes to test
ROUTES = [
    ("/", "Dashboard"),
    ("/accounts", "Accounts"),
    ("/contacts", "Contacts"),
    ("/opportunities", "Opportunities"),
    ("/how-to-use", "How to Use"),
]

def test_route(path, name):
    """Test a single route"""
    url = BASE_URL + path
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"✓ {name:20} - OK (200)")
            return True
        else:
            print(f"✗ {name:20} - FAILED (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ {name:20} - ERROR: {str(e)}")
        return False

def main():
    """Run smoke tests"""
    print(f"\n🔍 Running smoke tests on {BASE_URL}\n")
    print("-" * 50)

    results = []
    for path, name in ROUTES:
        results.append(test_route(path, name))

    print("-" * 50)
    passed = sum(results)
    total = len(results)
    print(f"\n✅ Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All smoke tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
