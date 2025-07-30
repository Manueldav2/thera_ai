# Thera AI Backend

This is the backend service for Thera AI, providing audio processing and AI-powered functionality.

## Project Structure
- `audio_utils.py`: Audio processing utilities
- `imports.py`: Project dependencies and imports
- `main.py`: Main application entry point
- `server.py`: Server implementation
- `thera_ai.py`: Core Thera AI functionality

## Environment Setup

1. Create a `.env` file in the root directory with the following variables:
```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_key_here

# Server Configuration
PORT=8000
```

2. Never commit your `.env` file - it contains sensitive information!

## Setup and Installation
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

## Security Notes
- Keep your API keys and credentials secure
- Never commit sensitive information to the repository
- Use environment variables for all sensitive data
- The `.env` file is ignored by git for security 