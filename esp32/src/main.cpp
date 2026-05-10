/**
 * CardioIA — Fase 3 (protótipo Wokwi / ESP32)
 *
 * Sensores: DHT22 (temperatura + umidade) e botões BPM+ / BPM− (base 60 + 10 × toques; − remove um passo).
 * Wi-Fi simulado: booleano controlado por botão (GPIO18) — cada toque alterna online/offline.
 * Com "online" simulado: drena a fila — Serial (sempre sem secrets) ou MQTT (com secrets.h).
 *
 * MQTT: copie src/secrets.h.example → src/secrets.h e preencha Wi-Fi + HiveMQ Cloud.
 * TLS: uso de setInsecure() para simplificar o laboratório; em produção fixar CA raiz.
 *
 * Pinos: DHT22 → GPIO15; BPM+ → GPIO4; BPM− → GPIO5; Wi‑Fi sim → GPIO18 (INPUT_PULLUP, ativo em LOW).
 */

#include <Arduino.h>
#include <DHTesp.h>
#include <cstring>

#if __has_include("secrets.h")
#include "secrets.h"
#ifndef CARDIOIA_SERIAL_MIRROR
#define CARDIOIA_SERIAL_MIRROR 0
#endif
#define CARDIOIA_USE_MQTT 1
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#else
#define CARDIOIA_USE_MQTT 0
#endif

// --- Hardware ---
static const int PIN_DHT = 15;
static const int PIN_BPM_UP = 4;
static const int PIN_BPM_DOWN = 5;
static const int PIN_WIFI_SIM_TOGGLE = 18;

// --- Amostragem e “rede” simulada ---
static const unsigned long SAMPLE_INTERVAL_MS = 1000;
static const unsigned long BTN_DEBOUNCE_MS = 150;
/** BPM simulado: base + (10 × toques válidos); teto evita valores irreais. */
static const int BPM_SIM_BASE = 60;
static const int BPM_PER_TOUCH = 10;
static const int BPM_SIM_MAX = 250;

// Fila offline (RAM). SPIFFS é opcional em hardware real; no Wokwi é volátil.
static const size_t MAX_QUEUE = 512;
static const char *DEVICE_ID = "esp32-wokwi-01";

struct Sample {
  uint32_t ts_ms;
  float temp_c;
  float hum_pct;
  int bpm_sim;
  bool dht_ok;
};

static Sample g_queue[MAX_QUEUE];
static size_t g_qHead = 0;
static size_t g_qTail = 0;
static size_t g_qCount = 0;

static DHTesp dhtSensor;

static unsigned g_bpmTouchCount = 0;

static int bpmSimFromTouches() {
  return BPM_SIM_BASE + BPM_PER_TOUCH * static_cast<int>(g_bpmTouchCount);
}

static int g_btnUpStable = HIGH;
static int g_btnUpLastRead = HIGH;
static unsigned long g_btnUpLastDebounce = 0;
static int g_btnDownStable = HIGH;
static int g_btnDownLastRead = HIGH;
static unsigned long g_btnDownLastDebounce = 0;
static int g_btnWifiStable = HIGH;
static int g_btnWifiLastRead = HIGH;
static unsigned long g_btnWifiLastDebounce = 0;

static void pollPullupButton(int pin, int *stable, int *lastRead, unsigned long *lastDebounce,
                             void (*onLowEdge)()) {
  const int reading = digitalRead(pin);
  const uint32_t now = millis();
  if (reading != *lastRead) {
    *lastDebounce = now;
    *lastRead = reading;
  }
  if (now - *lastDebounce > 20) {
    if (reading != *stable) {
      *stable = reading;
      if (*stable == LOW) onLowEdge();
    }
  }
}

static bool g_wifiSimConnected = true;

static unsigned long g_lastSampleMs = 0;

#if CARDIOIA_USE_MQTT
static WiFiClientSecure g_tls;
static PubSubClient g_mqtt(g_tls);
static unsigned long g_lastWifiAttempt = 0;
static unsigned long g_lastMqttAttempt = 0;
#endif

static bool queuePush(const Sample &s) {
  if (g_qCount >= MAX_QUEUE) {
    g_qHead = (g_qHead + 1) % MAX_QUEUE;
    g_qCount--;
  }
  g_queue[g_qTail] = s;
  g_qTail = (g_qTail + 1) % MAX_QUEUE;
  g_qCount++;
  return true;
}

static bool queuePop(Sample *out) {
  if (g_qCount == 0 || out == nullptr) return false;
  *out = g_queue[g_qHead];
  g_qHead = (g_qHead + 1) % MAX_QUEUE;
  g_qCount--;
  return true;
}

static void recordPress() {
  static unsigned long s_lastPressMs = 0;
  const uint32_t now = millis();
  if (now - s_lastPressMs < BTN_DEBOUNCE_MS) return;
  s_lastPressMs = now;

  const int next = BPM_SIM_BASE + BPM_PER_TOUCH * (static_cast<int>(g_bpmTouchCount) + 1);
  if (next > BPM_SIM_MAX) return;
  g_bpmTouchCount++;
}

static void recordPressDown() {
  static unsigned long s_lastPressMs = 0;
  const uint32_t now = millis();
  if (now - s_lastPressMs < BTN_DEBOUNCE_MS) return;
  s_lastPressMs = now;
  if (g_bpmTouchCount > 0) g_bpmTouchCount--;
}

/** Cada pressão válida alterna “rede simulada” ON/OFF (debounce extra evita duplo toque). */
static void toggleWifiSimPressed() {
  static unsigned long s_lastToggleMs = 0;
  const uint32_t now = millis();
  if (now - s_lastToggleMs < 400) return;
  s_lastToggleMs = now;
  g_wifiSimConnected = !g_wifiSimConnected;
  Serial.print(F("wifi_sim (manual): "));
  Serial.println(g_wifiSimConnected ? F("ON — drena fila / MQTT") : F("OFF — só enfileira"));
}

static size_t formatTelemetryJson(const Sample &s, char *buf, size_t cap) {
  char tc[24];
  char hc[24];
  if (s.dht_ok) {
    snprintf(tc, sizeof(tc), "%.2f", (double)s.temp_c);
    snprintf(hc, sizeof(hc), "%.1f", (double)s.hum_pct);
  } else {
    strncpy(tc, "null", sizeof(tc));
    tc[sizeof(tc) - 1] = '\0';
    strncpy(hc, "null", sizeof(hc));
    hc[sizeof(hc) - 1] = '\0';
  }
  return snprintf(
      buf, cap,
      "{\"schema\":\"cardioia.telemetry.v1\",\"device_id\":\"%s\",\"ts_ms\":%u,\"temp_c\":%s,\"hum_pct\":%s,"
      "\"bpm_sim\":%d,\"wifi_sim\":%s,\"queue_depth\":%u,\"batch\":false}",
      DEVICE_ID, static_cast<unsigned>(s.ts_ms), tc, hc, s.bpm_sim,
      g_wifiSimConnected ? "true" : "false", static_cast<unsigned>(g_qCount));
}

static void printJsonLine(const Sample &s) {
  char buf[384];
  const size_t n = formatTelemetryJson(s, buf, sizeof(buf));
  if (n < sizeof(buf)) Serial.print(buf);
  Serial.print('\n');
}

static void drainQueueToSerial() {
  Sample s;
  while (queuePop(&s)) printJsonLine(s);
}

#if CARDIOIA_USE_MQTT
static void tryWifiConnect() {
  if (WiFi.status() == WL_CONNECTED) return;
  const uint32_t now = millis();
  if (now - g_lastWifiAttempt < 8000) return;
  g_lastWifiAttempt = now;
  WiFi.mode(WIFI_STA);
#ifdef CARDIOIA_WOKWI_SIM
  // Rede virtual do simulador — exige IoT Gateway (público ou privado) para internet/MQTT.
  // https://docs.wokwi.com/guides/esp32-wifi
  WiFi.begin("Wokwi-GUEST", "", 6);
  Serial.println(F("Wi-Fi (Wokwi): Wokwi-GUEST canal 6 — ative o IoT Gateway para HiveMQ"));
#else
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print(F("Wi-Fi: conectando a "));
  Serial.println(WIFI_SSID);
#endif
}

static bool tryMqttConnect() {
  if (WiFi.status() != WL_CONNECTED) return false;
  if (g_mqtt.connected()) return true;

  const uint32_t now = millis();
  if (now - g_lastMqttAttempt < 4000) return false;
  g_lastMqttAttempt = now;

  g_tls.setInsecure();
  g_mqtt.setServer(MQTT_HOST, static_cast<uint16_t>(MQTT_PORT));
  g_mqtt.setBufferSize(512);

  char clientId[56];
  const uint64_t mac = ESP.getEfuseMac();
  snprintf(clientId, sizeof(clientId), "%s-%04X%04X", DEVICE_ID,
           static_cast<unsigned>((mac >> 32) & 0xFFFF), static_cast<unsigned>(mac & 0xFFFF));

  if (g_mqtt.connect(clientId, MQTT_USER, MQTT_PASS)) {
    Serial.println(F("MQTT: conectado ao broker"));
    return true;
  }
  Serial.print(F("MQTT: falha, estado="));
  Serial.println(g_mqtt.state());
  return false;
}

/** Com Wi-Fi real + MQTT: drena por publish. Sem Wi-Fi: cai no Serial (ex.: Wokwi sem gateway). */
static void drainQueueTransport() {
  if (!g_wifiSimConnected) return;

#if CARDIOIA_USE_MQTT
  if (WiFi.status() != WL_CONNECTED) {
    tryWifiConnect();
    drainQueueToSerial();
    return;
  }

  if (!g_mqtt.connected() && !tryMqttConnect()) {
    return;
  }

  char buf[384];
  Sample s;
  while (queuePop(&s)) {
    const size_t n = formatTelemetryJson(s, buf, sizeof(buf));
    if (n >= sizeof(buf)) continue;
    g_mqtt.publish(MQTT_TOPIC_TELEMETRY, buf, false);
    g_mqtt.loop();
#if CARDIOIA_SERIAL_MIRROR
    Serial.println(buf);
#endif
  }
#else
  drainQueueToSerial();
#endif
}
#else
static void drainQueueTransport() { drainQueueToSerial(); }
#endif

static void readButtons() {
  pollPullupButton(PIN_BPM_UP, &g_btnUpStable, &g_btnUpLastRead, &g_btnUpLastDebounce, recordPress);
  pollPullupButton(PIN_BPM_DOWN, &g_btnDownStable, &g_btnDownLastRead, &g_btnDownLastDebounce,
                   recordPressDown);
  pollPullupButton(PIN_WIFI_SIM_TOGGLE, &g_btnWifiStable, &g_btnWifiLastRead, &g_btnWifiLastDebounce,
                   toggleWifiSimPressed);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(PIN_BPM_UP, INPUT_PULLUP);
  pinMode(PIN_BPM_DOWN, INPUT_PULLUP);
  pinMode(PIN_WIFI_SIM_TOGGLE, INPUT_PULLUP);
  dhtSensor.setup(PIN_DHT, DHTesp::DHT22);

#if CARDIOIA_USE_MQTT
  WiFi.mode(WIFI_STA);
#ifdef CARDIOIA_WOKWI_SIM
  Serial.println(F("CardioIA Fase 3 — MQTT + Wokwi-GUEST. Wi-Fi sim: botão GPIO18 (toggle ON/OFF)."));
#else
  Serial.println(F("CardioIA Fase 3 — MQTT (secrets.h). Wi-Fi sim: botão GPIO18 (toggle ON/OFF)."));
#endif
#else
  Serial.println(F("CardioIA Fase 3 — só Serial. Wi-Fi sim: botão GPIO18 (toggle ON/OFF)."));
#endif
}

void loop() {
  readButtons();

#if CARDIOIA_USE_MQTT
  if (g_wifiSimConnected) tryWifiConnect();
  if (WiFi.status() == WL_CONNECTED) {
    if (!g_mqtt.connected()) tryMqttConnect();
  }
  g_mqtt.loop();
#endif

  const uint32_t now = millis();

  if (g_wifiSimConnected) {
    drainQueueTransport();
  }

  if (now - g_lastSampleMs >= SAMPLE_INTERVAL_MS) {
    g_lastSampleMs = now;

    TempAndHumidity d = dhtSensor.getTempAndHumidity();
    const bool dht_ok = (dhtSensor.getStatus() == 0);

    Sample s;
    s.ts_ms = now;
    s.temp_c = dht_ok ? d.temperature : NAN;
    s.hum_pct = dht_ok ? d.humidity : NAN;
    s.bpm_sim = bpmSimFromTouches();
    s.dht_ok = dht_ok;

    queuePush(s);
  }

  delay(2);
}
