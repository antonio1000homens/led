"""Optional CircuitPython MQTT transport for issue #74.

This module is intentionally not imported unless both safety flags in
``settings.py`` are enabled. It contains no credentials or broker defaults.
"""


class FlashMqttClient:
    def __init__(self, settings, on_message, mqtt_factory=None):
        self.settings = settings
        self.on_message = on_message
        self.mqtt_factory = mqtt_factory
        self.client = None
        self.connected = False
        self.next_attempt = 0

    def _connect(self, now):
        if now < self.next_attempt:
            return
        if not self.settings.MQTT_BROKER:
            return
        try:
            if self.mqtt_factory is None:
                import adafruit_connection_manager
                import adafruit_minimqtt.adafruit_minimqtt as MQTT
                import wifi

                if not wifi.radio.connected:
                    wifi.radio.connect(self.settings.WIFI_SSID, self.settings.WIFI_PASSWORD)
                pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
                self.client = MQTT.MQTT(
                    broker=self.settings.MQTT_BROKER,
                    port=self.settings.MQTT_PORT,
                    username=self.settings.MQTT_USERNAME or None,
                    password=self.settings.MQTT_PASSWORD or None,
                    socket_pool=pool,
                    socket_timeout=0.5,
                )
            else:
                self.client = self.mqtt_factory(self.settings)
            self.client.on_message = lambda client, topic, message: self.on_message(message)
            self.client.connect()
            self.client.subscribe(self.settings.MQTT_TOPIC, qos=1)
            self.connected = True
            print("MQTT subscribed topic={}".format(self.settings.MQTT_TOPIC))
        except Exception as error:
            self._discard_client()
            self.next_attempt = now + 30
            print("MQTT unavailable:", error)

    def _discard_client(self):
        client = self.client
        self.connected = False
        self.client = None
        if client is not None:
            try:
                disconnect = getattr(client, "disconnect", None)
                if disconnect is not None:
                    disconnect()
            except Exception:
                pass

    def poll(self, now):
        self._connect(now)
        if not self.client or not self.connected:
            return
        try:
            # MiniMQTT requires the loop timeout to be at least the socket
            # timeout configured above. Keep both bounded so MQTT remains
            # subordinate to the render loop without rejecting every poll.
            self.client.loop(timeout=0.5)
        except Exception as error:
            self._discard_client()
            self.next_attempt = now + 5
            print("MQTT disconnected:", error)
