"""National Rail LDBWS JSON client for MatrixPortal S3.

The API requires HTTP Basic Authentication. Responses are normalized before
they reach the renderer so a future sanitizing webservice can replace this
module without changing display code.
"""

import ssl
import binascii

import adafruit_requests
import socketpool
import wifi

from models import services_from_board


BASE_URL = "https://realtime.nationalrail.co.uk/LDBWS/api/20220120/GetDepartureBoard"


class NationalRailClient:
    def __init__(self, settings):
        self.settings = settings
        self.pool = socketpool.SocketPool(wifi.radio)
        self.session = adafruit_requests.Session(self.pool, ssl.create_default_context())

    def connect(self):
        if not wifi.radio.connected:
            wifi.radio.connect(self.settings.WIFI_SSID, self.settings.WIFI_PASSWORD)

    def fetch(self):
        self.connect()
        params = {"numRows": self.settings.MAX_ROWS, "timeWindow": 120}
        if self.settings.FILTER_CRS:
            params["filterCrs"] = self.settings.FILTER_CRS
            params["filterType"] = "to"
        response = None
        try:
            credentials = self.settings.NATIONAL_RAIL_USERNAME + ":" + self.settings.NATIONAL_RAIL_PASSWORD
            auth = binascii.b2a_base64(credentials.encode()).strip().decode()
            response = self.session.get(
                BASE_URL + "/" + self.settings.STATION_CRS.upper(),
                params=params,
                headers={"Authorization": "Basic " + auth, "Accept": "application/json"},
            )
            response.raise_for_status()
            return services_from_board(response.json())
        finally:
            if response is not None:
                response.close()
