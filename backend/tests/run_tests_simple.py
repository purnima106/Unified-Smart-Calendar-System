"""
Simple test execution script with explicit output
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*60)
print("Running Feature Verification...")
print("="*60)
sys.stdout.flush()

try:
    from verify_features import FeatureVerifier
    verifier = FeatureVerifier()
    success = verifier.run_all()
    print(f"\nFeature verification: {'PASSED' if success else 'FAILED'}")
    sys.stdout.flush()
except Exception as e:
    print(f"Error running feature verification: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()

print("\n" + "="*60)
print("Running API Endpoint Tests...")
print("="*60)
sys.stdout.flush()

try:
    from test_api_endpoints import run_api_tests
    success = run_api_tests()
    print(f"\nAPI tests: {'PASSED' if success else 'FAILED'}")
    sys.stdout.flush()
except Exception as e:
    print(f"Error running API tests: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()

print("\n" + "="*60)
print("Test execution complete!")
print("="*60)
sys.stdout.flush()

