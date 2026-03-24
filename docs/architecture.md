# Architecture: AI-Powered Natural Language Dashboard Generator

## Overview

A multi-agent RAG system that converts natural language questions into data visualizations and Power BI assets — no SQL or DAX knowledge required.

## Components

### Data Layer
- **SQLite Database** (`database/fmcg_warehouse.db`): All 8 Olist tables loaded from CSV
- **Metadata Store** (`metadata/`): JSON files describing tables, columns, relationships, and domain knowledge

### Agent Layer
1. **Table Recommender** (`agents/table_recommender.py`): Given a user question, uses metadata RAG to identify which tables are needed
2. **SQL Generator** (`agents/sql_generator.py`): Writes SQL against the identified tables, validates it, and self-corrects on error
3. **Viz Recommender** (`agents/viz_recommender.py`): Selects the best chart type and configuration for the data
4. **Orchestrator** (`agents/orchestrator.py`): Coordinates all agents, manages context, routes to Path A or Path B

### Output Layer
- **Path A — Quick Insights**: Streamlit + Plotly for instant analyst visualizations
- **Path B — Power BI**: Excel export + DAX measure generation + setup instructions

## RAG Context Flow

```
User Question
     ↓
Table Recommender ← [table_registry.json + data_dictionary.json + domain_knowledge.json]
     ↓
SQL Generator ← [relationships.json + domain_knowledge.json + table schemas]
     ↓
Execute SQL → DataFrame
     ↓
Viz Recommender ← [domain_knowledge.json + query type]
     ↓
Path A: Plotly Chart  |  Path B: Excel + DAX
```

## Metadata Files

| File | Purpose |
|------|---------|
| `table_registry.json` | Table-level descriptions, row counts, column classifications |
| `data_dictionary.json` | Column-level types, samples, descriptions |
| `relationships.json` | How tables join (verified + auto-detected) |
| `domain_knowledge.json` | Business metric definitions, SQL patterns, business rules |
| `use_case_log.json` | Feedback loop — stores successful Q&A pairs for few-shot learning |
