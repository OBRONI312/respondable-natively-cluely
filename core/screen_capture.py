import mss
import mss.tools
import base64
import os
import time
from PIL import Image

class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()

    def capture_base64(self) -> str:
        """Captures the primary monitor and returns it as a base64 encoded JPEG string."""
        monitor = self.sct.monitors[1]  # primary monitor
        sct_img = self.sct.grab(monitor)
        
        # Save temporarily
        temp_filename = "temp_capture.jpg"
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        # Resize to save bandwidth / token costs for Vision models
        img.thumbnail((1280, 720))
        img.save(temp_filename, format="JPEG", quality=75)

        with open(temp_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        # Clean up
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return encoded_string
        
    def capture_image(self) -> Image.Image:
        """Captures the primary monitor and returns a PIL Image."""
        monitor = self.sct.monitors[1]
        sct_img = self.sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img
