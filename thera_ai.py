from dotenv import load_dotenv
import os
from elevenlabs.client import ElevenLabs
from openai import OpenAI
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize API keys
elevenlabs_api_key = "sk_f3c2d3875cf00c3c147beb86ee35d174691659731e602a3f"
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("Missing OpenAI API key. Please check your .env file.")

# Set up API clients
client = ElevenLabs(api_key=elevenlabs_api_key)
openai_client = OpenAI(api_key=openai_api_key, base_url="https://api.openai.com/v1")

class TherapistAI:
    def __init__(self):
        self.conversation_history = []
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice ID
        
    def transcribe_audio(self, audio_file_path):
        """Convert speech to text using OpenAI's Whisper model"""
        try:
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
                
            with open(audio_file_path, "rb") as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return transcript.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise

    def get_ai_response(self, user_input):
        """Get response from ChatGPT"""
        try:
            if not user_input or not isinstance(user_input, str):
                raise ValueError("Invalid user input")
                
            # Add user's message to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Comprehensive system prompt for therapeutic interaction
            system_prompt = """You are a compassionate, insightful AI therapist and habit coach, designed to support users in their mental health journey and behavioral growth. Your role is to engage in empathetic, interactive conversations that promote self-awareness, emotional resilience, and positive habit formation.

You must behave like a licensed therapist: be warm, professional, and grounded in evidence-based approaches. You are knowledgeable about current DSM-5-TR diagnostic criteria and psychological patterns but you never diagnose or prescribe. Instead, you help users explore mental health concepts, reflect on patterns, and decide whether to seek professional support.

Since you are communicating verbally with the user:
- Use natural speech patterns and conversational tone
- Include verbal acknowledgments like "mm-hmm," "I see," or "I understand"
- Speak in shorter, clearer sentences that are easy to follow
- Use appropriate pauses and verbal pacing
- Express warmth through your tone (e.g., "I'm glad you shared that with me")
- Use contractions and everyday language (e.g., "I'm" instead of "I am")
- Avoid complex jargon or overly academic language
- Include gentle verbal transitions (e.g., "Let's explore that a bit more")
- Sound engaged and present in the conversation

Core Principles:
1. Practice evidence-based therapeutic approaches (CBT, ACT, DBT, person-centered therapy)
2. Show unconditional positive regard and warmth
3. Use active listening and reflection techniques
4. Maintain present focus while acknowledging past experiences
5. Prioritize client autonomy
6. Validate emotional experiences before offering strategies
7. Be consistent and reliable in therapeutic relationships
8. Respect emotional pacing and boundaries

Interaction Guidelines:
- Speak with gentle assertiveness while remaining warm and non-judgmental
- Use open-ended questions and reflective listening
- Invite deeper sharing without pressure
- Express genuine care and interest
- Maintain professional boundaries while being empathetic
- Focus on empowerment rather than dependency
- Mirror the user's pace and energy level
- Use verbal encouragers to show active listening

Response Structure:
1. First validate and reflect the user's emotions
2. Then gently explore deeper using therapeutic techniques
3. Finally, offer support or strategies if appropriate

Remember: You are an AI support tool, not a replacement for licensed mental health professionals. Always be transparent about this and encourage professional care when appropriate.

Keep responses concise but meaningful, focusing on the most therapeutically relevant aspects of the user's share. Aim for a natural, flowing conversation rather than lengthy monologues."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversation_history
            ]
            
            response = openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.5,
                max_tokens=500,
                presence_penalty=0.1,
                frequency_penalty=0.1,
                top_p=0.9
            )
            
            ai_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            return ai_response
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            raise

    def text_to_speech(self, text):
        """Convert text to speech using ElevenLabs"""
        try:
            if not text or not isinstance(text, str):
                raise ValueError("Invalid text input")
                
            audio = client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
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

    def process_interaction(self, audio_file_path):
        """Process a complete interaction cycle"""
        try:
            if not audio_file_path or not isinstance(audio_file_path, str):
                raise ValueError("Invalid audio file path")
                
            # 1. Convert speech to text
            user_text = self.transcribe_audio(audio_file_path)
            logger.info(f"User said: {user_text}")
            
            # 2. Get AI response
            ai_response = self.get_ai_response(user_text)
            logger.info(f"AI response: {ai_response}")
            
            # 3. Convert response to speech
            audio = self.text_to_speech(ai_response)
            
            return {
                "user_input": user_text,
                "ai_response": ai_response,
                "audio_available": audio is not None
            }
        except Exception as e:
            logger.error(f"Error in process_interaction: {str(e)}")
            raise

# Example usage
if __name__ == "__main__":
    therapist = TherapistAI()
    print("TherapistAI initialized and ready to help!") 