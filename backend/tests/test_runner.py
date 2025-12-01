"""
Test Runner for End-to-End Testing
Executes all test suites and generates reports
"""
import sys
import os
import json
from datetime import datetime
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_api_endpoints import run_api_tests


class TestRunner:
    """Main test runner for comprehensive testing"""
    
    def __init__(self):
        self.results = {
            'start_time': datetime.now().isoformat(),
            'tests': {},
            'summary': {}
        }
    
    def run_api_tests(self):
        """Run API endpoint tests"""
        print("\n" + "="*60)
        print("RUNNING API ENDPOINT TESTS")
        print("="*60)
        try:
            success = run_api_tests()
            self.results['tests']['api_endpoints'] = {
                'status': 'PASS' if success else 'FAIL',
                'timestamp': datetime.now().isoformat()
            }
            return success
        except Exception as e:
            print(f"API tests failed: {e}")
            self.results['tests']['api_endpoints'] = {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def check_backend_health(self):
        """Check if backend is running"""
        import requests
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print("✓ Backend is running")
                return True
            else:
                print(f"✗ Backend returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Backend is not running: {e}")
            print("  Please start the backend server: cd backend && python app.py")
            return False
    
    def check_database_connection(self):
        """Check database connection"""
        try:
            from app import create_app
            from config import Config
            from models.user_model import db
            from sqlalchemy import text
            
            app = create_app(Config)
            with app.app_context():
                db.session.execute(text('SELECT 1'))
                print("✓ Database connection successful")
                return True
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
    
    def verify_environment(self):
        """Verify testing environment"""
        print("\n" + "="*60)
        print("VERIFYING TEST ENVIRONMENT")
        print("="*60)
        
        checks = {
            'backend_health': self.check_backend_health(),
            'database_connection': self.check_database_connection()
        }
        
        self.results['environment'] = checks
        
        all_passed = all(checks.values())
        if all_passed:
            print("\n✓ All environment checks passed")
        else:
            print("\n✗ Some environment checks failed")
            print("  Please fix the issues above before running tests")
        
        return all_passed
    
    def generate_report(self):
        """Generate test report"""
        self.results['end_time'] = datetime.now().isoformat()
        
        # Calculate summary
        total_tests = len(self.results['tests'])
        passed = sum(1 for t in self.results['tests'].values() if t.get('status') == 'PASS')
        failed = sum(1 for t in self.results['tests'].values() if t.get('status') == 'FAIL')
        errors = sum(1 for t in self.results['tests'].values() if t.get('status') == 'ERROR')
        
        self.results['summary'] = {
            'total': total_tests,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'success_rate': f"{(passed/total_tests*100):.1f}%" if total_tests > 0 else "0%"
        }
        
        # Print summary
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        print(f"Total Test Suites: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Success Rate: {self.results['summary']['success_rate']}")
        print("="*60)
        
        # Save report
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nTest report saved to: {report_file}")
    
    def run_all(self):
        """Run all test suites"""
        print("\n" + "="*60)
        print("UNIFIED SMART CALENDAR SYSTEM - TEST RUNNER")
        print("="*60)
        
        # Verify environment first
        if not self.verify_environment():
            print("\nEnvironment verification failed. Please fix issues and try again.")
            return False
        
        # Run test suites
        print("\n" + "="*60)
        print("RUNNING TEST SUITES")
        print("="*60)
        
        # API tests
        self.run_api_tests()
        
        # Generate final report
        self.generate_report()
        
        return self.results['summary']['failed'] == 0 and self.results['summary']['errors'] == 0


def main():
    """Main entry point"""
    runner = TestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

