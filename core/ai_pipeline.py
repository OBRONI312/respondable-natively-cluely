import os
import json
import requests
from openai import OpenAI
import threading
import time

class AIPipeline:
    def __init__(self, config_path="config.json", log_callback=None):
        self.config_path = config_path
        self.log_callback = log_callback
        self.load_config()
        self.is_running = False
        
        # Audio routing helper (this will need external VB-Cable setup by user)
        # We can play the generated audio using sounddevice to a specific output device
        # This will be configured later or use default device for testing.
        import sounddevice as sd
        self.sd = sd

    def load_config(self):
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        api_keys = self.config.get("api_keys", {})
        self.openai_client = OpenAI(api_key=api_keys.get("openai", "")) if api_keys.get("openai") else None

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[AI] {message}")

    def process_tick(self, audio_bytes, base64_image):
        """Processes a single tick of recorded audio and the latest screen capture."""
        if not audio_bytes:
            return

        self.log("Transcribing audio...")
        transcription = self._transcribe(audio_bytes)
        
        if not transcription or len(transcription.strip()) < 5:
            # Skip very short or empty transcriptions
            return

        self.log(f"Heard: {transcription}")
        
        # Determine if a question was asked or context warrants a response
        # We will use the LLM to decide AND respond
        self.log("Analyzing transcription and screen...")
        response_text = self._generate_response(transcription, base64_image)
        
        if response_text and "IGNORE" not in response_text:
            self.log(f"AI Response: {response_text}")
            self.log("Generating Voice...")
            audio_data = self._text_to_speech(response_text)
            if audio_data:
                self.log("Playing output voice...")
                self._play_audio(audio_data)

    def _transcribe(self, audio_bytes) -> str:
        settings = self.config.get("settings", {})
        if settings.get("use_local_stt"):
            # Mock local STT for now
            return "Local STT not yet implemented."
        else:
            if not self.openai_client:
                return "Error: OpenAI API key not set."
            
            # Save bytes to temp file because OpenAI needs a file object with a name
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_filename = temp_audio.name
                
            try:
                with open(temp_filename, "rb") as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                return transcript.text
            except Exception as e:
                return f"STT Error: {e}"
            finally:
                os.remove(temp_filename)

    def _generate_response(self, text, base64_image) -> str:
        settings = self.config.get("settings", {})
        if settings.get("use_local_llm"):
            # Mock local LLM
            # Could send to self.config["local_models"]["ollama_url"]
            return "Local LLM response placeholder."
        else:
            if not self.openai_client:
                return "Error: OpenAI API key not set."
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI lecture assistant. The user is in an online class. You are listening to the lecture and seeing the user's screen. If the transcribed text asks a direct question to the user, provide a concise, natural, and accurate answer that the user can say out loud. If the transcription is just normal lecture content without a question directed at the user, respond with 'IGNORE'."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Lecture Transcription: {text}"}
                    ]
                }
            ]
            
            if base64_image:
                 messages[1]["content"].append({
                     "type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                 })

            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=150
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"LLM Error: {e}"

    def _text_to_speech(self, text) -> bytes:
        settings = self.config.get("settings", {})
        if settings.get("use_local_tts"):
            return b""
        else:
            elevenlabs_key = self.config.get("api_keys", {}).get("elevenlabs", "")
            if not elevenlabs_key:
                return b""
                
            voice_id = settings.get("voice_id", "EXAVITQu4vr4xnSDxMaL")
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": elevenlabs_key,
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            try:
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    return response.content
                else:
                    self.log(f"TTS Error: {response.status_code} {response.text}")
                    return b""
            except Exception as e:
                self.log(f"TTS Exception: {e}")
                return b""

    def _play_audio(self, audio_data: bytes):
        # Decode and play the MP3 data (ElevenLabs returns MP3 by default)
        # Using a simple temp file and pygame or pydub to play it
        import tempfile
        try:
            import pygame
            pygame.mixer.init()
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_filename = temp_audio.name
                
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            pygame.mixer.music.unload()
            os.remove(temp_filename)
            
        except ImportError:
            self.log("Please install pygame to play audio (`pip install pygame`)")
        except Exception as e:
            self.log(f"Playback error: {e}")
