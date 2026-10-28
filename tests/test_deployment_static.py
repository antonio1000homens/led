from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentStaticTests(unittest.TestCase):
    def test_admin_groups_departures_and_steam_train_without_brightness_card(self):
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("function departuresSectionHtml", admin)
        self.assertIn("Departures &amp; Steam Train", admin)
        self.assertIn("cardHtml('departures'", admin)
        self.assertIn("cardHtml('steam_train'", admin)  # Safe fallback if Rail schema is missing
        self.assertIn('data-rail-group="true"', admin)
        self.assertIn('data-rail-feed="', admin)
        self.assertIn("data-save-rail", admin)
        self.assertIn("railFeedFields('steam_train'", admin)
        self.assertIn("collectRailCard(card)", admin)
        self.assertNotIn("function displayCardHtml", admin)
        self.assertNotIn("displayCardHtml(config.display", admin)

    def test_admin_schedule_windows_offer_readable_duration_units(self):
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("const WINDOW_UNITS=[['minutes',1],['hours',60],['days',1440],['weeks',10080],['months',43200]]", admin)
        self.assertIn("duration_minutes:duration", admin)
        self.assertIn("Month means 30 days", admin)
        self.assertIn("windowDurationControl(60)", admin)

    def test_sl7_bus_uses_https_and_rejects_mqtt_override(self):
        mqtt = (ROOT / "hardware" / "matrixportal" / "firmware" / "mqtt_screens.py").read_text()
        bus = (ROOT / "hardware" / "matrixportal" / "firmware" / "bus_departures.py").read_text()
        provider = (ROOT / "backend" / "transitous_bus.py").read_text()
        rotation = (ROOT / "hardware" / "matrixportal" / "firmware" / "screen_client.py").read_text()
        code = (ROOT / "code.py").read_text()
        admin = (ROOT / "simulator" / "admin.html").read_text()
        self.assertIn('if slot.startswith("sl7-"):', mqtt)
        self.assertNotIn("def configure_bus(self, config):", mqtt)
        self.assertNotIn("mqtt_screens.configure_bus", code)
        self.assertIn('item.get("kind") != "bus_departures"', rotation)
        self.assertIn("Transitous / MOTIS · HTTPS API", admin)
        self.assertIn('STOP_KEYS = ("heathrow", "new-malden")', bus)
        self.assertIn("TransitousBusProvider", provider)
        self.assertIn("api.transitous.org/api", provider)

    def test_sl7_split_columns_use_nonoverlapping_four_row_layout(self):
        display = (ROOT / "hardware/matrixportal/firmware/display.py").read_text()
        simulator = (ROOT / "simulator/index.html").read_text()
        admin = (ROOT / "simulator/admin.html").read_text()
        runtime = (ROOT / "backend/runtime_config.py").read_text()
        publisher = (ROOT / "backend/publisher.py").read_text()
        self.assertIn('("new-malden", "SL7 to Heathrow", 0)', display)
        self.assertIn('("heathrow", "SL7 to New Malden", 128)', display)
        self.assertIn("y = 11 + index * 8", display)
        self.assertIn('time_text[:5], time_color, x + SL7_TIME_COLUMN_X, y', display)
        self.assertIn('self._label(group, prefix, due_color, x + SL7_DUE_COLUMN_X, y)', display)
        self.assertIn("drawLedText('Due in ', x + 42 * FONT_PIXEL_SCALE, y)", simulator)
        self.assertIn('kind == "bus_departures_combined"', display)
        self.assertIn("function drawSplitSl7(screen)", simulator)
        self.assertIn("const y = (8 + i * 8)", simulator)
        self.assertIn("drawSplitSl7(screen)", simulator)
        self.assertIn("layout_mode", runtime)
        self.assertIn("Side-by-side (default)", admin)
        self.assertIn('screens.append(self._bus_combined(', publisher)

    def test_simulator_renders_and_previews_bin_collection_screens(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function drawBinCollection(screen, phase)", simulator)
        self.assertIn("screen.kind === 'bin_collection'", simulator)
        self.assertIn("screen.collection_date", simulator)
        self.assertIn("drawLedText(dueLabel, dueX, 14 * FONT_PIXEL_SCALE);", simulator)
        self.assertIn("drawBinLorry(x);", simulator)
        self.assertIn("for (const center of [12, 40])", simulator)
        self.assertIn("if (screen.stale || forceStale)", simulator)
        self.assertIn("Preview recycling screen", simulator)
        self.assertIn("id: 'homeassistant-next-bin'", simulator)

    def test_loading_upcoming_card_matches_upcoming_header_position(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        self.assertIn("id:'static-fallback',kind:'today'", simulator)
        self.assertNotIn("display.show_loading(", (ROOT / "code.py").read_text())
        self.assertIn("drawLedText(String(screen.title || 'UPCOMING').slice(0, 30), 0, HEADER_TEXT_Y);", simulator)
        self.assertIn("drawLedText(message, Math.max(0, (1024 - measureLedText(message).width) / 2), 18 * FONT_PIXEL_SCALE);", simulator)
        self.assertIn("self._label(group, title, 0xFFAA00, 0, 3)", display)
        self.assertIn("self._text(title, 0, 0, (255, 170, 0))", display)

    def test_simulator_preview_uses_full_available_width(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("main { width: 100%; padding: 28px; }", simulator)
        self.assertIn("canvas { display: block; width: 100%;", simulator)

    def test_production_deploy_enables_and_verifies_todoist(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn('LED_CALENDAR_SOURCE: "todoist"', workflow)
        self.assertIn('hosting_bucket=$(output HostingBucketName)', workflow)
        self.assertIn("Verify Todoist screen is live", workflow)
        self.assertIn("calendar.get('source') != 'todoist'", workflow)
        self.assertIn("calendar.get('stale')", workflow)

    def test_static_deploy_uploads_current_simulator_html(self):
        deploy_static = (ROOT / "scripts" / "deploy-static.sh").read_text(encoding="utf-8")
        self.assertIn('simulator/index.html', deploy_static)
        self.assertIn('s3://${BUCKET}/index.html', deploy_static)
        self.assertIn("--paths '/index.html' '/api/screens'", deploy_static)

    def test_simulator_keeps_static_clock_and_uses_weather_sprites(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function drawWeatherSprite(name, x, y, stale, scale = WEATHER_SPRITE_SCALE, solar = false)", simulator)
        self.assertIn("drawWeatherSprite(iconName, iconX, 40, stale);", simulator)
        self.assertIn("drawClock(clock);", simulator)
        self.assertNotIn("weatherIcons", simulator)

    def test_simulator_reuses_top_level_shared_weather_for_screens(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("const sharedWeather = payload.weather", simulator)
        self.assertIn("screen.weather = sharedWeather", simulator)

    def test_simulator_has_three_fullscreen_weather_screens(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function drawWeeklyWeather(screen)", simulator)
        self.assertIn("function drawTodayWeather(screen)", simulator)
        self.assertIn("function drawSunWeather(screen, phase)", simulator)
        self.assertIn("SUN_WEATHER_ANIMATION_SECONDS", simulator)
        self.assertIn("screen.kind === 'weather_weekly'", simulator)
        self.assertIn("screen.kind === 'weather_today'", simulator)
        self.assertIn("screen.kind === 'weather_sun'", simulator)
        self.assertIn("Math.floor(index * 1024 / 7)", simulator)
        self.assertIn("Math.floor(index * 1024 / 6)", simulator)
        self.assertIn("status.dataset.detail = '7-day weather forecast';", simulator)
        self.assertIn("status.dataset.detail = 'Next 24 hours in rolling four-hour snapshots';", simulator)
        self.assertIn("status.dataset.detail = 'Today sunrise and sunset';", simulator)
        self.assertIn("suppressHeader = true;", simulator)

    def test_simulator_hides_all_day_time_and_renders_due_countdown(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("event.all_day || rawTimeText.toUpperCase() === 'ALL'", simulator)
        self.assertIn("function calendarDueText(event, now = new Date())", simulator)
        self.assertIn("return 'DUE TODAY';", simulator)
        self.assertIn("return `DUE IN ${dayDelta}d`;", simulator)
        self.assertIn("drawCalendarDue(events, wallClock", simulator)
        self.assertIn("timeZone: 'Europe/London'", simulator)

    def test_todoist_due_labels_are_day_only_and_row_level(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        self.assertIn("function todoistDueLabel(event, now = new Date())", simulator)
        self.assertIn("return 'TODAY';", simulator)
        self.assertIn("screen.source === 'todoist'", simulator)
        self.assertIn("todoist_due_label(events[event_index], clock_date)", display)
        self.assertIn('screen.get("source") == "todoist"', display)

    def test_simulator_does_not_pretruncate_agenda_rows(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("return parts.when + ' ' + parts.title;", simulator)
        self.assertNotIn("String(event.title || event.location || 'Event')).slice(0, 32)", simulator)

    def test_simulator_keeps_agenda_date_time_fixed_while_title_scrolls(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function agendaTitleX(title, phase, startX)", simulator)
        self.assertIn("const titleStart = measureLedText(parts.when + ' ').width;", simulator)
        self.assertIn("context.rect(titleStart, 32, 1024 - titleStart, 96);", simulator)
        self.assertIn("drawLedText(parts.title, agendaTitleX(parts.title, titlePhase, titleStart), y);", simulator)
        self.assertIn("drawLedText(parts.when, 0, y);", simulator)

    def test_simulator_rail_uses_spare_line_and_runtime_marquee_settings(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("const RAIL_MARQUEE_DELAY_SECONDS = 1.2;", simulator)
        self.assertIn("const RAIL_MARQUEE_SPEED = 120;", simulator)
        self.assertIn("const RAIL_MARQUEE_GAP = 112;", simulator)
        self.assertIn("return { services: services.slice(0, 1 + count) };", simulator)
        self.assertIn("function railRows(services, phase, summarySeconds = RAIL_SUMMARY_SECONDS, callingSeconds = RAIL_CALLING_SECONDS)", simulator)
        self.assertIn("RAIL_ROW_Y[rowIndex]", simulator)
        self.assertIn("drawRailService(row.service, y, 0, headerRight", simulator)
        self.assertNotIn("context.fillText('UPCOMING', 0, 64);", simulator)
        self.assertIn("stationMarqueeSpeed(screen)", simulator)
        self.assertIn("function stationMarqueeGap()", simulator)
        self.assertIn("return RAIL_MARQUEE_GAP;", simulator)
        self.assertIn("function stationSeparator(service)", simulator)
        self.assertIn("service.station_spacing_px", simulator)

    def test_simulator_right_aligns_rail_and_queue_state_to_display_edge(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function drawRailService(service, y, xOffset, rightEdge, color, ordinal = 1)", simulator)
        self.assertIn("rightEdge - measureLedText(state).width", simulator)
        self.assertIn("function drawQueueRide(ride, y, rightEdge)", simulator)
        self.assertIn("const QUEUE_ROW_HEIGHT = CONTENT_ROW_HEIGHT;", simulator)
        self.assertIn("drawQueueRide(ride, CONTENT_FIRST_Y + slot * QUEUE_ROW_HEIGHT - yOffset, 1024);", simulator)

    def test_simulator_hardware_preview_matches_matrix_constraints(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="hardware-preview"', simulator)
        self.assertIn("let hardwarePreview = true;", simulator)
        self.assertIn("const MATRIX_REFRESH_FPS = 7;", simulator)
        self.assertIn("logicalCanvas.width = 256;", simulator)
        self.assertIn("logicalCanvas.height = 32;", simulator)
        self.assertIn("const FONT_5X7 =", simulator)
        self.assertIn("function drawLedText(value, x, y)", simulator)
        self.assertIn("function quantizeRgb(red, green, blue)", simulator)
        self.assertIn("[64, 128, 192].forEach", simulator)
        self.assertIn("const TODOIST_MARQUEE_SPEED = 7 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const TODOIST_MARQUEE_PAUSE_SECONDS = 1.5;", simulator)
        self.assertIn("const CLOCK_X = 231 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const STALE_X = 190 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const RAIL_ROW_Y = [4, 12, 20, 28].map(value => value * FONT_PIXEL_SCALE);", simulator)
        self.assertIn("const CONTENT_FIRST_Y = 8 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const AGENDA_FIRST_Y = 11 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const UPCOMING_FIRST_Y = 17 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("presentPreview();", simulator)
        self.assertNotIn("context.font = '24px monospace';", simulator)

    def test_physical_renderer_uses_both_departure_rows_and_clips_agenda_title(self):
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        self.assertIn("RAIL_ROW_Y", display)
        self.assertIn("rail_rows(services, phase, calling_seconds, summary_seconds)", display)
        self.assertIn('self._label(group, "DEPARTURES", 0xFFAA00, 0, y)', display)
        self.assertIn('self._mask(group, 0, y - 3, AGENDA_TITLE_X, AGENDA_ROW_HEIGHT)', display)
        self.assertIn('self._label(group, when, 0xFFFFFF, 0, y)', display)

    def test_steam_train_intro_is_fullscreen_configurable_and_persistent(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        code = (ROOT / "code.py").read_text(encoding="utf-8")
        self.assertIn("screen.kind === 'steam_train_intro'", simulator)
        self.assertIn("function drawSteamTrain(screen, phase)", simulator)
        self.assertIn("STEAM_TRAIN_TEXT_GAP", simulator)
        self.assertIn('kind == "steam_train_intro"', display)
        self.assertIn("def _show_steam_train", display)
        self.assertIn("self._steam_train_motion_group.x = next_x", display)
        self.assertIn("Animation speed", admin)
        self.assertIn("Trailing words", admin)
        self.assertIn("type=\"text\"", admin)
        self.assertIn("def _smooth_steam_train", code)

    def test_no_services_page_suppresses_normal_departure_chrome(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("if (screen.empty_state) {", simulator)
        self.assertIn("suppressHeader = true;", simulator)
        self.assertIn('empty_state = screen.get("empty_state")', display)
        self.assertIn("No services duration", admin)

    def test_admin_weather_card_exposes_named_screen_controls(self):
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("function weatherCardHtml", admin)
        self.assertIn("7-day overview", admin)
        self.assertIn("Next 24 hours · six blocks", admin)
        self.assertIn("Sunrise / sunset", admin)
        self.assertIn("today_duration_seconds", admin)
        self.assertIn("sun_duration_seconds", admin)
        self.assertNotIn("day_0_enabled", admin)

    def test_admin_exposes_standalone_today_separately_from_next_24_hours(self):
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("if(feedId==='today')return cardHtml(feedId,feed,schema", admin)
        self.assertIn("todayNote=feedId==='today'", admin)
        self.assertIn("Today · current conditions", admin)
        self.assertIn("Next 24 hours (six forecast blocks)", admin)
        self.assertIn("labels.enabled=['Enabled','show the standalone current-conditions screen", admin)
        self.assertIn("labels.screen_duration_seconds=['Today screen duration'", admin)
        self.assertIn("if(feedId==='weather')return weatherCardHtml", admin)
        self.assertIn("encodeURIComponent(feedId)", admin)

    def test_admin_bootstraps_access_before_fetching_api(self):
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="icon" href="data:,">', admin)
        self.assertIn("window.location.replace(`${API}/session`);", admin)
        self.assertIn("window.history.replaceState(null,'','/admin'+restoredHash);", admin)
        self.assertIn("window.sessionStorage.setItem('led-admin-return-hash'", admin)
        self.assertIn('<details class="feed-advanced"><summary>Advanced</summary>', admin)


if __name__ == "__main__":
    unittest.main()
