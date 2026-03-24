# Enterprise Roadmap: Scaling to GCP / BigQuery

## Current POC Architecture
Local SQLite + Claude API + Streamlit

## Phase 2: Cloud Data Layer
- Replace SQLite with **BigQuery** as the analytical data warehouse
- Store CSVs in **Google Cloud Storage**; load via BigQuery Data Transfer
- Use **BigQuery ML** for in-database ML (forecasting, clustering)

## Phase 3: Enterprise Agent Layer
- Deploy agents as **Cloud Run** microservices
- Use **Vertex AI** for LLM inference (Gemini) or keep Anthropic API
- Store metadata in **Firestore** for real-time updates
- Add **embedding-based RAG** with Vertex AI Vector Search

## Phase 4: Enterprise Frontend
- Replace Streamlit with **Looker** or custom React app
- Integrate with **Power BI Service** via REST API for automated report publishing
- Add **SSO** via Google Identity Platform

## Phase 5: Production Hardening
- Query caching with **Redis**
- Audit logging in **BigQuery**
- Cost controls and query budget limits
- Multi-tenant support with row-level security
