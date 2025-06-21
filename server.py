from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from thera_ai import TherapistAI
import os
from typing import Dict
import logging
import traceback
import soundfile as sf
import io
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize TherapistAI
therapist = TherapistAI()

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

@app.post("/process-interaction")
async def process_interaction(audio: UploadFile) -> Dict:
    if not audio:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    try:
        logger.info(f"Processing audio file: {audio.filename}")
        
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
            
            # Process the interaction
            logger.info("Processing interaction with TherapistAI")
            result = therapist.process_interaction(temp_wav)
            
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"  # Required for Heroku
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, workers=1) 