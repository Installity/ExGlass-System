import os
import time
import base64
import cv2
from openai import OpenAI

stream_url = "http://192.168.1.55/stream"
model = "gpt-4o-mini"
check_every_sec = 3

prompt = """You are an assistive navigation system for a visually impaired user.

Look at this image and give a very short, practical response.

Rules:
- Focus only on what matters immediately.
- Mention obstacles or hazards ahead.
- Give one clear action.
- Be brief.

Format exactly like this:

Scene: ...
Hazard: ...
Action: ...
Alert: yes/no
"""

client = OpenAI()

def frame_to_data_url(frame):
    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("Could not encode frame")
    
    image_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{image_b64}"

def analyse_frame(frame):
    image_data_url = frame_to_data_url(frame)

    response = client.response.create(
        model=MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {"type": "input_image", "image_url": image_data_url, "detail": "low"}
                ]
            }
        ]
    )

    return response.output_text.strip()

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set in environment variable")
    
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        raise RuntimeError("Could not open ESP32-CAM stream")
    
    print("Running. Press Q to quit.")
    last_check = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Could not read frame")
            time.sleep(1)
            continue

        now = time.time()

        if now - last_check >= check_every_sec:
            try:
                result = analyse_frame(frame)
                print("\n---Navigation Update---")
                print(result)

                if "Alert: yes" in result:
                    print("Alert Triggered") #placeholder for buzzer activation 

            except Exception as e:
                print("OpenAI request failed:", e)

            last_check = now

        cv2.imshow("ExGlass Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()