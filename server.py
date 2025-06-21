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

@app.post("/process-interaction")
async def process_interaction(audio: UploadFile) -> Dict:
    if not audio:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    try:
        logger.info(f"Processing audio file: {audio.filename}")
        
        # Read the audio content
        content = await audio.read()
        
        # Save the uploaded file temporarily
        temp_path = f"temp_recording.wav"
        try:
            with open(temp_path, "wb") as buffer:
                buffer.write(content)
            
            # Process the interaction
            logger.info("Processing interaction with TherapistAI")
            result = therapist.process_interaction(temp_path)
            
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
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"Cleaned up temporary file: {temp_path}")
    
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