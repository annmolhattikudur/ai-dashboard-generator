# 🤖 AI Dashboard Generator

**Natural language to insights — powered by RAG + Agentic AI**

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Claude API](https://img.shields.io/badge/Claude_API-Anthropic-orange?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red?style=flat-square&logo=streamlit)
![Power BI MCP](https://img.shields.io/badge/Power_BI-MCP_Ready-yellow?style=flat-square&logo=powerbi)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What This Does

Ask a business question in plain English. The AI finds the right data tables, writes the SQL, executes it, and renders a chart — in seconds, with zero SQL or DAX knowledge required.

Two output paths are available. **Quick Insights** delivers instant interactive Plotly visualizations directly in the browser. **Power BI Builder** generates Excel exports, DAX measures, and MCP-ready prompts for governed enterprise dashboards in Power BI Desktop.

The system understands business context — period-over-period growth, YTD comparisons, assortment metrics, geographic breakdowns — and self-corrects when queries fail. Every interaction feeds a feedback loop that makes future recommendations smarter.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                              │
│              "What is the sales growth for May 2018?"               │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                                │
│   app/streamlit_app.py  ·  Session state  ·  Two-path routing       │
└──────────┬───────────────────────────────────────┬──────────────────┘
           │                                       │
           ▼                                       ▼
  ⚡ Quick Insights                       📊 Power BI Builder
  (Path A)                                (Path B)
           │                                       │
           └──────────────┬────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                                   │
│              agents/orchestrator.py                                  │
│         Coordinates agents · Logs use cases · Routes paths          │
└──────┬────────────────────┬──────────────────────┬──────────────────┘
       │                    │                       │
       ▼                    ▼                       ▼
┌──────────────┐   ┌────────────────┐   ┌──────────────────────┐
│   AGENT 1    │   │    AGENT 2     │   │       AGENT 3        │
│   Table      │   │  SQL Generator │   │   Viz Recommender    │
│  Recommender │   │                │   │                      │
│              │   │ · Writes SQL   │   │ · Selects chart type │
│ · RAG over   │   │ · Validates    │   │ · Maps columns to    │
│   metadata   │   │ · Self-corrects│   │   axes               │
│ · Scores     │   │   (3 retries)  │   │ · Builds Plotly fig  │
│   tables     │   │ · Executes     │   │ · Generates DAX      │
└──────┬───────┘   └───────┬────────┘   └──────────┬───────────┘
       │                   │                        │
       ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       METADATA STORE                                 │
│  metadata/                                                           │
│  ├── table_registry.json      ← table descriptions, row counts      │
│  ├── data_dictionary.json     ← column-level semantics              │
│  ├── relationships.json       ← join paths between tables           │
│  ├── domain_knowledge.json    ← business rules, growth logic, KPIs  │
│  └── use_case_log.json        ← feedback loop (grows over time)     │
└─────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SQLite DATABASE                                   │
│   database/fmcg_warehouse.db  ·  8 tables  ·  ~1.55M rows          │
│   Olist Brazilian E-Commerce Dataset (Kaggle)                        │
└─────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────┐   ┌──────────────────────────────────────┐
│    PATH A OUTPUT         │   │           PATH B OUTPUT              │
│  · Plotly chart          │   │  · Excel export (Data + ChartConfig) │
│  · Interactive table     │   │  · DAX measures (Claude-generated)   │
│  · Excel / CSV download  │   │  · Power BI setup guide (.txt)       │
│                          │   │  · MCP command prompts               │
└──────────────────────────┘   └──────────────────────────────────────┘
```

---

## How the AI Works

### RAG (Retrieval-Augmented Generation)

This system does not fine-tune a model or train on your data. Instead, it uses **RAG** — at query time, all relevant metadata is retrieved from JSON files and injected into the LLM prompt as context. Claude reads the business rules, table schemas, metric definitions, and relationship graph before generating any SQL or chart recommendation.

This means:
- **Schema changes are instant** — update a JSON file, the AI adapts immediately
- **Business logic is explicit** — growth formulas, order status filters, and KPI definitions live in `domain_knowledge.json` as readable text
- **No retraining required** — the "knowledge" is in the metadata, not the model weights

### Agentic Pipeline

Three specialised agents run in sequence, each with a focused role:

| Agent | Input | Output | Claude's role |
|-------|-------|--------|---------------|
| Table Recommender | User question + full metadata | Ranked table list + suggested joins | Semantic matching: which tables contain the answer? |
| SQL Generator | Question + recommended tables + schemas + domain rules | Validated, executed SQL + DataFrame | Code generation + self-correction (up to 3 retries) |
| Viz Recommender | Question + DataFrame shape + growth viz spec | Plotly figure + chart config + DAX suggestion | Visual reasoning: what chart best answers the question? |

### Feedback Loop

Every query is logged to `metadata/use_case_log.json` with the question, tables used, SQL generated, and whether it was marked helpful. The Feedback & Learning page lets analysts correct table selections and SQL, which enriches the log. Future queries can reference this growing knowledge base — the system gets smarter with use.

---

## Screenshots

*Screenshots will be added after initial deployment.*

| Screen | Description |
|--------|-------------|
| `screenshots/main-interface.png` | Landing page with retail banner and navigation |
| `screenshots/quick-insights.png` | Quick Insights tab — question, chart, data table |
| `screenshots/growth-chart.png` | Sales growth combo bar+line chart |
| `screenshots/power-bi-builder.png` | Power BI Builder — DAX measures + MCP prompts |
| `screenshots/data-catalog.png` | Data Catalog — all tables, columns, relationships |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Olist Brazilian E-Commerce CSVs ([Kaggle dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce))

### 1. Clone the repository
```bash
git clone https://github.com/annmolhattikudur/ai-dashboard-generator.git
cd ai-dashboard-generator
```

### 2. Install dependencies
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Set your Anthropic API key
```bash
# Windows (Command Prompt):
set ANTHROPIC_API_KEY=your_key_here

# Windows (PowerShell):
$env:ANTHROPIC_API_KEY="your_key_here"

# macOS/Linux:
export ANTHROPIC_API_KEY=your_key_here
```

### 4. Add the CSV data
Download all 8 CSV files from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place them in:
```
data/raw/
├── olist_customers_dataset.csv
├── olist_geolocation_dataset.csv
├── olist_order_items_dataset.csv
├── olist_order_payments_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_orders_dataset.csv
├── olist_products_dataset.csv
└── olist_sellers_dataset.csv
```

### 5. Build the database
```bash
python setup_database.py
```
This loads all CSVs into SQLite with indexes. Expect ~30–60 seconds for 1.55M rows.

### 6. Generate metadata
```bash
python generate_metadata.py
```
This auto-generates all 5 metadata JSON files by profiling the database.

### 7. (Optional) Enrich metadata
Open `metadata/domain_knowledge.json` and add any domain-specific metric definitions, business rules, or known insights for your data. The richer this file, the more accurate the AI's answers will be.

### 8. Run the app
```bash
python -m streamlit run app/streamlit_app.py
```
Open `http://localhost:8501` in your browser.

---

## Power BI MCP Integration

### What is the Power BI Modeling MCP Server?

The [Power BI Modeling MCP Server](https://github.com/microsoft/powerbi-mcp) is a Model Context Protocol server that exposes Power BI Desktop's semantic model to AI assistants. It allows an AI to programmatically create tables, measures, and relationships in Power BI Desktop without manual DAX authoring.

### Setting It Up

**Option A — Claude Desktop:**
1. Install the Power BI Modeling MCP Server
2. Add it to your `claude_desktop_config.json`
3. Open Claude Desktop with Power BI Desktop running in the background
4. Paste the MCP prompts generated by Path B

**Option B — VS Code + GitHub Copilot:**
1. Install the MCP extension for VS Code
2. Configure the Power BI Modeling MCP Server
3. Use the generated MCP prompts in the Copilot chat pane

### How Path B Generates MCP Prompts

When you run a query in Power BI Builder, the system:
1. Executes the SQL and retrieves the data
2. Asks Claude to generate DAX measures equivalent to the SQL logic
3. Generates a structured `.txt` file of prompts you can paste directly into Claude Desktop or Copilot
4. The prompts instruct the MCP server to create the semantic model tables and measures automatically

### Current Limitations

The Power BI Modeling MCP Server can create and modify the **semantic model** (tables, measures, relationships) but **cannot yet create visuals or report pages**. You will still need to drag fields onto the canvas manually — but the hardest part (the DAX) is done for you.

---

## Project Structure

```
ai-dashboard-generator/
│
├── app/
│   └── streamlit_app.py          # Full Streamlit frontend (5 pages)
│
├── agents/
│   ├── orchestrator.py           # Coordinates all agents, manages flow
│   ├── table_recommender.py      # Agent 1: RAG-based table selection
│   ├── sql_generator.py          # Agent 2: SQL generation + self-correction
│   └── viz_recommender.py        # Agent 3: Chart recommendation + Plotly build
│
├── powerbi/
│   └── export_handler.py         # Excel export, DAX generation, MCP prompts
│
├── metadata/
│   ├── table_registry.json       # Table descriptions, row counts, column types
│   ├── data_dictionary.json      # Column-level descriptions and sample values
│   ├── relationships.json        # Foreign key relationships between tables
│   ├── domain_knowledge.json     # Business rules, KPI definitions, growth logic
│   └── use_case_log.json         # Feedback loop — query history and corrections
│
├── database/
│   └── fmcg_warehouse.db         # SQLite database (generated — not committed)
│
├── data/
│   └── raw/                      # Source CSVs (not committed — add your own)
│
├── docs/
│   ├── architecture.md           # Detailed architecture and RAG explanation
│   ├── enterprise-roadmap.md     # Path from POC to production on GCP
│   └── guide/                    # Phase-by-phase build guides
│
├── Background_Image/
│   └── Retail_Image.png          # Banner image for the app header
│
├── config.py                     # All paths, model names, app settings
├── setup_database.py             # Loads CSVs into SQLite
├── generate_metadata.py          # Auto-generates all metadata JSON files
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## Example Queries

| Question | What it demonstrates |
|----------|---------------------|
| What are the top 10 product categories by revenue? | Ranking + bar chart |
| What is the sales growth for May 2018? | Monthly YoY growth + combo chart |
| What is the YTD sales growth for Q1 2017? | YTD comparison |
| Show me monthly order trend over time | Time series + line chart |
| Which states have the highest average order value? | Geographic breakdown |
| What is the average delivery time by seller state? | Logistics metric |
| Compare payment methods by percentage of orders | Mix analysis + pie chart |
| Which product categories have the highest review scores? | Customer satisfaction ranking |
| What is the assortment growth by category for 2017? | Assortment metric + YoY |
| Which sellers have the most orders and highest revenue? | Multi-metric ranking |

---

## Enterprise Roadmap

For production deployment at scale, see [`docs/enterprise-roadmap.md`](docs/enterprise-roadmap.md).

Key upgrade path:
- **Data layer**: SQLite → BigQuery
- **Metadata RAG**: JSON files → Vector database (Vertex AI Vector Search / Pinecone)
- **Agents**: Direct API calls → Cloud Run microservices with LangChain/LangGraph
- **Auth**: None → SSO via Google Identity Platform or Azure AD
- **Frontend**: Streamlit → Looker or custom React + FastAPI
- **Power BI**: Local MCP → Power BI REST API for automated cloud publishing
- **Governance**: None → Cost controls, audit logging, RBAC, rate limiting

---

## Technologies Used

| Technology | Role |
|------------|------|
| Python 3.11 | Core language |
| [Anthropic Claude API](https://docs.anthropic.com/) | LLM backbone for all three agents |
| Streamlit 1.32+ | Web frontend framework |
| SQLite | Local analytical database |
| Plotly | Interactive chart rendering |
| Pandas | Data manipulation and DataFrame handling |
| OpenPyXL | Excel export for Power BI |
| Power BI Modeling MCP Server | Semantic model automation in Power BI Desktop |

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Author

**Annmol Hattikudur**
[github.com/annmolhattikudur](https://github.com/annmolhattikudur)

---

*Powered by Claude AI · RAG + Agentic Architecture*
