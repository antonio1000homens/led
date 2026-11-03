"""Optional CircuitPython MQTT transport for flash events and cycle screens.

This module is intentionally not imported unless both local opt-in flags are
enabled. It contains no credentials or broker defaults.
"""

from diagnostic_counter import event as diagnostic_event
from monotonic_clock import ticks_ms

MQTT_LOOP_INTERVAL_SECONDS = 1.5
MQTT_IDLE_INTERVAL_SECONDS = 5.0
MQTT_POLL_INTERVAL_CHOICES = (1.5, 2, 3, 5, 10, 15, 30)
MQTT_STATS_INTERVAL_SECONDS = 60
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
        self.adaptive_polling = True
        self.idle_poll_seconds = MQTT_IDLE_INTERVAL_SECONDS
        self.live_poll_seconds = MQTT_LOOP_INTERVAL_SECONDS
        self.live_match = False
        self.poll_count = 0
        self.poll_max_ms = 0
        self.message_count = 0
        self.connect_successes = 0
        self.connect_failures = 0
        self._last_report_at = None

    def effective_poll_seconds(self):
        return self.live_poll_seconds if self.adaptive_polling and self.live_match else self.idle_poll_seconds

    def configure_polling(self, display_config, now):
        """Apply backend settings without reconnecting; ignore invalid/legacy payloads."""
        if not isinstance(display_config, dict):
            return False
        keys = ("mqtt_adaptive_enabled", "mqtt_idle_poll_seconds", "mqtt_live_poll_seconds")
        if not all(key in display_config for key in keys):
            return False
        adaptive, idle, live = (display_config[key] for key in keys)
        if type(adaptive) is not bool:
            return False
        if any(type(value) not in (int, float) or value not in MQTT_POLL_INTERVAL_CHOICES
               for value in (idle, live)):
            return False
        previous = self.effective_poll_seconds()
        changed = (adaptive != self.adaptive_polling or idle != self.idle_poll_seconds
                   or live != self.live_poll_seconds)
        self.adaptive_polling = adaptive
        self.idle_poll_seconds = float(idle)
        self.live_poll_seconds = float(live)
        if changed:
            self._reschedule_for_policy(now, previous)
        return changed

    def set_live_match(self, active, now):
        active = bool(active)
        if self.live_match == active:
            return False
        previous = self.effective_poll_seconds()
        self.live_match = active
        self._reschedule_for_policy(now, previous)
        return True

    def _reschedule_for_policy(self, now, previous_interval):
        interval = self.effective_poll_seconds()
        if self.connected:
            due = float(now) + interval
            # Never enqueue catch-up polls. Shorten the deadline for live
            # updates, lengthen it after POST or stale match expiry.
            self.next_loop = min(self.next_loop, due) if interval < previous_interval else max(self.next_loop, due)
        print("MQTT POLL POLICY mode={} interval_s={} adaptive={}".format(
            "live" if self.adaptive_polling and self.live_match else "idle",
            interval, self.adaptive_polling,
        ))

    def report_if_due(self, now):
        """Low-volume aggregate telemetry; avoid printing on every poll."""
        if self._last_report_at is None:
            self._last_report_at = float(now)
        if float(now) - self._last_report_at < MQTT_STATS_INTERVAL_SECONDS:
            return
        print("MQTT POLL STATS interval_s={} live={} polls={} max_poll_ms={} messages={} connects={} connect_failures={}".format(
            self.effective_poll_seconds(),
            self.adaptive_polling and self.live_match,
            self.poll_count, self.poll_max_ms, self.message_count,
            self.connect_successes, self.connect_failures,
        ))
        self._last_report_at = float(now)
        self.poll_count = 0
        self.poll_max_ms = 0
        self.message_count = 0
        self.connect_successes = 0
        self.connect_failures = 0

    def set_enabled(self, enabled):
        """Apply the admin runtime gate and close the connection when disabled."""
        enabled = bool(enabled)
        if self.enabled == enabled:
            return
        self.enabled = enabled
        if not enabled:
            self._discard_client()
            self.next_attempt = 0

    def _handle_message(self, client, topic, message):
        """Keep application callback failures from tearing down MQTT transport."""
        self.message_count += 1
        try:
            self.on_message(topic, message)
        except Exception as error:
            # Do not log the payload: timer messages can contain user labels.
            print("MQTT message handler failed type={}".format(
                type(error).__name__))

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
            self.client.on_message = self._handle_message
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
            self.connect_successes += 1
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
            self.connect_failures += 1
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
            poll_started = ticks_ms()
            try:
                self.client.loop(timeout=MQTT_SOCKET_TIMEOUT_SECONDS)
            finally:
                diagnostic_event(
                    "MQTT_POLL", "DONE",
                    "timeout_ms=10 duration_ms={}".format(ticks_ms() - poll_started),
                )
            self.next_loop = now + self.effective_poll_seconds()
            self.poll_count += 1
            self.poll_max_ms = max(self.poll_max_ms, ticks_ms() - poll_started)
        except Exception as error:
            self._discard_client()
            self.next_attempt = now + 5
            print("MQTT disconnected type={}".format(type(error).__name__))
