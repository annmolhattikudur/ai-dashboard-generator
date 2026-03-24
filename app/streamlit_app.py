"""
Streamlit Frontend — Dual-Tab Architecture
Tab A: Quick Insights  (Path A — instant Plotly charts)
Tab B: Power BI Builder (Path B — DAX measures + Excel export)
Sidebar: Data Catalog | Feedback & Learning | Example Queries
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Page config (must be first Streamlit call) ─────────────────
st.set_page_config(
    page_title="AI Dashboard Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Path setup ─────────────────────────────────────────────────
import sys
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.orchestrator import process_query
from config import (
    TABLE_REGISTRY_PATH,
    DATA_DICTIONARY_PATH,
    RELATIONSHIPS_PATH,
    USE_CASE_LOG_PATH,
)
from powerbi.export_handler import (
    export_to_excel_bytes,
    export_to_csv_bytes,
    export_standardized_excel_bytes,
    generate_powerbi_instructions,
    generate_dax_measures,
    generate_mcp_commands,
)


# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: linear-gradient(160deg, #EEF2F7 0%, #E8EDF5 100%);
}

/* ── Reduce Streamlit's default paddings ── */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
}
/* Tighten vertical gap between Streamlit blocks */
[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B1F3A 0%, #0D2B50 55%, #0E3D6B 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #D6E8F8 !important; }

/* Sidebar brand strip */
.sidebar-brand {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff !important;
    letter-spacing: 0.3px;
    padding: 0 2px 10px 2px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 4px;
}
.sidebar-brand span { color: #4EAADF !important; }

/* Nav section headings */
.nav-section {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #6FA8C8 !important;
    margin: 14px 0 5px 0;
    padding-left: 2px;
}

/* Nav buttons */
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    text-align: left;
    background: transparent;
    color: #C8DFF2 !important;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13.5px;
    font-weight: 500;
    margin-bottom: 2px;
    transition: background 0.15s ease;
    min-height: unset !important;
    height: auto !important;
    line-height: 1.4 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.09) !important;
    color: #ffffff !important;
    border: none;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(255,255,255,0.13) !important;
    color: #ffffff !important;
    border-left: 3px solid #4EAADF !important;
    font-weight: 600;
}
/* Tighten gap between nav buttons only */
[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div { gap: 0.1rem !important; }

/* Sidebar divider */
.sidebar-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.1);
    margin: 12px 0;
}

/* Sidebar info text */
.sidebar-info {
    font-size: 11.5px;
    color: #7AAEC8 !important;
    line-height: 1.6;
    margin: 0;
}
.sidebar-info a { color: #4EAADF !important; }

/* ── Main header ── */
.app-header {
    background: linear-gradient(135deg, #0B1F3A 0%, #0D3B6E 50%, #1565C0 100%);
    padding: 16px 26px;
    border-radius: 10px;
    margin-bottom: 14px;
    box-shadow: 0 4px 20px rgba(11, 31, 58, 0.24);
}
.app-header h1 {
    color: white;
    margin: 0;
    font-size: 25px;
    font-weight: 700;
    letter-spacing: -0.3px;
}
.app-header p {
    color: #90C4E8;
    margin: 4px 0 0 0;
    font-size: 13.5px;
    font-weight: 400;
}

/* ── Retail banner image ── */
[data-testid="stImage"] img {
    max-height: 170px;
    object-fit: cover;
    object-position: center;
    width: 100%;
    border-radius: 8px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.1);
}

/* ── Content cards (expanders) ── */
[data-testid="stExpander"] {
    background: white;
    border-radius: 10px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 8px;
}

/* ── Confidence badges ── */
.badge-high   { background: linear-gradient(90deg,#1B6B3A,#27AE60); color:white;
                padding:4px 12px; border-radius:20px; font-weight:600; font-size:12px;
                box-shadow: 0 2px 6px rgba(39,174,96,0.3); }
.badge-medium { background: linear-gradient(90deg,#B7770D,#F0AC1C); color:white;
                padding:4px 12px; border-radius:20px; font-weight:600; font-size:12px;
                box-shadow: 0 2px 6px rgba(240,172,28,0.3); }
.badge-low    { background: linear-gradient(90deg,#922B21,#E74C3C); color:white;
                padding:4px 12px; border-radius:20px; font-weight:600; font-size:12px;
                box-shadow: 0 2px 6px rgba(231,76,60,0.3); }

/* ── Section cards ── */
.section-card {
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    padding: 14px 18px;
    margin-bottom: 10px;
    border: 1px solid #EBF0F7;
}

/* ── Primary buttons (main CTA) ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1565C0, #1976D2);
    border: none;
    border-radius: 8px;
    padding: 9px 22px;
    font-weight: 600;
    font-size: 14px;
    box-shadow: 0 3px 10px rgba(21,101,192,0.35);
    transition: all 0.2s ease;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 5px 16px rgba(21,101,192,0.45);
    transform: translateY(-1px);
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: white;
    border-radius: 10px;
    padding: 10px 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #EBF0F7;
}

/* ── Footer ── */
.footer {
    text-align: center;
    color: #94A3B8;
    font-size: 12px;
    margin-top: 28px;
    padding-top: 14px;
    border-top: 1px solid #E2E8F0;
}
.footer a { color: #1565C0; text-decoration: none; font-weight: 500; }
.footer a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────

def _init_state():
    defaults = {
        "page": "⚡ Quick Insights",
        # Path A state
        "qa_result": None,
        "qa_question": "",
        "qa_approved_tables": [],
        "qa_sql_override": "",
        "qa_ran": False,
        # Path B state
        "pbi_result": None,
        "pbi_question": "",
        "pbi_dax": [],
        "pbi_ran": False,
        # Shared
        "prefill_question": "",
        "prefill_tab": "quick",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _load_json(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _confidence_badge(result: dict) -> str:
    """Return HTML badge based on error count and row count."""
    errors = result.get("errors", [])
    row_count = result.get("sql_results", {}).get("row_count", 0)
    if errors:
        return '<span class="badge-low">LOW — Results may not match your question</span>'
    if row_count == 0:
        return '<span class="badge-medium">MEDIUM — No rows returned; review query</span>'
    return '<span class="badge-high">HIGH — Query executed successfully</span>'


def _run_query(question: str, override_tables: list | None = None) -> dict:
    """Run the orchestrator and cache result in session state."""
    with st.spinner("Thinking... running all three agents..."):
        result = process_query(question, override_tables=override_tables or None)
    return result


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────

st.markdown("""
<div class="app-header">
  <h1>📊 AI Dashboard Generator</h1>
  <p>Natural Language to Insights — No SQL or DAX Knowledge Required</p>
</div>
""", unsafe_allow_html=True)

st.image(
    str(ROOT / "Background_Image" / "Retail_Image.png"),
    use_container_width=True,
)


# ─────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<p class="sidebar-brand">📊 AI Dashboard &nbsp;<span>Generator</span></p>',
        unsafe_allow_html=True,
    )

    # ── Group 1: Get Insights & Generate Visualizations ──
    st.markdown('<p class="nav-section">Get Insights &amp; Generate Visualizations</p>', unsafe_allow_html=True)
    for _label in ["⚡ Quick Insights", "📊 Power BI Builder"]:
        _btn_type = "primary" if st.session_state["page"] == _label else "secondary"
        if st.button(_label, key=f"nav_{_label}", use_container_width=True, type=_btn_type):
            st.session_state["page"] = _label
            st.rerun()

    # ── Group 2: Additional Resources ──
    st.markdown('<p class="nav-section">Additional Resources</p>', unsafe_allow_html=True)
    for _label in ["📚 Data Catalog", "🔄 Feedback & Learning", "💡 Example Queries"]:
        _btn_type = "primary" if st.session_state["page"] == _label else "secondary"
        if st.button(_label, key=f"nav_{_label}", use_container_width=True, type=_btn_type):
            st.session_state["page"] = _label
            st.rerun()

    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
    st.markdown('<p class="nav-section">Dataset</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sidebar-info">Olist Brazilian E-Commerce &nbsp;·&nbsp; ~100k orders &nbsp;·&nbsp; 8 tables &nbsp;·&nbsp; 2016–2018 &nbsp;·&nbsp; '
        '<a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce" target="_blank">Kaggle ↗</a></p>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
    st.markdown('<p class="nav-section">Architecture</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sidebar-info">'
        'Agent 1 · Table Recommender &nbsp;|&nbsp; Agent 2 · SQL Generator &nbsp;|&nbsp; '
        'Agent 3 · Viz Recommender &nbsp;|&nbsp; Orchestrator · Coordinates all'
        '</p>',
        unsafe_allow_html=True,
    )

page = st.session_state["page"]


# ─────────────────────────────────────────────
# PAGE: Quick Insights (Path A)
# ─────────────────────────────────────────────

if page == "⚡ Quick Insights":
    st.subheader("Ask a question — get insights instantly")

    prefill = st.session_state.get("prefill_question", "") \
        if st.session_state.get("prefill_tab") == "quick" else ""

    question = st.text_area(
        "What would you like to know about your data?",
        value=prefill,
        height=80,
        placeholder="e.g. What are the top 10 product categories by total revenue?",
        key="qa_input",
    )
    st.session_state["prefill_question"] = ""

    run_btn = st.button("Get Insights", type="primary", key="qa_run")

    if run_btn and question.strip():
        st.session_state["qa_question"] = question.strip()
        st.session_state["qa_result"] = _run_query(question.strip())
        st.session_state["qa_ran"] = True
        st.session_state["qa_approved_tables"] = \
            st.session_state["qa_result"]["table_recommendations"].get("recommended_tables", [])
        st.session_state["qa_sql_override"] = \
            st.session_state["qa_result"]["sql_results"].get("sql_query", "")

    if st.session_state.get("qa_ran") and st.session_state.get("qa_result"):
        result = st.session_state["qa_result"]
        table_recs = result.get("table_recommendations", {})
        sql_res = result.get("sql_results", {})
        viz = result.get("visualization", {})
        df: pd.DataFrame = sql_res.get("results", pd.DataFrame())

        # ── 1. Table Recommendations ──────────────────────────
        with st.expander("1. Table Recommendations", expanded=True):
            st.markdown(f"**Reasoning:** {table_recs.get('reasoning', '')}")
            all_tables = table_recs.get("recommended_tables", [])
            approved = st.multiselect(
                "Tables to use (uncheck to exclude):",
                options=all_tables,
                default=st.session_state["qa_approved_tables"],
                key="qa_table_select",
            )
            st.session_state["qa_approved_tables"] = approved

            joins = table_recs.get("suggested_joins", [])
            if joins:
                st.markdown("**Suggested joins:**")
                for j in joins:
                    st.code(f"{j.get('type','JOIN')} {j.get('left','')} = {j.get('right','')}", language="sql")

            if st.button("Re-run with selected tables", key="qa_rerun"):
                st.session_state["qa_result"] = _run_query(
                    st.session_state["qa_question"], approved
                )
                st.session_state["qa_sql_override"] = \
                    st.session_state["qa_result"]["sql_results"].get("sql_query", "")
                st.rerun()

        # ── 2. Generated SQL ──────────────────────────────────
        with st.expander("2. Generated SQL", expanded=True):
            edited_sql = st.text_area(
                "SQL (edit and click Execute to re-run):",
                value=st.session_state.get("qa_sql_override", sql_res.get("sql_query", "")),
                height=180,
                key="qa_sql_edit",
            )
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Execute SQL", key="qa_exec"):
                    # Run a manual SQL override
                    import sqlite3
                    from config import DATABASE_PATH
                    try:
                        conn = sqlite3.connect(DATABASE_PATH)
                        override_df = pd.read_sql_query(edited_sql, conn)
                        conn.close()
                        # Patch the result
                        new_res = dict(result)
                        new_res["sql_results"] = dict(sql_res)
                        new_res["sql_results"]["results"] = override_df
                        new_res["sql_results"]["row_count"] = len(override_df)
                        new_res["sql_results"]["sql_query"] = edited_sql
                        new_res["sql_results"]["errors"] = []
                        st.session_state["qa_result"] = new_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"SQL execution error: {e}")
            with col2:
                if sql_res.get("sql_explanation"):
                    st.info(f"What this query does: {sql_res['sql_explanation']}")

            st.markdown(
                f"Execution time: **{sql_res.get('execution_time_ms', 0):.0f} ms** · "
                f"Rows returned: **{sql_res.get('row_count', 0):,}**"
            )

        # ── 3. Results & Visualization ────────────────────────
        st.markdown("### 3. Results & Visualization")

        if sql_res.get("errors"):
            for err in sql_res["errors"]:
                st.error(f"Error: {err}")
        elif df.empty:
            st.warning("Query returned no results.")
        else:
            # Chart
            fig = viz.get("figure")
            if fig and isinstance(fig, go.Figure):
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No chart generated.")

            # Data table
            st.markdown(f"**Data** (showing first 100 of {len(df):,} rows)")
            st.dataframe(df.head(100), use_container_width=True)

            # Download buttons
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                st.download_button(
                    "Download Excel",
                    data=export_to_excel_bytes(df),
                    file_name="query_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with dl_col2:
                st.download_button(
                    "Download CSV",
                    data=export_to_csv_bytes(df),
                    file_name="query_results.csv",
                    mime="text/csv",
                )

        # ── 4. Confidence badge ───────────────────────────────
        st.markdown("### 4. Confidence")
        st.markdown(_confidence_badge(result), unsafe_allow_html=True)
        if result.get("errors"):
            for e in result["errors"]:
                st.warning(e)


# ─────────────────────────────────────────────
# PAGE: Power BI Builder (Path B)
# ─────────────────────────────────────────────

elif page == "📊 Power BI Builder":
    st.subheader("Prepare your data and DAX measures for Power BI")

    prefill = st.session_state.get("prefill_question", "") \
        if st.session_state.get("prefill_tab") == "pbi" else ""

    question = st.text_area(
        "Describe the Power BI dashboard you want to create:",
        value=prefill,
        height=80,
        placeholder=(
            "Example: Create a sales dashboard showing monthly revenue trend by category, "
            "top 10 products by revenue, and a regional performance comparison"
        ),
        key="pbi_input",
    )
    st.caption(
        "Tip: Be as specific as possible. Mention the metrics you care about "
        "(revenue, orders, reviews) and any time or category filters."
    )
    st.session_state["prefill_question"] = ""

    run_btn = st.button("Prepare for Power BI", type="primary", key="pbi_run")

    if run_btn and question.strip():
        st.session_state["pbi_question"] = question.strip()
        st.session_state["pbi_result"] = _run_query(question.strip())
        st.session_state["pbi_ran"] = True
        st.session_state["pbi_dax"] = []

    if st.session_state.get("pbi_ran") and st.session_state.get("pbi_result"):
        result = st.session_state["pbi_result"]
        table_recs = result.get("table_recommendations", {})
        sql_res = result.get("sql_results", {})
        viz = result.get("visualization", {})
        df: pd.DataFrame = sql_res.get("results", pd.DataFrame())

        # ── 1. Table Recommendations ──────────────────────────
        with st.expander("1. Table Recommendations", expanded=True):
            st.markdown(f"**Reasoning:** {table_recs.get('reasoning', '')}")
            all_tables = table_recs.get("recommended_tables", [])
            approved_pbi = st.multiselect(
                "Tables to use:",
                options=all_tables,
                default=all_tables,
                key="pbi_table_select",
            )
            if st.button("Re-run with selected tables", key="pbi_rerun"):
                st.session_state["pbi_result"] = _run_query(
                    st.session_state["pbi_question"], approved_pbi
                )
                st.session_state["pbi_dax"] = []
                st.rerun()

        # ── 2. Generated SQL ──────────────────────────────────
        with st.expander("2. Generated SQL", expanded=True):
            st.code(sql_res.get("sql_query", ""), language="sql")
            if sql_res.get("sql_explanation"):
                st.info(sql_res["sql_explanation"])
            st.markdown(
                f"Rows: **{sql_res.get('row_count', 0):,}** · "
                f"Time: **{sql_res.get('execution_time_ms', 0):.0f} ms**"
            )
            if not df.empty:
                st.dataframe(df.head(20), use_container_width=True)

        # ── 3. Power BI Preparation ────────────────────────────
        st.markdown("### 3. Power BI Preparation")

        if sql_res.get("errors"):
            for e in sql_res["errors"]:
                st.error(e)
        else:
            # Generate DAX measures (lazy — only once)
            if not st.session_state["pbi_dax"]:
                with st.spinner("Generating DAX measures..."):
                    st.session_state["pbi_dax"] = generate_dax_measures(
                        viz, st.session_state["pbi_question"]
                    )

            dax_measures = st.session_state["pbi_dax"]

            # DAX measures
            st.markdown("#### DAX Measures")
            if dax_measures:
                for m in dax_measures:
                    st.markdown(f"**{m.get('name', 'Measure')}** — {m.get('explanation', '')}")
                    st.code(m.get("dax", ""), language="dax")
            else:
                st.info("No DAX measures generated for this query.")

            # Power BI visual suggestion
            st.markdown("#### Recommended Power BI Visual")
            pbi_suggestion = viz.get("powerbi_suggestion", "")
            st.info(pbi_suggestion or "See the setup guide for details.")

            # Download buttons
            dl1, dl2 = st.columns(2)
            with dl1:
                if not df.empty:
                    st.download_button(
                        "Download Excel for Power BI",
                        data=export_standardized_excel_bytes(df, viz),
                        file_name="powerbi_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            with dl2:
                guide = generate_powerbi_instructions(viz)
                st.download_button(
                    "Download Power BI Setup Guide",
                    data=guide.encode("utf-8"),
                    file_name="powerbi_setup_guide.txt",
                    mime="text/plain",
                )

            st.info(
                "If you have the Power BI Modeling MCP server configured, "
                "the measures and tables below can be created automatically "
                "in Power BI Desktop via VS Code + GitHub Copilot."
            )

            # ── 4. MCP Command Generator ─────────────────────
            with st.expander("4. MCP Command Generator", expanded=False):
                st.markdown(
                    "Copy these prompts and paste them into **Claude Desktop** "
                    "with the Power BI Modeling MCP server active."
                )
                mcp_text = generate_mcp_commands(
                    viz, dax_measures, df, st.session_state["pbi_question"]
                )
                st.text_area("MCP Prompts", value=mcp_text, height=300, key="mcp_output")
                st.download_button(
                    "Download MCP Prompts",
                    data=mcp_text.encode("utf-8"),
                    file_name="mcp_commands.txt",
                    mime="text/plain",
                )


# ─────────────────────────────────────────────
# PAGE: Data Catalog
# ─────────────────────────────────────────────

elif page == "📚 Data Catalog":
    st.subheader("Data Catalog — All Available Tables")

    registry = _load_json(TABLE_REGISTRY_PATH)
    data_dict = _load_json(DATA_DICTIONARY_PATH)
    relationships = _load_json(RELATIONSHIPS_PATH)

    search = st.text_input(
        "Search by table name, column name, or description:",
        placeholder="e.g. revenue, customer_id, order",
    )

    for table_name, info in registry.items():
        # Filter by search
        if search:
            searchable = (
                table_name + " "
                + info.get("description", "") + " "
                + " ".join(info.get("columns", []))
            ).lower()
            if search.lower() not in searchable:
                continue

        with st.expander(f"**{table_name}** — {info.get('row_count', 0):,} rows"):
            st.markdown(f"**Description:** {info.get('description', 'N/A')}")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Date columns:** {', '.join(info.get('date_columns', [])) or 'none'}")
                st.markdown(f"**Numeric columns:** {', '.join(info.get('numeric_columns', [])) or 'none'}")
            with col_b:
                st.markdown(f"**Primary key candidate:** `{info.get('primary_key_candidate', 'N/A')}`")
                st.markdown(f"**Total columns:** {len(info.get('columns', []))}")

            # Column details
            st.markdown("**Column Descriptions:**")
            col_rows = []
            for col in info.get("columns", []):
                key = f"{table_name}.{col}"
                col_info = data_dict.get(key, {})
                col_rows.append({
                    "Column": col,
                    "Type": col_info.get("data_type", ""),
                    "Unique Values": col_info.get("unique_count", ""),
                    "Nullable": "Yes" if col_info.get("nullable") else "No",
                    "Description": col_info.get("description", ""),
                })
            st.dataframe(pd.DataFrame(col_rows), use_container_width=True, hide_index=True)

            # Sample values
            sample_vals = info.get("sample_values", {})
            if sample_vals:
                st.markdown("**Sample Values (categorical columns):**")
                sv_rows = [{"Column": c, "Sample Values": ", ".join(str(v) for v in vals)}
                           for c, vals in sample_vals.items()]
                st.dataframe(pd.DataFrame(sv_rows), use_container_width=True, hide_index=True)

    # Relationships section
    st.markdown("---")
    st.markdown("### Table Relationships")
    rels = relationships.get("relationships", [])
    if rels:
        rel_rows = [{
            "From Table": r.get("from_table", ""),
            "From Column": r.get("from_column", ""),
            "→": "→",
            "To Table": r.get("to_table", ""),
            "To Column": r.get("to_column", ""),
            "Type": r.get("relationship_type", ""),
            "Confidence": r.get("confidence", ""),
        } for r in rels]
        st.dataframe(pd.DataFrame(rel_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No relationships defined.")


# ─────────────────────────────────────────────
# PAGE: Feedback & Learning
# ─────────────────────────────────────────────

elif page == "🔄 Feedback & Learning":
    st.subheader("Query History & Feedback Loop")

    log = _load_json(USE_CASE_LOG_PATH)
    use_cases = log.get("use_cases", [])

    if not use_cases:
        st.info("No queries logged yet. Run a query in Quick Insights or Power BI Builder to get started.")
    else:
        # ── Metrics dashboard ─────────────────────────────────
        total = len(use_cases)
        successful = sum(1 for uc in use_cases if not uc.get("errors"))
        helpful = sum(1 for uc in use_cases if uc.get("was_helpful") is True)
        modified = sum(
            1 for uc in use_cases
            if uc.get("sql_generated") != uc.get("sql_used") and uc.get("sql_used")
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Queries", total)
        m2.metric("Successful (%)", f"{100 * successful // total}%" if total else "0%")
        m3.metric("Marked Helpful (%)",
                  f"{100 * helpful // total}%" if total else "N/A")
        m4.metric("SQL Modified (%)",
                  f"{100 * modified // total}%" if total else "0%")

        st.markdown("---")

        # ── Per-query feedback ────────────────────────────────
        registry = _load_json(TABLE_REGISTRY_PATH)
        all_table_names = list(registry.keys())

        for idx, uc in enumerate(reversed(use_cases)):
            uc_id = uc.get("id", f"uc_{idx}")
            ts = uc.get("timestamp", "")[:19].replace("T", " ")
            label = f"**{uc_id}** · {ts} · _{uc.get('user_question', '')[:80]}_"

            with st.expander(label):
                st.markdown(f"**Question:** {uc.get('user_question', '')}")
                st.markdown(f"**Tables recommended:** {', '.join(uc.get('tables_recommended', []))}")

                actual_tables = st.multiselect(
                    "Which tables did you actually use?",
                    options=all_table_names,
                    default=[t for t in uc.get("tables_actually_used", []) if t in all_table_names],
                    key=f"fb_tables_{uc_id}",
                )
                final_sql = st.text_area(
                    "Final SQL used (paste here if you modified it):",
                    value=uc.get("sql_used", uc.get("sql_generated", "")),
                    height=100,
                    key=f"fb_sql_{uc_id}",
                )
                helpful_val = st.radio(
                    "Was this helpful?",
                    options=["Not rated", "Yes", "No"],
                    index=0 if uc.get("was_helpful") is None
                          else (1 if uc.get("was_helpful") else 2),
                    horizontal=True,
                    key=f"fb_helpful_{uc_id}",
                )

                if st.button("Save Feedback", key=f"fb_save_{uc_id}"):
                    # Find and update this entry in the log
                    for entry in log["use_cases"]:
                        if entry.get("id") == uc_id:
                            entry["tables_actually_used"] = actual_tables
                            entry["sql_used"] = final_sql
                            entry["was_helpful"] = (
                                None if helpful_val == "Not rated"
                                else helpful_val == "Yes"
                            )
                            break
                    with open(USE_CASE_LOG_PATH, "w", encoding="utf-8") as f:
                        json.dump(log, f, indent=2, ensure_ascii=False)
                    st.success("Feedback saved!")


# ─────────────────────────────────────────────
# PAGE: Example Queries
# ─────────────────────────────────────────────

elif page == "💡 Example Queries":
    st.subheader("Example Queries — Click to Try")

    examples = [
        {
            "question": "What are the top 10 product categories by total revenue?",
            "description": "Revenue ranking across all categories",
        },
        {
            "question": "Show me monthly order trend over time",
            "description": "Time-series line chart of order volume",
        },
        {
            "question": "Which states have the highest average order value?",
            "description": "Geographic breakdown of AOV",
        },
        {
            "question": "What is the average delivery time by seller state?",
            "description": "Logistics performance by seller location",
        },
        {
            "question": "Compare payment methods — what percentage of orders use each type?",
            "description": "Payment mix breakdown (credit card, boleto, etc.)",
        },
        {
            "question": "Which product categories have the highest review scores?",
            "description": "Customer satisfaction by category",
        },
        {
            "question": "Show me revenue by customer state",
            "description": "Geographic revenue distribution",
        },
        {
            "question": "What is the average number of installments by payment type?",
            "description": "Installment behaviour analysis",
        },
        {
            "question": "Which sellers have the most orders and highest revenue?",
            "description": "Top seller performance ranking",
        },
        {
            "question": "What is the order cancellation rate over time?",
            "description": "Cancellation trend by month",
        },
    ]

    for ex in examples:
        with st.container():
            col_text, col_qa, col_pbi = st.columns([5, 1, 1])
            with col_text:
                st.markdown(f"**{ex['question']}**")
                st.caption(ex["description"])
            with col_qa:
                if st.button("Quick Insights", key=f"ex_qa_{ex['question'][:30]}"):
                    st.session_state["prefill_question"] = ex["question"]
                    st.session_state["prefill_tab"] = "quick"
                    st.session_state["page"] = "⚡ Quick Insights"
                    st.rerun()
            with col_pbi:
                if st.button("Power BI", key=f"ex_pbi_{ex['question'][:30]}"):
                    st.session_state["prefill_question"] = ex["question"]
                    st.session_state["prefill_tab"] = "pbi"
                    st.session_state["page"] = "📊 Power BI Builder"
                    st.rerun()
            st.divider()


# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────

st.markdown(
    '<div class="footer">'
    'Powered by Claude AI | RAG + Agentic Architecture | Architected by Annmol Hattikudur'
    '<br><a href="https://github.com/annmolhattikudur" target="_blank" '
    'style="color:#1A6EAF;text-decoration:none;">github.com/annmolhattikudur</a>'
    '</div>',
    unsafe_allow_html=True,
)
