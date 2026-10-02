# BIS Sahayak Architecture

## Target PS
SIH26107 — AI-powered Intelligent Assistant for Indian Standards and BIS Services for Industries and Consumers.

## High-level flow

User → React frontend → FastAPI → intent/service routing → retrieval/knowledge layer → evidence → deterministic verification where applicable → response.

## Trust model

- LLM is an explanation layer, not the source of truth.
- Standards and regulatory claims should be grounded in authoritative BIS/Government material before production use.
- Deterministic calculations and compliance checks are performed by Python rule engines.
- Unverified/demo registry data must never be represented as live BIS records.

## Current implementation

- Deterministic compliance evaluator reused from supplied project.
- Four-stage identifier verifier reused as a demo engine.
- STI planner retained as a compliance-planning capability.
- Seed standard schemas and QCO registry retained under `backend/data`.
- FastAPI API and React/Vite UI added.
- Basic deterministic knowledge search added as a temporary bridge.

## Next implementation layers

1. Authoritative source ingestion and document versioning.
2. Hybrid BM25 + vector retrieval.
3. Reranking and evidence extraction.
4. Product → standard recommendation.
5. Certification workflow knowledge.
6. Testing laboratory discovery.
7. Hallmarking guidance.
8. Hindi and additional Indian languages.
9. Document/OCR pipeline for test reports.
10. Admin/source refresh and evaluation suite.
