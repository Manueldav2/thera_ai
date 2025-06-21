from dotenv import load_dotenv
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import play

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("ELEVENLABS_API_KEY")

# Print first and last 4 characters of API key for verification
if api_key:
    print(f"API Key loaded: {api_key[:4]}...{api_key[-4:]}")
else:
    print("No API key found in .env file!")

# Initialize the client with API key directly
client = ElevenLabs(
    api_key="sk_f3c2d3875cf00c3c147beb86ee35d174691659731e602a3f"
)

# Generate audio using the correct method
audio = client.text_to_speech.convert(
    text="Hello, how are you?",
    voice_id="JBFqnCBsd6RMkjVDRZzb",  # Rachel's voice ID
    model_id="eleven_multilingual_v2"
)

# Play the audio
play(audio)