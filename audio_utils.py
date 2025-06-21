import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import os

class AudioRecorder:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.recordings_dir = "recordings"
        
        # Create recordings directory if it doesn't exist
        if not os.path.exists(self.recordings_dir):
            os.makedirs(self.recordings_dir)
    
    def record(self, duration=5):
        """Record audio for the specified duration"""
        print(f"Recording for {duration} seconds...")
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1
        )
        sd.wait()
        print("Recording finished!")
        return recording
    
    def save_recording(self, recording, filename=None):
        """Save the recording to a WAV file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
        
        filepath = os.path.join(self.recordings_dir, filename)
        sf.write(filepath, recording, self.sample_rate)
        return filepath
    
    def record_and_save(self, duration=5):
        """Record audio and save it to a file"""
        recording = self.record(duration)
        return self.save_recording(recording) 