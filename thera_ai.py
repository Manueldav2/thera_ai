from dotenv import load_dotenv
import os
from elevenlabs.client import ElevenLabs
from openai import OpenAI
import json
import logging
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize API keys
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("Missing OpenAI API key. Please check your .env file.")

# Set up API clients
client = ElevenLabs(api_key=elevenlabs_api_key)
openai_client = OpenAI()

class TherapistAI:
    def __init__(self):
        self.openai = openai_client
        self.system_prompt = """You are a highly qualified, licensed mental health professional with years of experience in therapy and counseling.
        Your approach combines empathy with clinical expertise. You should:
        
        1. Maintain a professional therapeutic relationship while showing genuine care
        2. Use evidence-based therapeutic techniques and professional insights
        3. Provide constructive coping strategies and practical guidance when appropriate
        4. Recognize and respect the complexity of mental health challenges
        5. Focus on empowering the client while maintaining appropriate professional boundaries
        6. Use a warm, professional tone that balances empathy with clinical expertise
        7. Never dismiss or minimize the client's feelings
        8. Avoid generic responses - draw from your clinical expertise to provide meaningful insights
        9. When appropriate, explore underlying thoughts and feelings to help the client gain deeper understanding
        10. Always maintain a hopeful but realistic perspective
        
        Keep responses concise but meaningful, and always maintain professional therapeutic standards."""

    def process_interaction(self, audio_path: str, context: str = "") -> Dict:
        """
        Process an audio interaction with context from previous conversations
        """
        try:
            # Transcribe audio to text
            user_input = self.transcribe_audio(audio_path)
            logger.info(f"Transcribed user input: {user_input}")
            
            # Generate response considering context
            if context:
                prompt = f"""Previous conversation:\n{context}\n\nCurrent user message: {user_input}\n\nTherapist:"""
            else:
                prompt = f"""User: {user_input}\n\nTherapist:"""
            
            # Get AI response
            ai_response = self.generate_response(prompt)
            logger.info(f"Generated AI response: {ai_response}")
            
            return {
                "user_input": user_input,
                "ai_response": ai_response,
                "audio_available": False  # Set to True if implementing speech synthesis
            }
            
        except Exception as e:
            logger.error(f"Error in process_interaction: {str(e)}")
            raise

    def transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe audio file to text using OpenAI's Whisper model
        """
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
                
            with open(audio_path, "rb") as audio_file:
                transcript = self.openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
                return transcript.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise

    def generate_response(self, prompt: str) -> str:
        """
        Generate AI response using GPT-4 with professional therapeutic approach
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            response = self.openai.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                max_tokens=500,
                temperature=0.5,  # Lower temperature for more consistent, professional responses
                presence_penalty=0.3,  # Moderate presence penalty to maintain focus
                frequency_penalty=0.3,  # Prevent repetition while maintaining consistency
                top_p=0.9  # Focus on more likely/professional responses
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    def text_to_speech(self, text):
        """Convert text to speech using ElevenLabs"""
        try:
            if not text or not isinstance(text, str):
                raise ValueError("Invalid text input")
                
            audio = client.text_to_speech.convert(
                text=text,
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Professional therapist voice
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
                voice_settings={
                    "stability": 0.71,
                    "similarity_boost": 0.75,
                    "style": 0.35,
                    "use_speaker_boost": True
                }
            )
            return audio
        except Exception as e:
            if "quota_exceeded" in str(e):
                logger.warning("ElevenLabs quota exceeded. Returning without audio.")
                return None
            logger.error(f"Error converting text to speech: {str(e)}")
            raise

# Example usage
if __name__ == "__main__":
    therapist = TherapistAI()
    print("TherapistAI initialized and ready to help!") 