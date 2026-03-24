# TENSORFLOW LITE MODEL INFERENCE PROGRAM - BD STEM STARS 2025

#For ISE:
#This code fetched the camera stream, ran the TensorFlow Lite model on each frame, and sent a request to the second ESP32 when the model thought the user was too close to an obstacle.


import cv2
import numpy as np
import tensorflow as tf
import os
import time
import threading
import queue
from collections import deque
import requests
from tensorflow.lite.python.interpreter import Interpreter

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
tflite_model_path = 'obstacle_detector_v4.tflite'
interpreter = Interpreter(model_path=tflite_model_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# image res = QVGA (320x240)
img_width, img_height = 320, 240

# cam stream URL
stream_url = "http://192.168.1.55/stream"
# --------- MAKE SURE TO CHECK FOR CHANGES AFTER EACH RESTART -----------
# ESP8266 buzzer alert endpoint
speaker_url = "http://172.20.10.4/alert" 

# alert cooldown (sec)
ALERT_COOLDOWN = 5  
last_alert_time = 0

# frame queue to manage overload
frame_queue = queue.Queue(maxsize=2)

def frame_capture_thread(cap, frame_queue):
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.release()
            time.sleep(1)
            cap = cv2.VideoCapture(stream_url)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, img_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, img_height)
            continue
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        frame_queue.put(frame)

# function that sends alert seperately
def send_alert():
    try:
        response = requests.get(speaker_url, timeout=0.5)
        print("Alert sent. Response code:", response.status_code)
    except Exception as e:
        print("Failed to send alert:", e)

# Initialise VideoCapture and set resolution
cap = cv2.VideoCapture(stream_url)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, img_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, img_height)
capture_thread = threading.Thread(target=frame_capture_thread, args=(cap, frame_queue))
capture_thread.daemon = True
capture_thread.start()

frame_count = 0
smoothing_window = deque(maxlen=5)
detection_threshold = 0.5  # THRESHOLD SUBJECT TO CHANGE

prev_time = time.time()
fps = 0

while True:
    try:
        frame = frame_queue.get(timeout=1)
    except queue.Empty:
        continue

    # Rotate the frame 90 degrees counterclockwise for orientation correction (COMMENTED OUT UNTIL GLASSES IN USE)
    #frame = cv2.rotate(frame, cv2.ROTATE_180)
    
    frame_count += 1
    if frame_count % 2 != 0:  # process every second frame, too much lag occuring bruh
        continue

    current_time = time.time()
    time_diff = current_time - prev_time
    prev_time = current_time
    if time_diff > 0:
        fps = 1.0 / time_diff

    # Preprocess the frame (resize and normalize)
    resized_frame = cv2.resize(frame, (img_width, img_height))
    normalized_frame = resized_frame.astype("float32") / 255.0
    input_data = np.expand_dims(normalized_frame, axis=0)

    # set TFlite tensor and invoke interpreter
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    current_prob = output_data[0][0]

    smoothing_window.append(current_prob)
    avg_prob = np.mean(smoothing_window)

    if avg_prob < detection_threshold:  #WEIRD?? ALWAYS INVERTING
        text = "Obstacle Detected!"
        color = (0, 0, 255)
        if (current_time - last_alert_time) > ALERT_COOLDOWN:
            threading.Thread(target=send_alert, daemon=True).start()
            last_alert_time = current_time
    else:
        text = "Safe"
        color = (0, 255, 0)

    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    cv2.putText(frame, f"Prob: {avg_prob:.2f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1]-150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    cv2.imshow("Obstacle Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
