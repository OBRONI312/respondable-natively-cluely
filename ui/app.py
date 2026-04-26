import customtkinter as ctk
import json
import threading
import time
from core.audio_capture import AudioCapture
from core.screen_capture import ScreenCapture
from core.ai_pipeline import AIPipeline
from core.video_replication import VideoReplicator

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LectureAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cluely - AI Lecture Assistant")
        self.geometry("800x600")

        self.audio_capture = AudioCapture()
        self.screen_capture = ScreenCapture()
        self.ai_pipeline = AIPipeline(log_callback=self.log_message)
        self.video_replicator = VideoReplicator(log_callback=self.log_message)
        
        self.is_running_pipeline = False
        self.pipeline_thread = None

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        # Create Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_settings = self.tabview.add("Settings")

        # --- Dashboard ---
        self.tab_dashboard.grid_columnconfigure(0, weight=1)
        self.tab_dashboard.grid_columnconfigure(1, weight=1)
        self.tab_dashboard.grid_rowconfigure(2, weight=1)

        self.lbl_status = ctk.CTkLabel(self.tab_dashboard, text="Status: Idle", font=("Arial", 18, "bold"))
        self.lbl_status.grid(row=0, column=0, columnspan=2, pady=10)

        self.switch_listen = ctk.CTkSwitch(self.tab_dashboard, text="Enable Listening (Mic/System)", command=self.toggle_listening)
        self.switch_listen.grid(row=1, column=0, pady=10, padx=20, sticky="w")

        self.switch_screen = ctk.CTkSwitch(self.tab_dashboard, text="Enable Screen Recording", command=self.toggle_screen)
        self.switch_screen.grid(row=1, column=1, pady=10, padx=20, sticky="e")
        
        self.switch_video = ctk.CTkSwitch(self.tab_dashboard, text="Enable Video Replication", command=self.toggle_video)
        self.switch_video.grid(row=2, column=0, columnspan=2, pady=10, padx=20)

        self.log_box = ctk.CTkTextbox(self.tab_dashboard, width=700, height=250)
        self.log_box.grid(row=3, column=0, columnspan=2, pady=20, padx=20, sticky="nsew")
        self.log_box.configure(state="disabled")

        # --- Settings ---
        self.tab_settings.grid_columnconfigure(1, weight=1)

        # API Keys
        ctk.CTkLabel(self.tab_settings, text="API Keys", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10, sticky="w")
        
        ctk.CTkLabel(self.tab_settings, text="OpenAI Key:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_openai = ctk.CTkEntry(self.tab_settings, width=400, show="*")
        self.entry_openai.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.tab_settings, text="ElevenLabs Key:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.entry_elevenlabs = ctk.CTkEntry(self.tab_settings, width=400, show="*")
        self.entry_elevenlabs.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(self.tab_settings, text="Video Loop Path:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.entry_video_path = ctk.CTkEntry(self.tab_settings, width=400)
        self.entry_video_path.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # Toggles for Local vs API
        ctk.CTkLabel(self.tab_settings, text="Preferences", font=("Arial", 16, "bold")).grid(row=4, column=0, columnspan=2, pady=(20,10), sticky="w")
        
        self.var_local_llm = ctk.BooleanVar()
        self.chk_local_llm = ctk.CTkCheckBox(self.tab_settings, text="Use Local LLM (Ollama)", variable=self.var_local_llm)
        self.chk_local_llm.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.var_local_stt = ctk.BooleanVar()
        self.chk_local_stt = ctk.CTkCheckBox(self.tab_settings, text="Use Local STT (Whisper)", variable=self.var_local_stt)
        self.chk_local_stt.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.var_local_tts = ctk.BooleanVar()
        self.chk_local_tts = ctk.CTkCheckBox(self.tab_settings, text="Use Local TTS (Coqui)", variable=self.var_local_tts)
        self.chk_local_tts.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.btn_save = ctk.CTkButton(self.tab_settings, text="Save Settings", command=self.save_settings)
        self.btn_save.grid(row=8, column=0, columnspan=2, pady=20)

    def log_message(self, message):
        self.log_box.configure(state="normal")
        time_str = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{time_str}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def toggle_listening(self):
        if self.switch_listen.get() == 1:
            self.log_message("Audio listening enabled.")
            self.audio_capture.start_recording()
            self._check_start_pipeline()
        else:
            self.log_message("Audio listening disabled.")
            self.audio_capture.stop_recording()
            self._check_stop_pipeline()

    def toggle_screen(self):
        if self.switch_screen.get() == 1:
            self.log_message("Screen recording enabled.")
            self._check_start_pipeline()
        else:
            self.log_message("Screen recording disabled.")
            self._check_stop_pipeline()

    def toggle_video(self):
        if self.switch_video.get() == 1:
            self.log_message("Video replication requested.")
            self.video_replicator.start()
        else:
            self.log_message("Video replication disabled.")
            self.video_replicator.stop()

    def _check_start_pipeline(self):
        if not self.is_running_pipeline and (self.switch_listen.get() == 1 or self.switch_screen.get() == 1):
            self.is_running_pipeline = True
            self.lbl_status.configure(text="Status: Active", text_color="green")
            self.pipeline_thread = threading.Thread(target=self.run_pipeline_loop, daemon=True)
            self.pipeline_thread.start()

    def _check_stop_pipeline(self):
        if self.is_running_pipeline and self.switch_listen.get() == 0 and self.switch_screen.get() == 0:
            self.is_running_pipeline = False
            self.lbl_status.configure(text="Status: Idle", text_color="white")

    def run_pipeline_loop(self):
        interval = self.ai_pipeline.config.get("settings", {}).get("capture_interval_sec", 5)
        while self.is_running_pipeline:
            # Sleep in small chunks so we can exit quickly
            for _ in range(interval * 10):
                if not self.is_running_pipeline:
                    return
                time.sleep(0.1)
                
            audio_bytes = None
            if self.switch_listen.get() == 1:
                audio_bytes = self.audio_capture.get_audio_wav_bytes()
                
            base64_image = None
            if self.switch_screen.get() == 1:
                base64_image = self.screen_capture.capture_base64()
                
            if audio_bytes or base64_image:
                # Process in another thread to not block the capture loop
                threading.Thread(target=self.ai_pipeline.process_tick, args=(audio_bytes, base64_image), daemon=True).start()

    def load_settings(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                
            api_keys = config.get("api_keys", {})
            self.entry_openai.insert(0, api_keys.get("openai", ""))
            self.entry_elevenlabs.insert(0, api_keys.get("elevenlabs", ""))
            
            settings = config.get("settings", {})
            self.var_local_llm.set(settings.get("use_local_llm", False))
            self.var_local_stt.set(settings.get("use_local_stt", False))
            self.var_local_tts.set(settings.get("use_local_tts", False))
            self.entry_video_path.insert(0, settings.get("video_path", ""))
            self.video_replicator.set_video_path(settings.get("video_path", ""))
        except FileNotFoundError:
            pass

    def save_settings(self):
        config = {
            "api_keys": {
                "openai": self.entry_openai.get(),
                "elevenlabs": self.entry_elevenlabs.get()
            },
            "local_models": {
                "ollama_url": "http://localhost:11434/api/generate",
                "whisper_path": "base",
                "tts_api_url": "http://localhost:5002/api/tts"
            },
            "settings": {
                "use_local_llm": self.var_local_llm.get(),
                "use_local_stt": self.var_local_stt.get(),
                "use_local_tts": self.var_local_tts.get(),
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "capture_interval_sec": 5,
                "video_path": self.entry_video_path.get()
            }
        }
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
            
        self.ai_pipeline.load_config()
        self.video_replicator.set_video_path(self.entry_video_path.get())
        self.log_message("Settings saved and reloaded.")
        
    def on_closing(self):
        self.is_running_pipeline = False
        self.audio_capture.stop_recording()
        self.video_replicator.stop()
        self.destroy()
