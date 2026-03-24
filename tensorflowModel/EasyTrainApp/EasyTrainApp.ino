// ESP EASYTRAIN
// Developed for BD STEM STARS 2025 - ExGlass
//---------------------------------------
// This is an application that makes it seamless to train the 
// obstacle detection Tensorflow Model for the ExGlass System. 
//-------------------------------------------------------------
// This program works without much effort, simply choose the network you'd like to connect to in WIFI credentials,
// upload the code to your ESP32-CAM, and take photos. Whenever you are at a safe distance from an object, press the
// "safe" button, and it'll take a photo, and the same for the "close" button. SD card required in order for images to be saved to it.
// Program automatically creates a directory named DataTraining on your SD card (must be formatted in FAT32) and arranges photos that are safe and close in
// their corresponding folders within DataTraining.


#include "esp_camera.h"
#include "WiFi.h"
#include "SD_MMC.h"   // (FAT32 formatted)
#include "FS.h"
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// WiFi credentials 
const char* ssid = "";
const char* password = "";

// port of web server
WiFiServer server(80);

// Desired image resolution (320x240)
const int targetWidth = 320;
const int targetHeight = 240;

// Folder names on SD card
const char* baseFolder = "/DataTraining";
const char* safeFolder = "/DataTraining/safe";
const char* closeFolder = "/DataTraining/close";

// Flash control
const int flashPin = 4;
bool flashEnabled = false;

// forward declarations
void initSD();
void createFolderStructure();
void captureAndSaveImage(String label);
String buildMainPage();
void streamMJPEG(WiFiClient &client);
void sendResponse(WiFiClient &client, String content, String contentType);
void toggleFlash();

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);

  // Initialise flash pin and force flash off
  pinMode(flashPin, OUTPUT);
  digitalWrite(flashPin, LOW);

  // initialise the camera & pins for it
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // set resolution to QVGA (320x240)
  config.frame_size   = FRAMESIZE_QVGA;
  config.jpeg_quality = 10;  
  config.fb_count     = 2;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init failed");
    return;
  }
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi connected. IP: ");
  Serial.println(WiFi.localIP());
  
  // Initialise SD card and create folder structure
  initSD();
  createFolderStructure();

  // Start the web server
  server.begin();
  Serial.println("Server started.");
}

void loop() {
  WiFiClient client = server.available();
  if (!client) {
    delay(1);
    return;
  }
  
  // read HTTP request
  String req = client.readStringUntil('\r');
  req.trim();
  Serial.println("Request: [" + req + "]");
  client.flush();

  if (req.startsWith("GET /stream")) {
    streamMJPEG(client);
    return;
  }
  else if (req.startsWith("GET /capture?label=")) {
    int labelIndex = req.indexOf("label=") + 6;
    int endIndex = req.indexOf(" ", labelIndex);
    String label = req.substring(labelIndex, endIndex);
    label.toLowerCase();
    Serial.println("Capture request with label: " + label);
    
    // ENSURE flash remains off if disabled... hopefully
    if (!flashEnabled) {
      digitalWrite(flashPin, LOW);
      Serial.println("Flash is disabled; proceeding without flash.");
    } else {
      Serial.println("Flash is enabled; turning flash ON for capture.");
      digitalWrite(flashPin, HIGH);
      delay(50);  // short delay for flash to prepare
    }
    
    captureAndSaveImage(label);
    
    // turn flash off if it was enabled 
    if (flashEnabled) {
      digitalWrite(flashPin, LOW);
      Serial.println("Turning flash OFF after capture.");
    }
    
    // send a response with meta-refresh to redirect back to main page after 1 second
    String response = "<html><head><meta http-equiv='refresh' content='1; url=/'></head><body><h3>Image captured for label: " + label + "</h3></body></html>";
    sendResponse(client, response, "text/html");
  }
  else if (req.startsWith("GET /toggleflash")) {
    toggleFlash();
    // Respond with new flash state and auto-redirect after 1 second (issue occured with flash toggle)
    String response = "<html><head><meta http-equiv='refresh' content='1; url=/'></head><body><h3>Flash toggled. Now: ";
    response += flashEnabled ? "ON" : "OFF";
    response += "</h3></body></html>";
    sendResponse(client, response, "text/html");
  }
  else {
    // serves the main training homepage
    String html = buildMainPage();
    sendResponse(client, html, "text/html");
  }
  
  delay(1);
  client.stop();
  Serial.println("Client disconnected");
}

//
// --- directory handling ---
//

void initSD() {
  if (!SD_MMC.begin()) {
    Serial.println("SD Card Mount Failed");
    return;
  }
  uint8_t cardType = SD_MMC.cardType();
  if(cardType == CARD_NONE){
    Serial.println("No SD card attached");
    return;
  }
  Serial.println("SD card initialised.");
}

void createFolderStructure() {
  if (!SD_MMC.exists(baseFolder)) {
    SD_MMC.mkdir(baseFolder);
    Serial.println("Created folder: " + String(baseFolder));
  }
  if (!SD_MMC.exists(safeFolder)) {
    SD_MMC.mkdir(safeFolder);
    Serial.println("Created folder: " + String(safeFolder));
  }
  if (!SD_MMC.exists(closeFolder)) {
    SD_MMC.mkdir(closeFolder);
    Serial.println("Created folder: " + String(closeFolder));
  }
}

//
// --- image save & capture ---
//

void captureAndSaveImage(String label) {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }
  
  String path = baseFolder;
  if (label == "safe") {
    path += "/safe/";
  } else if (label == "close") {
    path += "/close/";
  } else {
    path += "/safe/"; // default to safe if unknown
  }
  
  String filename = path + "IMG_" + String(millis()) + ".jpg";
  Serial.println("Saving image to: " + filename);
  
  File file = SD_MMC.open(filename.c_str(), FILE_WRITE);
  if (!file) {
    Serial.println("Failed to open file for writing");
  } else {
    file.write(fb->buf, fb->len);
    Serial.println("File saved successfully");
  }
  file.close();
  esp_camera_fb_return(fb);
}

//
// --- MJPEG streaming ---
//

void streamMJPEG(WiFiClient &client) {
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
  client.println("Cache-Control: no-cache");
  client.println();
  
  while (client.connected()) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      break;
    }
    client.println("--frame");
    client.println("Content-Type: image/jpeg");
    client.print("Content-Length: ");
    client.println(fb->len);
    client.println();
    client.write(fb->buf, fb->len);
    client.println();
    esp_camera_fb_return(fb);
    delay(30);
  }
}

//
// --- flash on ESP32-CAM ---
//

void toggleFlash() {
  flashEnabled = !flashEnabled;
  Serial.println("Flash toggled. New state: " + String(flashEnabled ? "ON" : "OFF"));
}

//
// --- webserver build ---
//

String buildMainPage() {
  String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<title>EasyTrain Program</title>";
  html += "<style>body{font-family:Arial; text-align:center; padding:20px;}"
          "button{font-size:20px; padding:15px 30px; margin:20px;}"
          "img{max-width:100%; height:auto; border:1px solid #ccc; margin-top:20px;}"
          "</style></head><body>";
  html += "<h2>Data Training Capture</h2>";
  html += "<p>Press a button to capture an image with the corresponding label.</p>";
  html += "<button onclick=\"location.href='/capture?label=safe'\">Safe</button>";
  html += "<button onclick=\"location.href='/capture?label=close'\">Close</button>";
  html += "<p>Flash is currently: <strong>" + String(flashEnabled ? "ON" : "OFF") + "</strong></p>";
  html += "<button onclick=\"location.href='/toggleflash'\">Toggle Flash</button>";
  html += "<h3>Live Preview</h3>";
  // force fresh reload of the MJPEG stream with parameter
  html += "<img src='/stream?rand=" + String(millis()) + "' alt='Live Camera Feed'>";
  html += "</body></html>";
  return html;
}

//
// --- send HTTP response ---
//

void sendResponse(WiFiClient &client, String content, String contentType) {
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: " + contentType);
  client.println("Connection: close");
  client.println();
  client.println(content);
}
