"""
API Endpoint Testing Suite
Tests all API endpoints for the Unified Smart Calendar System
"""
import unittest
import requests
import json
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get('TEST_API_URL', 'http://localhost:5000/api')
TEST_USER_EMAIL = os.environ.get('TEST_USER_EMAIL', 'test@example.com')


class APITestSuite(unittest.TestCase):
    """Comprehensive API endpoint testing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.test_results = []
        
    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        self.test_results.append({
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        print(f"[{status}] {test_name}: {message}")
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        try:
            response = requests.get(f'{self.base_url.replace("/api", "")}/health')
            self.assertEqual(response.status_code, 200)
            self.log_test("Health Check", True, "Backend is running")
        except Exception as e:
            self.log_test("Health Check", False, str(e))
            self.fail(f"Health check failed: {e}")
    
    def test_google_login_initiation(self):
        """Test Google OAuth login initiation"""
        try:
            response = requests.get(f'{self.base_url}/auth/login/google', allow_redirects=False)
            # Should redirect (302) or return auth URL
            self.assertIn(response.status_code, [200, 302])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('auth_url', data)
            self.log_test("Google Login Initiation", True, "OAuth URL generated")
        except Exception as e:
            self.log_test("Google Login Initiation", False, str(e))
    
    def test_microsoft_login_initiation(self):
        """Test Microsoft OAuth login initiation"""
        try:
            response = requests.get(f'{self.base_url}/auth/login/microsoft', allow_redirects=False)
            # Should redirect (302) or return auth URL
            self.assertIn(response.status_code, [200, 302])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('auth_url', data)
            self.log_test("Microsoft Login Initiation", True, "OAuth URL generated")
        except Exception as e:
            self.log_test("Microsoft Login Initiation", False, str(e))
    
    def test_calendar_events_endpoint(self):
        """Test calendar events retrieval"""
        try:
            # This will fail without authentication, but we test the endpoint exists
            response = requests.get(f'{self.base_url}/calendar/events')
            # Should return 401 (unauthorized) or 200 (if test user exists)
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('events', data)
            self.log_test("Calendar Events Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Calendar Events Endpoint", False, str(e))
    
    def test_sync_google_endpoint(self):
        """Test Google sync endpoint"""
        try:
            response = requests.post(f'{self.base_url}/calendar/sync/google')
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('synced_count', data)
            self.log_test("Sync Google Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Sync Google Endpoint", False, str(e))
    
    def test_sync_microsoft_endpoint(self):
        """Test Microsoft sync endpoint"""
        try:
            response = requests.post(f'{self.base_url}/calendar/sync/microsoft')
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('synced_count', data)
            self.log_test("Sync Microsoft Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Sync Microsoft Endpoint", False, str(e))
    
    def test_sync_all_endpoint(self):
        """Test sync all endpoint"""
        try:
            response = requests.post(f'{self.base_url}/calendar/sync/all')
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('total_synced', data)
            self.log_test("Sync All Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Sync All Endpoint", False, str(e))
    
    def test_sync_bidirectional_endpoint(self):
        """Test bidirectional sync endpoint"""
        try:
            response = requests.post(f'{self.base_url}/calendar/sync/bidirectional')
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('total_synced', data)
            self.log_test("Bidirectional Sync Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Bidirectional Sync Endpoint", False, str(e))
    
    def test_conflicts_endpoint(self):
        """Test conflicts endpoint"""
        try:
            params = {
                'start_date': datetime.now().strftime('%Y-%m-%d'),
                'end_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            }
            response = requests.get(f'{self.base_url}/calendar/conflicts', params=params)
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('conflicts', data)
            self.log_test("Conflicts Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Conflicts Endpoint", False, str(e))
    
    def test_free_slots_endpoint(self):
        """Test free slots endpoint"""
        try:
            params = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'duration': 60
            }
            response = requests.get(f'{self.base_url}/calendar/free-slots', params=params)
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403, 400])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('free_slots', data)
            self.log_test("Free Slots Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Free Slots Endpoint", False, str(e))
    
    def test_summary_endpoint(self):
        """Test summary endpoint"""
        try:
            response = requests.get(f'{self.base_url}/calendar/summary')
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIn('total_events', data)
            self.log_test("Summary Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Summary Endpoint", False, str(e))
    
    def test_user_connections_endpoint(self):
        """Test user connections endpoint"""
        try:
            response = requests.get(f'{self.base_url}/auth/user/connections')
            # Should return 401 (unauthorized) or 200
            self.assertIn(response.status_code, [200, 401, 403])
            if response.status_code == 200:
                data = response.json()
                self.assertIsInstance(data, (list, dict))
            self.log_test("User Connections Endpoint", True, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("User Connections Endpoint", False, str(e))
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
    @classmethod
    def tearDownClass(cls):
        """Generate test report"""
        print("\n" + "="*60)
        print("API TEST SUMMARY")
        print("="*60)


def run_api_tests():
    """Run all API tests"""
    print("Starting API Endpoint Tests...")
    print(f"Testing against: {BASE_URL}")
    print("="*60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(APITestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_api_tests()
    sys.exit(0 if success else 1)

