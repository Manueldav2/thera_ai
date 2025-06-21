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

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Message(BaseModel):
    session_id: str
    message: str

class TherapistAI:
    def __init__(self):
        self.openai = openai_client
        self.system_prompt = """You are a compassionate and professional AI therapist. 
        Your responses should be empathetic, insightful, and focused on helping the user.
        Consider the conversation history provided and maintain continuity in your responses.
        Never disclose that you are an AI - maintain the therapeutic relationship.
        Keep responses concise but meaningful."""

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
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                presence_penalty=0.6,
                frequency_penalty=0.3
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

class SessionManager:
    @staticmethod
    def create_user(email: str, password: str):
        try:
            result = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            return result
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None

    @staticmethod
    def login_user(email: str, password: str):
        try:
            result = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {"session_id": result.session.access_token}
        except Exception as e:
            logger.error(f"Error logging in user: {str(e)}")
            return None

    @staticmethod
    def update_session_activity(session_id: str):
        try:
            supabase.table('sessions').update({
                'last_activity': 'now()'
            }).eq('session_id', session_id).execute()
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")

    @staticmethod
    def get_session_conversations(session_id: str):
        try:
            result = supabase.table('conversations').select('*').eq(
                'session_id', session_id
            ).order('created_at', desc=True).limit(5).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting conversations: {str(e)}")
            return []

    @staticmethod
    def store_conversation(session_id: str, user_message: str, ai_response: str):
        try:
            supabase.table('conversations').insert({
                'session_id': session_id,
                'user_message': user_message,
                'ai_response': ai_response
            }).execute()
        except Exception as e:
            logger.error(f"Error storing conversation: {str(e)}")

def convert_webm_to_wav(webm_path: str, wav_path: str) -> bool:
    try:
        subprocess.run([
            'ffmpeg',
            '-i', webm_path,
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            wav_path
        ], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting audio: {e.stderr.decode()}")
        return False

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

@app.post("/signup")
async def signup(user: UserCreate):
    result = SessionManager.create_user(user.email, user.password)
    if not result:
        raise HTTPException(status_code=400, detail="Could not create user")
    return {"message": "User created successfully"}

@app.post("/login")
async def login(user: UserLogin):
    session = SessionManager.login_user(user.email, user.password)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"session_id": session["session_id"]}

@app.post("/chat")
async def chat(message: Message):
    SessionManager.update_session_activity(message.session_id)
    previous_conversations = SessionManager.get_session_conversations(message.session_id)
    
    context = "\n".join([
        f"User: {conv['user_message']}\nAI: {conv['ai_response']}"
        for conv in previous_conversations[-5:]
    ])
    
    ai_response = therapist.generate_response(message.message)
    
    SessionManager.store_conversation(
        message.session_id,
        message.message,
        ai_response
    )
    
    return {"response": ai_response}

@app.get("/conversations/{session_id}")
async def get_conversations(session_id: str):
    conversations = SessionManager.get_session_conversations(session_id)
    return {"conversations": conversations}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, workers=1) 