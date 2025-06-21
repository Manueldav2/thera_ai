from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from thera_ai import TherapistAI
import os
from typing import Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # Allow localhost and all domains (update this with your specific domain later)
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
    
    if not audio.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="File must be a WAV audio file")
    
    try:
        logger.info(f"Processing audio file: {audio.filename}")
        
        # Save the uploaded file temporarily
        temp_path = f"temp_{audio.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                content = await audio.read()
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
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 