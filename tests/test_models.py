import unittest

from models import service_from_api, services_from_board


class ModelTests(unittest.TestCase):
    def test_normalizes_destination_and_delay(self):
        item = {"std": "12:04", "etd": "12:06", "destination": [{"locationName": "Waterloo"}], "platform": "1"}
        result = service_from_api(item)
        self.assertEqual(result["destination"], "Waterloo")
        self.assertEqual(result["status"], "12:06")

    def test_missing_services_is_empty(self):
        self.assertEqual(services_from_board({}), [])
