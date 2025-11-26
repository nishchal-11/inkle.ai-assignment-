. .\.venv\Scripts\Activate.ps1

# Environment variables can be set here OR in .env file (recommended)
# The .env file is automatically loaded by server/main.py
# You can override .env values by setting environment variables here

# Nominatim configuration (can also be in .env)
$env:NOMINATIM_USER_AGENT = 'MultiAgentTourism/1.0 (contact: travel-console@inkle.ai)'
$env:NOMINATIM_EMAIL = 'travel-console@inkle.ai'

# Gemini API Key (recommended: set in .env file)
# Get your API key from: https://makersuite.google.com/app/apikey
# If set in .env file, you don't need to set it here
# $env:GEMINI_API_KEY = 'your-gemini-api-key-here'

# Optional: Override Gemini model (default: gemini-1.5-flash)
# Options: gemini-1.5-flash (fast), gemini-1.5-pro (better quality)
# $env:GEMINI_MODEL = 'gemini-1.5-pro'

uvicorn server.main:app --reload --port 8000
