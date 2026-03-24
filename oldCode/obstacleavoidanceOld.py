# ORIGINAL OBSTACLE AVOIDANCE CODE --- OLD!!!! (BD STEM STARS)
# This was one of my earliest approaches. I tried to detect nearby obstacles using edge density and line detection in the lower centre of the camera frame, but it was too unreliable in real environments.

import cv2
import numpy as np

STREAM_URL = "http://192.168.1.55/stream"
EDGE_THRESHOLD = 0.0035
LINE_THRESHOLD = 20

def detect_obstacle(frame):
    height, width = frame.shape[:2]

    # Focus on the lower middle part of the image
    roi = np.array([[
        (int(width * 0.3), int(height * 0.8)),
        (int(width * 0.7), int(height * 0.8)),
        (int(width * 0.7), int(height * 0.5)),
        (int(width * 0.3), int(height * 0.5))
    ]], dtype=np.int32)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    mask = np.zeros_like(edges)
    cv2.fillPoly(mask, roi, 255)
    roi_edges = cv2.bitwise_and(edges, mask)

    edge_density = cv2.countNonZero(roi_edges) / roi_edges.size
    lines = cv2.HoughLinesP(roi_edges, 1, np.pi / 180, 20, minLineLength=20, maxLineGap=5)
    line_count = 0 if lines is None else len(lines)

    obstacle = edge_density > EDGE_THRESHOLD or line_count > LINE_THRESHOLD
#Determine if obstacle is detected
    cv2.polylines(frame, roi, True, (0, 255, 0), 2)
    cv2.putText(frame, f"Edge Density: {edge_density:.4f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    cv2.putText(frame, f"Line Count: {line_count}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    if obstacle:
        cv2.putText(frame, "Obstacle Detected!", (40, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    return obstacle, frame, edges

cap = cv2.VideoCapture(STREAM_URL)

while True:
    ok, frame = cap.read()
    if not ok:
        print("Could not read frame")
        break

    obstacle, output_frame, edges = detect_obstacle(frame)

    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    preview = cv2.addWeighted(output_frame, 0.8, edges_bgr, 0.2, 0)

    cv2.imshow("Obstacle Detection", preview)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()