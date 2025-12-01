import unittest
from unittest.mock import MagicMock, patch

from services.google_service import GoogleCalendarClient
from services.microsoft_service import MicrosoftGraphClient


class NotificationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.google_client = GoogleCalendarClient('fake-token')
        self.microsoft_client = MicrosoftGraphClient('fake-token')

    def test_google_blocker_payload_sanitization(self):
        payload = {
            'summary': '[Mirror] Busy',
            'attendees': [{'email': 'test@example.com'}],
            'reminders': {'useDefault': True}
        }
        sanitized = self.google_client._sanitize_blocker_payload(payload)
        self.assertEqual(sanitized['attendees'], [])
        self.assertEqual(sanitized['visibility'], 'private')
        self.assertEqual(sanitized['transparency'], 'opaque')
        self.assertFalse(sanitized['reminders']['useDefault'])

    @patch('services.google_service.requests.post')
    def test_google_create_event_disables_notifications(self, mock_post):
        response = MagicMock()
        response.json.return_value = {'id': 'evt'}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        self.google_client.create_calendar_event({'summary': '[Mirror] Busy'})

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['params']['sendUpdates'], 'none')
        self.assertEqual(kwargs['json']['attendees'], [])

    def test_microsoft_blocker_payload_sanitization(self):
        payload = {
            'subject': '[Mirror] Busy',
            'attendees': [{'emailAddress': {'address': 'a@b.com'}}],
            'isReminderOn': True
        }
        sanitized = self.microsoft_client._sanitize_blocker_payload(payload)
        self.assertEqual(sanitized['attendees'], [])
        self.assertEqual(sanitized['sensitivity'], 'private')
        self.assertEqual(sanitized['showAs'], 'busy')
        self.assertFalse(sanitized['isReminderOn'])

    @patch('services.microsoft_service.requests.post')
    def test_microsoft_create_event_disables_notifications(self, mock_post):
        response = MagicMock()
        response.json.return_value = {'id': 'evt'}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        self.microsoft_client.create_calendar_event({'subject': '[Mirror] Busy'})

        _, kwargs = mock_post.call_args
        sanitized_body = kwargs['json']
        self.assertEqual(sanitized_body['attendees'], [])
        self.assertFalse(sanitized_body['isReminderOn'])


if __name__ == '__main__':
    unittest.main()

