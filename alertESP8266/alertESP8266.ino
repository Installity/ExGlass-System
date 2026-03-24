//PROGRAM ONBOARD ESP8266 BOARD FOR HANDLING ALERTS - BD STEM STARS
//I used this as a simple alert controller, on a second board. When the model on the laptop classified a frame as dangerous, it sent a request to this board, which then played a warning tone through the buzzer.

#include <ESP8266WiFi.h>

const char* ssid = "";
const char* password = "";

WiFiServer server(80);

const int speakerPin = 13;
const int mq7Pin = A0;
const int mq135Pin = A0;

void sendResponse(WiFiClient &client, String content, String type) {
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: " + type);
  client.println("Connection: close");
  client.println();
  client.println(content);
}

void playAlertTone() {
  for (int i = 0; i < 250; i++) {
    digitalWrite(speakerPin, HIGH);
    delayMicroseconds(500);
    digitalWrite(speakerPin, LOW);
    delayMicroseconds(500);
  }
}
//web server creation
String buildHomePage(int mq7Value, int mq135Value) {
  String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<title>ExGlass Sensor Server</title></head><body>";
  html += "<h2>ExGlass Sensor Server</h2>";
  html += "<p>MQ7 value: " + String(mq7Value) + "</p>";
  html += "<p>MQ135 value: " + String(mq135Value) + "</p>";
  html += "<p><a href='/alert'>Trigger alert</a></p>";
  html += "</body></html>";
  return html;
}

void setup() {
  Serial.begin(115200);
  pinMode(speakerPin, OUTPUT);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connected: ");
  Serial.println(WiFi.localIP());
//begin web server
  server.begin();
}

void loop() {
  WiFiClient client = server.available();
  if (!client) return;

  String request = client.readStringUntil('\r');
  request.trim();
  client.flush();

  if (request.startsWith("GET /alert")) {
    playAlertTone();
    sendResponse(client, "Alert triggered", "text/plain");
  } else {
    int mq7Value = analogRead(mq7Pin);
    int mq135Value = analogRead(mq135Pin);
    sendResponse(client, buildHomePage(mq7Value, mq135Value), "text/html");
  }

  client.stop();
}
