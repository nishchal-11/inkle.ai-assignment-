# Gemini API Setup Guide

This project now uses Google's Gemini API for enhanced Natural Language Processing (NLP) to better understand user travel queries.

## How It Works

1. **User Input** → Gemini API analyzes the natural language query
2. **Gemini Output** → Extracts structured data (location, intent)
3. **Structured Data** → Used to call real APIs (geocoding, weather, places)

## Setup Instructions

### 1. Get a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### 2. Set the Environment Variable

#### Windows (PowerShell):
```powershell
$env:GEMINI_API_KEY = 'your-api-key-here'
```

#### Or edit `start_backend.ps1`:
```powershell
$env:GEMINI_API_KEY = 'your-api-key-here'
```

#### Linux/Mac:
```bash
export GEMINI_API_KEY='your-api-key-here'
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `google-generativeai` package.

## How It Works

- **With Gemini API Key**: Uses Gemini for intelligent NLP understanding
- **Without Gemini API Key**: Falls back to regex-based extraction (still works, but less intelligent)

## Benefits of Using Gemini

- Better understanding of natural language queries
- Handles complex sentence structures
- Extracts locations more accurately from context
- Understands intent even with ambiguous phrasing

## Example Queries Gemini Handles Better

- "I'm planning a 10-day escape to Tamilnadu, what should I know?"
- "What's the weather like and what can I see in Mysore?"
- "Planning a trip to Paris next month, need everything"

The system will automatically use Gemini if the API key is set, otherwise it falls back to the regex-based approach.

