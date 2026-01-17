# BioScan Backend - Architecture

## System Overview

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│             │  PDF    │              │  Text   │              │
│  Frontend   │────────▶│   FastAPI    │────────▶│  PDF Parser  │
│  (React)    │         │   Backend    │         │  (PyPDF2)    │
│             │◀────────│              │◀────────│              │
└─────────────┘  JSON   └──────────────┘  String └──────────────┘
                              │
                              │ Extracted Text
                              ▼
                        ┌──────────────┐
                        │              │
                        │ LLM Provider │
                        │  Abstraction │
                        │              │
                        └──────┬───────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
         ┌──────────┐   ┌──────────┐  ┌──────────┐
         │   Groq   │   │  Claude  │  │  OpenAI  │
         │   API    │   │   API    │  │   API    │
         └──────────┘   └──────────┘  └──────────┘
```

## Core Components

### 1. main.py - FastAPI Application

**Responsibilities:**
- HTTP request/response handling
- File upload validation (type, size)
- CORS configuration
- Error handling
- API endpoint routing

**Key Endpoints:**

| Endpoint | Method | Purpose | Input | Output |
|----------|--------|---------|-------|--------|
| `/` | GET | Root info | None | App info JSON |
| `/health` | GET | Health check | None | Status |
| `/api/analyze` | POST | Analyze protocol | PDF file | Analysis result |
| `/api/providers` | GET | List LLMs | None | Provider list |

**Flow:**
1. Receive PDF upload
2. Validate file (type, size ≤ 20MB)
3. Extract text via `pdf_parser`
4. Get LLM provider via `get_llm_provider()`
5. Analyze protocol
6. Return structured JSON

### 2. llm_providers.py - LLM Abstraction Layer

**Design Pattern:** Factory + Strategy Pattern

**Architecture:**
```python
LLMProvider (Abstract Base)
    │
    ├── GroqProvider
    ├── ClaudeProvider
    └── OpenAIProvider
```

**Benefits:**
- ✅ Swap LLMs without changing main code
- ✅ Consistent interface across providers
- ✅ Easy to add new providers
- ✅ Fallback parsing if JSON fails

**Key Methods:**

| Method | Purpose | Returns |
|--------|---------|---------|
| `analyze_protocol(text)` | Main analysis | Dict with results |
| `_build_analysis_prompt(text)` | Create prompt | Formatted prompt string |
| `_parse_analysis(response)` | Parse LLM output | Structured dict |

**Provider Selection:**
```python
LLM_PROVIDER env var → get_llm_provider() → Instantiate correct class
```

### 3. pdf_parser.py - PDF Text Extraction

**Responsibilities:**
- Extract text from PDF bytes
- Handle encrypted PDFs (reject)
- Handle scanned images (reject with helpful message)
- Page-by-page extraction with error resilience

**Error Handling:**
- Encrypted PDF → Clear error message
- Empty/scanned PDF → Suggest OCR
- Corrupted PDF → Specific error
- Partial failures → Continue with remaining pages

### 4. Data Flow

```
1. Frontend uploads PDF
         ↓
2. FastAPI receives file (main.py)
         ↓
3. Validate file type & size
         ↓
4. pdf_parser.extract_text_from_pdf(bytes)
         ↓
5. get_llm_provider() returns provider instance
         ↓
6. provider.analyze_protocol(text)
         ↓
7. LLM API call with structured prompt
         ↓
8. Parse JSON response
         ↓
9. Return AnalysisResult to frontend
```

## Configuration

### Environment Variables (.env)

```bash
LLM_PROVIDER=groq          # Which LLM to use
GROQ_API_KEY=xxx           # Groq API key
ANTHROPIC_API_KEY=xxx      # Claude API key (optional)
OPENAI_API_KEY=xxx         # OpenAI API key (optional)
```

### LLM Models Used

| Provider | Model | Why |
|----------|-------|-----|
| Groq | `llama-3.1-70b-versatile` | Fast, free, capable |
| Claude | `claude-3-5-sonnet-20241022` | Best reasoning |
| OpenAI | `gpt-4o-mini` | Cost-effective |

## Response Schema

```python
AnalysisResult:
    success_probability: int (0-100)
    critical_issues: List[{issue: str, description: str}]
    warnings: List[{issue: str, description: str}]
    passed_checks: List[{check: str, description: str}]
    estimated_cost: str | None
    estimated_time: str | None
    suggestions: List[str]
    raw_analysis: str
```

## Error Handling Strategy

| Error Type | HTTP Status | User Message |
|------------|-------------|--------------|
| Wrong file type | 400 | "Only PDF files supported" |
| File too large | 400 | "Max 20MB" |
| Empty PDF | 400 | "No text extracted" |
| Encrypted PDF | 400 | "Provide unencrypted file" |
| API key missing | 500 | "LLM not configured" |
| LLM API error | 500 | Specific API error |

## Performance Considerations

### File Size Limits
- **Upload:** 20MB max
- **Text sent to LLM:** First 8000 chars (to avoid token limits)

### Timeouts
- PDF parsing: ~1-2 seconds
- LLM analysis: ~5-10 seconds (Groq is fastest)
- Total: < 15 seconds typical

### Rate Limits
- **Groq free:** ~14,400 requests/month
- **Claude:** Tier-dependent
- **OpenAI:** Tier-dependent

## Security

### Input Validation
- File type check (PDF only)
- File size check (20MB max)
- Text extraction safety (PyPDF2 handles malicious PDFs)

### API Keys
- Stored in `.env` (not in git)
- Loaded via `os.getenv()`
- Never exposed in responses

### CORS
- Restricted to `localhost:5173` (frontend)
- No wildcard origins

## Dependencies

```
fastapi         - Web framework
uvicorn         - ASGI server
python-multipart - File upload handling
PyPDF2          - PDF text extraction
groq            - Groq API client
anthropic       - Claude API client
openai          - OpenAI API client
pydantic        - Data validation
python-dotenv   - Environment variables
```

## Testing Strategy (Post-Build)

1. **Unit Tests:** Test each provider separately
2. **Integration Tests:** Full API endpoint tests
3. **Sample Protocols:** Test with real protocols
4. **Error Cases:** Test all error paths

---

**Last Updated:** January 16, 2026 - Initial architecture
