**Why is there 2 versions, ContextVision and contextVisionImg?**

During production, my ESP32-CAM broke, and I needed a fallback to test the accuracy, and how this system worked. I made contextVisionImg for this purpose. Upload an image, link to its directory, and ensure to set your OpenAI API key in environment variables with this command: ($env:OPENAI_API_KEY="yourapikeyhere")
