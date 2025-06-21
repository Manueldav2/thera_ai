from fastapi import FastAPI, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from thera_ai import TherapistAI
from session_manager import SessionManager
from typing import Dict, Optional
import os
import logging
import traceback
import soundfile as sf
import io
import subprocess
from pydantic import BaseModel
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS to be completely permissive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight requests for 24 hours
)

# Initialize TherapistAI
therapist = TherapistAI()

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Message(BaseModel):
    session_id: str
    message: str

def convert_webm_to_wav(webm_path: str, wav_path: str) -> bool:
    """Convert webm audio file to wav format using ffmpeg"""
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
        
        # Parse conversation history if provided
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
        
        # Read the audio content
        content = await audio.read()
        
        # Save the uploaded file temporarily
        temp_webm = "temp_recording.webm"
        temp_wav = "temp_recording.wav"
        try:
            # Save the webm file
            with open(temp_webm, "wb") as buffer:
                buffer.write(content)
            
            # Convert webm to wav
            if not convert_webm_to_wav(temp_webm, temp_wav):
                raise ValueError("Failed to convert audio file")
            
            # Process the interaction with context
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
            # Clean up the temporary files
            for temp_file in [temp_webm, temp_wav]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")
    
    except Exception as e:
        logger.error(f"Error processing interaction: {str(e)}")
        logger.error(traceback.format_exc())  # Log the full traceback
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
    # Update session activity
    SessionManager.update_session_activity(message.session_id)
    
    # Get previous conversations for context
    previous_conversations = SessionManager.get_session_conversations(message.session_id)
    
    # Process the message with context
    context = "\n".join([
        f"User: {conv['user_message']}\nAI: {conv['ai_response']}"
        for conv in previous_conversations[-5:]  # Use last 5 conversations for context
    ])
    
    # Get AI response
    ai_response = therapist.get_response(message.message, context=context)
    
    # Store the conversation
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
    host = "0.0.0.0"  # Required for Heroku
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, workers=1) 