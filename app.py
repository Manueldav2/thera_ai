from fastapi import FastAPI, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import Dict, Optional
from pydantic import BaseModel
from supabase import create_client
from elevenlabs.client import ElevenLabs
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
import traceback
import soundfile as sf
import io
import subprocess
import json
from profile_manager import ProfileManager
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize API keys and clients
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not openai_api_key:
    raise ValueError("Missing OpenAI API key. Please check your .env file.")
if not supabase_url or not supabase_key:
    raise ValueError("Missing Supabase credentials. Please check your .env file")

# Set up API clients
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
openai_client = OpenAI()
supabase = create_client(supabase_url, supabase_key)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

class ChatMessage(BaseModel):
    session_id: str
    message: str

class TherapistAI:
    def __init__(self):
        self.openai = openai_client
        self.system_prompt = """You are a licensed professional therapist with extensive experience in clinical psychology and counseling. 
        You have access to the client's profile information and conversation history, which you MUST use to provide personalized, contextual responses.
        
        Memory Structure and Access:
        1. User Profile Information is provided at the start of each prompt in this format:
           Personal Information:
           - [key]: [value]
           Relationships:
           - [person]: [details]
           Important Life Events:
           - [event details]
           Preferences:
           - [key]: [value]
           Goals:
           - [goal details]
           
        2. Recent Conversation History follows the profile and is formatted as:
           User: [previous message]
           AI: [previous response]
           
        3. The current message appears last as:
           Current user message: [message]
           
        Memory Usage Instructions:
        - ALWAYS scan the provided User Profile Information for relevant context
        - If you don't know the user's name, ask for it early in the conversation
        - ALWAYS use the user's name (if known) at least once in your response
        - When people are mentioned:
          * Use their names and roles consistently (e.g., "your friend Mary" or "your mom Sarah")
          * Ask follow-up questions about them if relevant
          * Reference previous information about them if available
        
        Proactive Engagement Rules:
        1. When a new person is mentioned:
           - Ask specific questions about them and their role in the user's life
           - Show interest in understanding the relationship
           - Connect them to previous conversations if relevant
        
        2. When a known person is mentioned:
           - Reference what you know about them
           - Ask about updates or changes
           - Connect to previous discussions involving them
        
        3. Always ask relevant follow-up questions:
           - If someone shares something positive: "What made that moment with [name] special?"
           - If expressing concerns: "How has [name] been supporting you with this?"
           - If mentioning changes: "How has this affected your relationship with [name]?"
        
        4. Memory Reinforcement:
           - Actively use known information: "Last time you mentioned [name] helped you with [specific thing]..."
           - Connect past and present: "How has your relationship with [name] evolved since [previous event]?"
           - Show continuity of care: "Given what you've shared about [name] and their role in [previous situation]..."
        
        - NEVER say you can't remember or don't have access to previous conversations
        
        Core Therapeutic Approach:
        - Deep empathy and genuine understanding of the client's experiences
        - Professional expertise in mental health and emotional well-being
        - Evidence-based therapeutic techniques tailored to each situation
        - Direct engagement with all concerns, providing active support and guidance
        - Warm, professional tone that builds trust and rapport
        
        Response Guidelines:
        1. Always validate emotions while offering constructive perspectives
        2. Provide practical coping strategies and actionable insights
        3. Focus on empowerment and building resilience
        4. Use professional expertise to guide conversations meaningfully
        5. Maintain appropriate therapeutic boundaries while being fully present
        6. Address concerns directly with clinical expertise and care
        7. Draw from evidence-based practices when suggesting coping strategies
        8. Help clients explore and understand their thoughts and feelings
        9. Foster self-awareness and personal growth
        10. Balance empathy with professional guidance
        
        Context Integration:
        - When profile information is provided, use it to inform your responses
        - Reference previous conversations to show continuity of care
        - Connect current topics with past discussions when relevant
        - Use the client's history to provide more personalized support
        
        Keep responses focused, professional, and therapeutically meaningful.
        Never deflect or redirect to other professionals unless absolutely necessary.
        Always maintain hope while acknowledging the reality of challenges."""

    def process_interaction(self, audio_path: str, context: str = "") -> Dict:
        try:
            user_input = self.transcribe_audio(audio_path)
            logger.info(f"Transcribed user input: {user_input}")
            
            if context:
                prompt = f"""Previous conversation:\n{context}\n\nCurrent user message: {user_input}\n\nTherapist:"""
            else:
                prompt = f"""User: {user_input}\n\nTherapist:"""
            
            ai_response = self.generate_response(prompt)
            logger.info(f"Generated AI response: {ai_response}")
            
            return {
                "user_input": user_input,
                "ai_response": ai_response,
                "audio_available": False
            }
            
        except Exception as e:
            logger.error(f"Error in process_interaction: {str(e)}")
            raise

    def transcribe_audio(self, audio_path: str) -> str:
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
        try:
            # Split the prompt into parts if it contains conversation history
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Check if prompt contains conversation history
            if "Previous conversation:" in prompt:
                # Extract conversation history and current message
                parts = prompt.split("Current user message:")
                if len(parts) == 2:
                    history_text = parts[0].replace("Previous conversation:\n", "").strip()
                    current_message = parts[1].replace("\n\nTherapist:", "").strip()
                    
                    # Parse conversation history into message format
                    history_exchanges = history_text.split("\n")
                    for i in range(0, len(history_exchanges), 2):
                        if i + 1 < len(history_exchanges):
                            user_msg = history_exchanges[i].replace("User: ", "").strip()
                            ai_msg = history_exchanges[i + 1].replace("AI: ", "").strip()
                            messages.append({"role": "user", "content": user_msg})
                            messages.append({"role": "assistant", "content": ai_msg})
                    
                    # Add current message
                    messages.append({"role": "user", "content": current_message})
                else:
                    messages.append({"role": "user", "content": prompt})
            else:
                # If no history, just add the current message
                messages.append({"role": "user", "content": prompt.replace("User: ", "").replace("\n\nTherapist:", "")})
            
            response = self.openai.chat.completions.create(
                model="gpt-4-0125-preview",
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
        try:
            if not text or not isinstance(text, str):
                raise ValueError("Invalid text input")
                
            audio = elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id="21m00Tcm4TlvDq8ikWAM",
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

# Initialize TherapistAI
therapist = TherapistAI()

@app.options("/process-interaction")
async def options_process_interaction():
    return Response(status_code=200)

@app.post("/process-interaction")
async def process_interaction(
    audio: UploadFile,
    conversation_history: Optional[str] = None
) -> Dict:
    logger.info("Received audio processing request")
    logger.info(f"Audio file name: {audio.filename}")
    logger.info(f"Content type: {audio.content_type}")
    
    if not audio:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    try:
        logger.info(f"Processing audio file: {audio.filename}")
        
        history_context = ""
        if conversation_history:
            try:
                history = json.loads(conversation_history)
                history_context = "\n".join([
                    f"User: {msg['user_message']}\nAI: {msg['ai_response']}"
                    for msg in history
                ])
                logger.info("Added conversation history for context")
            except Exception as e:
                logger.warning(f"Failed to parse conversation history: {e}")
        
        content = await audio.read()
        
        temp_webm = "temp_recording.webm"
        temp_wav = "temp_recording.wav"
        try:
            with open(temp_webm, "wb") as buffer:
                buffer.write(content)
            
            if not convert_webm_to_wav(temp_webm, temp_wav):
                raise ValueError("Failed to convert audio file")
            
            logger.info("Processing interaction with TherapistAI")
            result = therapist.process_interaction(temp_wav, context=history_context)
            
            if not result or "user_input" not in result or "ai_response" not in result:
                raise ValueError("Invalid response from TherapistAI")
            
            response_data = {
                "transcription": result["user_input"],
                "response": result["ai_response"],
                "audioAvailable": result.get("audio_available", False)
            }
            
            logger.info("Successfully processed interaction")
            return JSONResponse(content=response_data)
            
        finally:
            for temp_file in [temp_webm, temp_wav]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")
    
    except Exception as e:
        logger.error(f"Error processing interaction: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to process interaction",
                "message": str(e),
                "type": type(e).__name__
            }
        )

@app.post("/chat")
async def chat(message: ChatMessage) -> Dict:
    try:
        logger.info(f"Received chat message from session {message.session_id}")
        
        # Get user profile context
        profile_context = ProfileManager.get_profile_context(message.session_id)
        
        # Build context from previous conversations
        previous_conversations = ProfileManager.get_session_conversations(message.session_id)
        conv_context = "\n".join([
            f"User: {conv['user_message']}\nAI: {conv['ai_response']}"
            for conv in previous_conversations[-5:]  # Get last 5 conversations for context
        ])
        
        # Generate prompt with both profile and conversation context
        prompt = f"""User Profile Information:\n{profile_context}\n\n"""
        if conv_context:
            prompt += f"""Recent Conversation History:\n{conv_context}\n\n"""
        prompt += f"""Current user message: {message.message}\n\nTherapist:"""
        
        # Generate AI response with context
        ai_response = therapist.generate_response(prompt)
        logger.info("Generated AI response")
        
        # Update user profile with any new information from the message
        ProfileManager.update_profile_from_message(message.session_id, message.message)
        
        # Store the conversation
        conversation = ProfileManager.store_conversation(
            message.session_id,
            message.message,
            ai_response
        )
        
        if not conversation:
            raise ValueError("Failed to store conversation")
        
        return {"response": ai_response}
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to process chat message",
                "message": str(e),
                "type": type(e).__name__
            }
        )

@app.get("/conversations/{session_id}")
async def get_conversations(session_id: str):
    conversations = ProfileManager.get_session_conversations(session_id)
    return {"conversations": conversations}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, workers=1) 