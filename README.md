# AI-Powered Natural Language Dashboard Generator

A proof-of-concept system where users can create insight-rich dashboards and find the right data tables using natural language — no SQL or DAX knowledge required.

## Dataset
Olist Brazilian E-Commerce dataset (~100k orders, 2016–2018).

## Architecture
- **Agent 1 – Table Recommender**: Finds the right tables using RAG over metadata
- **Agent 2 – SQL Generator**: Writes and self-corrects SQL queries
- **Agent 3 – Viz Recommender**: Suggests the best chart type
- **Orchestrator**: Coordinates all agents end-to-end

## Output Paths
- **Path A (Quick Insights)**: Instant Plotly visualizations in Streamlit
- **Path B (Power BI)**: Excel export + DAX measures + setup instructions

## Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python setup_database.py
python generate_metadata.py
streamlit run app/streamlit_app.py
```

## Phase Status
- [x] Phase 1: Database + Metadata
- [ ] Phase 2: Agents
- [ ] Phase 3: Frontend + Power BI Export
