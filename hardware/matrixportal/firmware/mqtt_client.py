"""Optional CircuitPython MQTT transport for flash events and cycle screens.

This module is intentionally not imported unless both local opt-in flags are
enabled. It contains no credentials or broker defaults.
"""

MQTT_LOOP_INTERVAL_SECONDS = 1.5
MQTT_KEEP_ALIVE_SECONDS = 180
MQTT_SOCKET_TIMEOUT_SECONDS = 0.01


class FlashMqttClient:
    def __init__(
        self,
        settings,
        on_message,
        mqtt_factory=None,
        startup_delay_seconds=0.0,
        started_at=None,
        on_connecting=None,
    ):
        self.settings = settings
        self.on_message = on_message
        self.mqtt_factory = mqtt_factory
        startup_delay_seconds = float(startup_delay_seconds)
        if startup_delay_seconds < 0:
            raise ValueError("startup_delay_seconds must be non-negative")
        self.connect_after = 0.0
        if startup_delay_seconds:
            if started_at is None:
                import time

                started_at = time.monotonic()
            self.connect_after = float(started_at) + startup_delay_seconds
        self.client = None
        self.connected = False
        self.enabled = True
        self.next_attempt = 0
        self.next_loop = 0
        self.pending_screen_status = None
        self.pending_health = None
        self.on_connecting = on_connecting

    def set_enabled(self, enabled):
        """Apply the admin runtime gate and close the connection when disabled."""
        enabled = bool(enabled)
        if self.enabled == enabled:
            return
        self.enabled = enabled
        if not enabled:
            self._discard_client()
            self.next_attempt = 0

    def _connect(self, now):
        if self.client is not None and self.connected:
            return
        if now < self.next_attempt:
            return
        if not self.settings.MQTT_BROKER:
            return
        if self.on_connecting is not None:
            try:
                self.on_connecting()
            except Exception as error:
                print("MQTT health checkpoint skipped:", type(error).__name__)
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
                    keep_alive=MQTT_KEEP_ALIVE_SECONDS,
                    socket_timeout=MQTT_SOCKET_TIMEOUT_SECONDS,
                )
            else:
                self.client = self.mqtt_factory(self.settings)
            self.client.on_message = lambda client, topic, message: self.on_message(topic, message)
            self.client.connect()
            self.client.subscribe(self.settings.MQTT_TOPIC, qos=1)
            assistant_topic = getattr(
                self.settings, "MQTT_ASSISTANT_RESPONSE_TOPIC",
                "led/flash/assistant-response",
            )
            self.client.subscribe(assistant_topic, qos=1)
            screen_topic = getattr(self.settings, "MQTT_SCREENS_TOPIC", "led/screens/+")
            football_topic = getattr(self.settings, "MQTT_FOOTBALL_TOPIC", "led/football/+")
            timer_topic = getattr(self.settings, "MQTT_TIMER_TOPIC", "led/timer/+")
            self.client.subscribe(screen_topic, qos=1)
            self.client.subscribe(football_topic, qos=1)
            self.client.subscribe(timer_topic, qos=1)
            self.connected = True
            self.next_loop = now
            if self.pending_screen_status is not None:
                self.client.publish(
                    getattr(self.settings, "MQTT_BOARD_STATUS_TOPIC", "led/board/screen"),
                    self.pending_screen_status,
                    retain=True,
                    qos=0,
                )
                self.pending_screen_status = None
            if self.pending_health is not None:
                self.client.publish(
                    getattr(self.settings, "MQTT_BOARD_HEALTH_TOPIC", "led/board/health"),
                    self.pending_health,
                    retain=True,
                    qos=0,
                )
                self.pending_health = None
            print("MQTT subscribed reminder={} assistant={} screens={} football={} timer={}".format(
                self.settings.MQTT_TOPIC, assistant_topic, screen_topic, football_topic, timer_topic))
        except Exception as error:
            self._discard_client()
            self.next_attempt = now + 30
            print("MQTT unavailable:", error)

    def _discard_client(self):
        client = self.client
        self.connected = False
        self.client = None
        self.next_loop = 0
        if client is not None:
            try:
                disconnect = getattr(client, "disconnect", None)
                if disconnect is not None:
                    disconnect()
            except Exception:
                pass

    def publish_screen_status(self, payload, now):
        """Publish the latest selected screen for an external stall watchdog."""
        topic = getattr(self.settings, "MQTT_BOARD_STATUS_TOPIC", "")
        if not self.enabled or not topic:
            return False
        if not self.connected or self.client is None:
            self.pending_screen_status = payload
            return False
        try:
            self.client.publish(topic, payload, retain=True, qos=0)
            return True
        except Exception as error:
            self.pending_screen_status = payload
            self._discard_client()
            self.next_attempt = now + 5
            print("MQTT screen status unavailable:", error)
            return False

    def publish_health(self, payload, now):
        """Publish the newest board health snapshot without blocking rendering."""
        topic = getattr(self.settings, "MQTT_BOARD_HEALTH_TOPIC", "led/board/health")
        if not self.enabled or not topic:
            return False
        if not self.connected or self.client is None:
            self.pending_health = payload
            return False
        try:
            self.client.publish(topic, payload, retain=True, qos=0)
            return True
        except Exception as error:
            self.pending_health = payload
            self._discard_client()
            self.next_attempt = now + 5
            print("MQTT health unavailable:", error)
            return False
    def poll(self, now, allow_connect=True):
        if not self.enabled:
            return
        # A Wi-Fi/MQTT handshake can block far longer than socket_timeout.
        # Avoid starting one in the middle of a visible animation.
        if not self.client or not self.connected:
            if not allow_connect or now < self.connect_after:
                return
            self._connect(now)
        if not self.client or not self.connected:
            return
        if now < self.next_loop:
            return
        try:
            # Keep MiniMQTT's blocking read below one 8 FPS display frame.
            # Service transient events promptly while keeping reads below one frame.
            self.client.loop(timeout=MQTT_SOCKET_TIMEOUT_SECONDS)
            self.next_loop = now + MQTT_LOOP_INTERVAL_SECONDS
        except Exception as error:
            self._discard_client()
            self.next_attempt = now + 5
            print("MQTT disconnected:", error)
