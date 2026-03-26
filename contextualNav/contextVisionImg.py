import os
import base64
import cv2
from openai import OpenAI
import textwrap

image_file = "images/test.jpg"
model = "gpt-4o-mini"
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

def resize_for_display(frame, max_width=1000, max_height=700):
    h, w = frame.shape[:2]
    scale = min(max_width / w, max_height / h, 1.0)

    new_w = int(w * scale)
    new_h = int(h * scale)

    return cv2.resize(frame, (new_w, new_h))

def draw_text_lines(frame, text):
    lines = text.splitlines()
    y = 30
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2
    line_gap = 12
    max_chars_per_line = 38 # lower = more wrap

    wrapped_lines = []

    for line in lines[:4]:
        wrapped = textwrap.wrap(line, width=max_chars_per_line)
        if not wrapped:
            wrapped = [""]
        wrapped_lines.extend(wrapped)

    for line in wrapped_lines:
        (text_w, text_h), _ = cv2.getTextSize(line, font, font_scale, thickness)

        cv2.rectangle(
            frame,
            (8, y - text_h - 8),
            (12 + text_w, y + 6),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            frame,
            line,
            (10, y),
            font,
            font_scale,
            (0, 255, 0),
            thickness
        )

        y += text_h + line_gap

def save_result(text):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set in environment variable")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, image_file)
    output_path = os.path.join(script_dir, output_file)

    print("Script folder:", script_dir)
    print("Looking for image at:", image_path)
    
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Could not find image file: {image_path}")
    
    frame = cv2.imread(image_path)
    if frame is None:
        raise RuntimeError("Could not load image")
    
    
    print("Running. Press Q or ESC to quit. Press S to analyse immediately.")
    latest_result = "Scene: Starting...\nHazard: Waiting...\nAction: Waiting..."

    try:
        latest_result = analyse_frame(frame)
        save_result(latest_result)

        print("\n---Navigation Update---")
        print(latest_result)

        if "Alert: yes" in latest_result:
            print("Alert Triggered") #placeholder for buzzer activation

    except Exception as e:
        print("OpenAI request failed:", e)

    window_name = "ExGlass Image Analysis"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        display_frame = resize_for_display(frame.copy(), max_width=1000,max_height=700)
        draw_text_lines(display_frame, latest_result)
        cv2.imshow(window_name, display_frame)

        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

        key = cv2.waitKey(30) & 0xFF

        if key == ord("s"):
            try:
                latest_result = analyse_frame(frame)
                save_result(latest_result)

                print("\n---Navigation Update---")
                print(latest_result)

                if "Alert: yes" in latest_result:
                    print("Alert Triggered")  # placeholder for buzzer activation

            except Exception as e:
                print("OpenAI request failed:", e)

        if key == ord("q") or key == 27:
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()