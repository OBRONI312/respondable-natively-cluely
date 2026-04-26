import cv2
import pyvirtualcam
import threading
import time
import os

class VideoReplicator:
    def __init__(self, log_callback=None):
        self.is_running = False
        self.thread = None
        self.log_callback = log_callback
        self.video_path = ""

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[Video] {message}")

    def set_video_path(self, path):
        self.video_path = path

    def start(self):
        if self.is_running:
            return
            
        if not self.video_path or not os.path.exists(self.video_path):
            self.log("Cannot start video replication: Video path is empty or invalid.")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.log("Video replication started.")

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self.thread:
            self.thread.join()
        self.log("Video replication stopped.")

    def _run_loop(self):
        try:
            # Open the video file to get dimensions and FPS
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.log(f"Failed to open video file: {self.video_path}")
                self.is_running = False
                return

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps == 0:
                fps = 30.0 # fallback

            # Create virtual camera
            with pyvirtualcam.Camera(width=width, height=height, fps=fps) as cam:
                self.log(f"Virtual camera started: {cam.device} ({width}x{height} @ {fps}fps)")
                
                while self.is_running:
                    ret, frame = cap.read()
                    
                    if not ret:
                        # Reached the end of the video, loop it
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                        
                    # OpenCV uses BGR, pyvirtualcam needs RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    cam.send(frame_rgb)
                    cam.sleep_until_next_frame()
                    
            cap.release()
            
        except Exception as e:
            self.log(f"Virtual camera error: {e}")
            self.log("Ensure OBS Virtual Camera (or similar) is installed.")
            self.is_running = False
