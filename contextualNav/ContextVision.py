import os
import time
import base64
import cv2
from openai import OpenAI

stream_url = ""
model = "gpt-4o-mini"
check_every_sec = 3
output_file = "latest_navigation.txt"

prompt = """You are an assistive navigation system for a visually impaired user.

Analyze this single image from a smart-glasses camera and give immediate, practical navigation information.

Priorities, in order:
1. Obstacles or hazards directly ahead
2. Changes in ground level or terrain
3. Doors, stairs, crossings, people, vehicles, poles, signs, or narrow passages
4. Useful orientation cues

Rules:
- Be brief, concrete, and safety-focused.
- Do not guess if the image is unclear.
- Do not describe unimportant background details.
- If nothing important is visible, say that clearly.
- Focus on what matters in the next few seconds of movement.
- Set Alert to yes only if there is an immediate hazard or obstacle that needs urgent warning.

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

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_data_url, "detail": "low"}
                ]
            }
        ]
    )

    return response.output_text.strip()

def draw_text_lines(frame, text):
    lines = text.splitlines()
    y = 30

    for line in lines[:4]:
        cv2.putText(
            frame,
            line[:80],
            (10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,255,0),
            2
        )
        y += 30

def save_result(text):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set in environment variable")
    
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        raise RuntimeError("Could not open ESP32-CAM stream")
    
    print("Running. Press Q to quit. Press S to analyse immediately.")
    last_check = 0
    latest_result = "Scene: Starting...\nHazard: Waiting...\nAction: Waiting..."

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Could not read frame")
            time.sleep(1)
            continue

        now = time.time()
        key = cv2.waitKey(1) & 0xFF

        should_analyse = False

        if now - last_check >= check_every_sec:
            should_analyse = True

        if key == ord("s"):
            should_analyse = True

        if should_analyse:
            try:
                latest_result = analyse_frame(frame)
                save_result(latest_result)

                print("\n---Navigation Update---")
                print(latest_result)

                if "Alert: yes" in latest_result:
                    print("Alert Triggered") # placeholder for buzzer activation
            except Exception as e:
                print("OpenAI request failed:", e)

            last_check = now


        display_frame = frame.copy()
        draw_text_lines(display_frame, latest_result)
        cv2.imshow("ExGlass Camera", display_frame)

        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()