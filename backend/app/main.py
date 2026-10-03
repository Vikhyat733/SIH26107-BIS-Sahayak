from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import health, assistant, standards, compliance, certification, qco, laboratories, hallmarking

app = FastAPI(
    title="BIS Sahayak API",
    version="0.1.0",
    description="AI-assisted information and compliance services for SIH26107.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(standards.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(certification.router, prefix="/api")
app.include_router(qco.router, prefix="/api")
app.include_router(laboratories.router, prefix="/api")
app.include_router(hallmarking.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    from .rag.semantic_retrieval import init_semantic_store
    init_semantic_store()


@app.get("/")
def root():
    return {"name": "BIS Sahayak", "problem_statement": "SIH26107", "status": "development"}
