import sounddevice as sd
import numpy as np
import threading
import queue
import wave
import io
import time

class AudioCapture:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.q = queue.Queue()
        self.is_recording = False
        self.stream = None
        self.thread = None
        self.audio_data = []

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, flush=True)
        self.q.put(indata.copy())

    def start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.audio_data = []
        
        def record_thread():
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, callback=self.callback):
                while self.is_recording:
                    sd.sleep(100)
                    while not self.q.empty():
                        self.audio_data.append(self.q.get())
        
        self.thread = threading.Thread(target=record_thread)
        self.thread.start()

    def stop_recording(self):
        self.is_recording = False
        if self.thread:
            self.thread.join()
            
    def get_audio_wav_bytes(self) -> bytes:
        """Returns the recorded audio as a WAV file in bytes, and clears the buffer."""
        if not self.audio_data:
            return b""
            
        data = np.concatenate(self.audio_data, axis=0)
        self.audio_data = [] # clear for next chunk
        
        # Convert to 16-bit PCM
        data_int16 = (data * np.iinfo(np.int16).max).astype(np.int16)
        
        byte_io = io.BytesIO()
        with wave.open(byte_io, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(data_int16.tobytes())
            
        return byte_io.getvalue()
