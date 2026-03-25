# Frequently Asked Questions

Questions asked during development and testing of the AI Dashboard Generator POC.

---

## Power BI Builder

**Q: What have we built in Power BI Builder and how can I test it?**

The Power BI Builder generates 4 outputs from a natural language question:
1. **Excel file** (`powerbi_export.xlsx`) — 2 sheets: `Data` (query results) and `ChartConfig` (recommended chart type, axis fields, title)
2. **Power BI Setup Guide** (`.txt`) — step-by-step manual instructions for building the visual in Power BI Desktop
3. **DAX Measures** — Claude-generated DAX code blocks (3–5 measures per chart) shown on screen for copy-paste into Power BI
4. **MCP Command Prompts** (`.txt`) — ready-to-paste prompts for Claude Desktop with the Power BI Modeling MCP Server

To test: run the app, go to Power BI Builder, enter a question like *"Show monthly revenue trend for 2017"*, click Prepare for Power BI, then download the Excel and Setup Guide files.

---

**Q: I understand that the only thing AI can do currently is create the semantic layer within Power BI and not the visualization itself. What are we generating and how can I view this in Power BI?**

Our solution generates data and instructions — not a `.pbix` file. To use the outputs in Power BI:

**Manual path (Path A — works today):**
1. Open Power BI Desktop → New report
2. Home → Get Data → Excel Workbook → select `powerbi_export.xlsx` → load the `Data` sheet only
3. Add DAX measures: right-click the `Data` table in Fields pane → New Measure → paste each measure
4. Build the visual by dragging fields to Axis, Values, Legend as instructed in the Setup Guide
5. Format and publish

**MCP path (Path B — experimental):**
- The Power BI Modeling MCP Server (community-built) can automate creating the data table and DAX measures in Power BI Desktop via Claude Desktop
- It **cannot** create visuals on the report canvas — that capability is still in preview in Microsoft's roadmap
- The visual still needs to be built manually

See `docs/architecture.md` for the full breakdown of what each output does and what still requires manual work.

---

**Q: I want to test Power BI Builder Path B (MCP path) completely end to end. Do I need Power BI Desktop and the Power BI MCP Server?**

Yes for Power BI Desktop (free, Windows-only, download from Microsoft). For the MCP path specifically:
- You also need Claude Desktop and a Power BI Modeling MCP Server
- There is no official fully-released Microsoft MCP server for Power BI Desktop today — only community-built implementations
- The MCP path automates table creation and DAX measures but not visual creation

**Recommendation for POC testing:** Test Phase 1 (manual path) only. It fully validates the value proposition. Phase 2 (MCP path) is out of scope for the POC.

---

## Multi-Chart Feature

**Q: Can the AI detect when I am asking for multiple charts at once, and handle each one separately?**

Yes — this was implemented as Agent 1 (Query Decomposer). When you enter a question like:
> *"Show monthly revenue trend for 2017, top 10 product categories for 2017, and revenue by geographic area"*

The Query Decomposer detects 3 distinct chart requests and splits them into focused sub-questions. Each runs through the full pipeline independently. Results are shown in separate tabs (Chart 1 | Chart 2 | Chart 3) on both Quick Insights and Power BI Builder.

A single question like *"What are the top 5 sellers by revenue?"* is detected as a single chart and behaves exactly as before — no tabs, no change in UX.

---

**Q: How many agents do we have in the architecture after the multi-chart feature was added?**

Five agents:

| # | Agent | Role |
|---|-------|------|
| 1 | Query Decomposer | Detects single vs. multi-chart, splits into focused sub-questions |
| 2 | Table Recommender | RAG-based table selection |
| 3 | SQL Generator | SQL generation + self-correction (up to 3 retries) |
| 4 | Viz Recommender | Chart type selection + Plotly figure build |
| 5 | Orchestrator | Coordinates all agents, logs use cases |

For a 3-chart request: 1 (Decomposer) + 3 × 3 (Table Recommender + SQL Generator + Viz Recommender) = 10 total agent calls.

---

## Deployment

**Q: How do I take the Streamlit frontend live online?**

Recommended platform: **Streamlit Community Cloud** (free, made for Streamlit, direct GitHub integration).

Main challenge: the SQLite database is 161.5 MB — over GitHub's 100 MB single-file limit. Solution: **Git LFS** (Large File Storage), which stores large files on GitHub's LFS server. Streamlit Community Cloud supports Git LFS and downloads the file during deployment.

Steps: install Git LFS → track database file → commit and push → deploy on share.streamlit.io → set secrets (ANTHROPIC_API_KEY, APP_PASSWORD).

---

**Q: I have installed Git LFS. Do we need to push to GitHub again?**

Yes — for two reasons:
1. All session work (multi-chart, Query Decomposer, password protection, docs) was not yet pushed
2. The database still needed to be added via Git LFS

Everything was committed and pushed in one go including all session changes + LFS setup + 161 MB database.

---

**Q: How does the live app on Streamlit get full information about my project and is able to run everything including Claude Agents? Is it because it gets access to GitHub Repo, API Keys, and Git LFS?**

Yes — exactly. Three things work together:

1. **GitHub repo** — Streamlit pulls all the code (`app/`, `agents/`, `powerbi/`, `metadata/`, `config.py`, `requirements.txt`) directly from your repo. This is everything needed to run the app.
2. **Git LFS** — the 161 MB SQLite database (`database/fmcg_warehouse.db`) is stored in GitHub via LFS. Streamlit downloads it during deployment so the agents have real data to query.
3. **Secrets (API keys)** — `ANTHROPIC_API_KEY` and `APP_PASSWORD` are stored in Streamlit Cloud's secrets manager (not in the repo). They are injected at runtime via `st.secrets` — this is how `config.py` reads them through the `_get_secret()` function.

Without any one of these three, the app would not work. The code runs on Streamlit's servers, not your local machine.

---

**Q: Can we add the live URL to my GitHub repo so visitors know the app is deployed?**

Yes — two places:
1. **README.md** — a Live Demo badge and link were added at the top
2. **GitHub repo homepage** — go to your repo → click the ⚙️ gear icon next to "About" → paste the URL in the Website field → Save

---

## GitHub & Git

**Q: Nobody online can make changes to my GitHub repo, right?**

Correct. The repo is public — anyone can view and clone it — but only you can push changes. GitHub only allows pushes from authenticated accounts that own the repo or are explicitly added as collaborators.

---

**Q: Why are my commits not showing on the GitHub contributions graph?**

The commits were authored with a placeholder identity (`dev@ai-dashboard.local`) that doesn't match your GitHub account email. GitHub only counts contributions when the commit email matches the account email.

Fix by running in PowerShell:
```bash
git config --global user.name "Annmol Hattikudur"
git config --global user.email "your-github-email@example.com"
```
Use the email shown at: github.com → Settings → Emails. All future commits will then count.

---

**Q: Do I run the git config lines in PowerShell?**

Yes — open PowerShell and run both lines, replacing the email with your actual GitHub account email. Verify with:
```bash
git config --global user.name
git config --global user.email
```

---

## Feedback & Learning

**Q: Does the Feedback & Learning page (Query History) update any file in the project?**

Yes — `metadata/use_case_log.json`. It is updated at two points:
1. **Automatically on every query** — the orchestrator appends a new entry with the question, tables used, SQL generated, and timestamp. `was_helpful` is `null` at this point.
2. **When you click Save Feedback** — updates `tables_actually_used`, `sql_used` (if you corrected the SQL), and `was_helpful` (`true`/`false`/`null`) for that specific entry.

---

**Q: Will feedback given on the live app be lost if the webpage is refreshed?**

Not on a simple browser refresh — that only reloads the UI. The file is written on the server, not in your browser.

What does lose the data:
- The app **goes to sleep** after ~1 hour of inactivity and restarts on a new container — file resets to the committed version
- You **redeploy** the app (push to GitHub) — file resets to whatever is in the repo
- Streamlit does a routine server restart

For the POC this is a known limitation. To make feedback persistent, the options are Google Sheets (simplest, Streamlit has native support) or a hosted database like Supabase.

---

## Architecture & Documentation

**Q: Can you update the Architecture section in the sidebar and add motivation text to Quick Insights and Power BI Builder pages?**

Done. Changes made:
- Sidebar architecture section updated to list all 5 agents
- Blue motivation card added to Quick Insights explaining the "instant answers without SQL" value
- Blue motivation card added to Power BI Builder explaining the "eliminate data prep and DAX writing" value
- Both cards end with the Olist Brazilian E-Commerce Dataset attribution

---

**Q: Can you update the architecture diagram and all documentation to reflect the 5-agent architecture?**

All documentation updated:
- `README.md` — new architecture ASCII diagram, 5-agent pipeline table, updated project structure, new multi-chart example query
- `docs/architecture.md` — full rewrite: new system diagram, Agent 1 section, renumbered agents, multi-chart data flow example, updated config section
- `docs/enterprise-roadmap.md` — Query Decomposer added to microservices diagram and LangGraph example
- `docs/guide/Phase_5_Prompt_for_Claude_Code.md` — new file documenting all Phase 5 work
- `docs/guide/AI_Dashboard_POC_Guide_and_Claude_Code_Prompt.md` — project structure updated

---

## General

**Q: Can you summarize the development for my CV?**

See the CV summary — short version:

> Built a live, deployed AI dashboard generator using a 5-agent RAG pipeline (Anthropic Claude) that converts natural language into SQL, Plotly charts, and Power BI DAX measures — including automatic multi-chart decomposition, self-correcting SQL generation, and access-controlled cloud deployment on Streamlit Community Cloud. Dataset: Olist Brazilian E-Commerce (~1.55M rows).

Full version with bullet points available in the previous session response.
