# BIS Sahayak / ManakMitra

**SIH Problem:** SIH26107
**Title:** AI-powered Intelligent Assistant for Indian Standards & BIS Services for Industries and Consumers

## Problem Statement
The Bureau of Indian Standards (BIS) oversees numerous standards, quality control orders (QCOs), testing protocols, and certifications. Navigating this vast regulatory landscape is complex for industries (manufacturers, importers) and consumers. There is a need for a unified, intelligent assistant that provides accurate, evidence-backed information without hallucination.

## Current implemented capabilities
- Standards discovery
- Product → Standard recommendation
- Evidence-backed BIS questions
- Certification guidance
- QCO information
- Certification + QCO workflow
- BIS LIMS laboratory search
- Location-aware laboratory filtering
- Compliance Check interface
- Deterministic compliance engine
- Evidence/provenance architecture
- Trust-first AI architecture

*Note: Compliance PDF extraction is **Under active development**.*

## Current Status

### Working
- Assistant
- Product → Standard
- Certification
- QCO
- BIS LIMS Testing Labs
- Lab pagination
- Location filtering
- Evidence/provenance

### In Progress
- MTC/Test Report PDF extraction (Under active development)
- Compliance result automation
- Multilingual/Hindi
- Hallmarking
- Final integration/polish

## Architecture
Frontend
↓
FastAPI backend
↓
Intent / entity routing
↓
Retrieval / knowledge services
↓
Authoritative BIS evidence
↓
Deterministic compliance engine
↓
Structured response

## Folder Structure
```text
SIH26107-BIS-Sahayak/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # REST API endpoints (Assistant, Standards, Compliance, etc.)
│   │   ├── core/             # Configuration and environment setup
│   │   ├── engine/           # Deterministic BIS compliance engines
│   │   ├── rag/              # RAG pipeline (Ingestion, Chunking, Retrieval, Grounding)
│   │   ├── services/         # Business logic (Standards, QCO, Labs, Hallmarking)
│   │   └── main.py           # FastAPI entry point
│   ├── data/
│   │   ├── standards/        # JSON Knowledge seeds for Standards
│   │   ├── qco/              # QCO seed registry
│   │   └── demo_reports/     # Test/MTC sample reports
│   ├── tests/                # Automated pytest suite
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
│
├── frontend/
│   ├── src/                  # React components, styles, App.tsx
│   ├── package.json
│   ├── Dockerfile
│   └── index.html
│
├── docs/
│   └── ARCHITECTURE.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Setup & Environment Variables
Copy `.env.example` to `.env` in the project root.

```env
VITE_API_URL=http://localhost:8000/api
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key_here
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:pass@localhost:5432/bissahayok
VECTOR_DB_URL=http://localhost:8080
```
*(Note: Never hardcode API keys in the source code.)*

## Running Locally

**Backend:**
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend API: `http://localhost:8000/docs`

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Frontend UI: `http://localhost:5173`

## API Endpoints
- `POST /api/assistant/ask` : Natural language assistant queries.
- `GET /api/standards` : Search or list Indian Standards.
- `POST /api/standards/recommend` : Recommend standards based on product description.
- `GET /api/standards/qco` : Search QCO registry.
- `POST /api/compliance/audit` : Audit a test report deterministically.
- `POST /api/compliance/verify` : Verify ISI, CRS, or HUID identifiers.
- `GET /api/certification` : Certification workflows.
- `GET /api/laboratories` : Find testing labs.
- `GET /api/hallmarking` : Hallmarking info.

## Anti-hallucination Approach
- **Grounding Check:** If retrieved evidence is insufficient, the system explicitly refuses to answer and warns the user.
- **Traceability:** Every substantive answer exposes its source citations.
- **Strict Separation:** The LLM explains deterministic results; it never generates deterministic results.

## Testing
Automated tests verify core engines, RAG components, API endpoints, and identifier detection.
```bash
cd backend
pytest -q
```
