# BioScan Backend

FastAPI backend for analyzing experimental protocols using LLM-powered analysis.

## Features

- **Multi-LLM Support**: Groq (free), Claude, or OpenAI
- **Protocol Analysis**: Detects critical issues, warnings, and good practices
- **PDF Parsing**: Extracts text from PDF protocols
- **RESTful API**: Clean endpoints for frontend integration

## Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API key
```

Get a free Groq API key: https://console.groq.com

### 3. Run Server

```bash
python main.py
```

Server runs at: `http://localhost:8000`

API docs: `http://localhost:8000/docs`

## API Endpoints

### POST /api/analyze
Upload a PDF protocol for analysis.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (PDF, max 20MB)

**Response:**
```json
{
  "success_probability": 75,
  "critical_issues": [...],
  "warnings": [...],
  "passed_checks": [...],
  "estimated_cost": "$5,000",
  "estimated_time": "4 weeks",
  "suggestions": [...]
}
```

### GET /health
Health check endpoint

### GET /api/providers
List available LLM providers

## Switching LLM Providers

Edit `.env`:

```bash
# Use Groq (free)
LLM_PROVIDER=groq
GROQ_API_KEY=your_key

# Or use Claude
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your_key

# Or use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
```

## Project Structure

```
Scan_backend/
├── main.py              # FastAPI app and endpoints
├── llm_providers.py     # LLM abstraction layer
├── pdf_parser.py        # PDF text extraction
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── .env.example         # Example env file
└── README.md           # This file
```

## Development

Run with auto-reload:
```bash
uvicorn main:app --reload --port 8000
```

## Troubleshooting

**"GROQ_API_KEY not found"**
- Make sure `.env` file exists and contains your API key
- Restart the server after updating `.env`

**"Could not extract text from PDF"**
- PDF might be a scanned image (needs OCR)
- Try a different PDF

**CORS errors**
- Frontend must run on `localhost:5173` or update CORS settings in `main.py`
