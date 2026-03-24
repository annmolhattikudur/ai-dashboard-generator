"""
Agent 3: Visualization Recommender
Analyzes SQL query results and uses Claude to recommend the best
chart type, axis mappings, and generates a ready-to-render Plotly figure.
"""

import json
from typing import Any

import anthropic
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, DOMAIN_KNOWLEDGE_PATH


def _load_json(path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# Result shape analysis
# ─────────────────────────────────────────────

def _describe_dataframe(df: pd.DataFrame) -> dict:
    """Summarise the shape and column types of a DataFrame for the prompt."""
    col_info = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        if "int" in dtype or "float" in dtype:
            col_type = "numeric"
        elif "datetime" in dtype:
            col_type = "datetime"
        else:
            # Check if it looks like a date string
            sample = df[col].dropna().head(3).tolist()
            import re
            if sample and all(re.match(r"\d{4}-\d{2}", str(v)) for v in sample):
                col_type = "date_string"
            else:
                col_type = "categorical"
        col_info[col] = {
            "dtype": dtype,
            "inferred_type": col_type,
            "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
            "unique_count": int(df[col].nunique()),
        }
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": col_info,
    }


# ─────────────────────────────────────────────
# Prompt construction
# ─────────────────────────────────────────────

def _build_prompt(user_question: str, df_description: dict, domain: dict) -> str:
    cols_block = json.dumps(df_description["columns"], indent=2)
    rules = "\n".join(f"  - {r}" for r in domain.get("business_rules", []))

    return f"""You are a data visualization expert. Given a user question and query result shape,
recommend the best Plotly chart and return a JSON configuration.

## USER QUESTION
{user_question}

## QUERY RESULT SHAPE
Rows: {df_description['row_count']}
Columns: {df_description['column_count']}

Column details:
{cols_block}

## BUSINESS RULES (for context)
{rules}

## CHART TYPE GUIDE
- 1 categorical + 1 numeric → bar chart
- date/time + 1 numeric → line chart (trend)
- date/time + multiple numerics → multi-line chart
- 1 categorical with few values (<=8) + proportions → pie chart
- 2 numerics → scatter plot
- many rows of raw data → table
- single KPI value (1x1 result) → kpi_card
- categorical + numeric with breakdown → grouped or stacked bar

## YOUR TASK

Respond with a JSON object (no markdown, no code fences) with exactly this structure:
{{
  "chart_type": "bar",
  "x_axis": "column_name",
  "y_axis": "column_name",
  "color_by": null,
  "title": "Chart title here",
  "orientation": "v",
  "plotly_config": {{
    "xaxis_title": "X Label",
    "yaxis_title": "Y Label",
    "color_discrete_sequence": null
  }},
  "powerbi_suggestion": "Use a clustered bar chart with X on axis, Y as values",
  "reasoning": "One sentence explaining why this chart type was chosen"
}}

Rules:
- chart_type must be one of: bar, line, pie, scatter, heatmap, table, kpi_card
- x_axis and y_axis must be exact column names from the result
- color_by should be null unless a breakdown dimension adds clear value
- orientation: "v" for vertical bars (default), "h" for horizontal (better when labels are long)
- For KPI cards (single number result), set x_axis and y_axis to the single column name
- Choose horizontal bars when categorical labels have more than 15 characters on average
"""


# ─────────────────────────────────────────────
# Plotly figure builder
# ─────────────────────────────────────────────

def _build_plotly_figure(df: pd.DataFrame, viz_config: dict) -> go.Figure:
    """Build a Plotly figure from the viz config and DataFrame."""
    chart_type = viz_config.get("chart_type", "bar")
    x = viz_config.get("x_axis")
    y = viz_config.get("y_axis")
    color = viz_config.get("color_by")
    title = viz_config.get("title", "")
    orientation = viz_config.get("orientation", "v")
    plotly_cfg = viz_config.get("plotly_config", {})

    xaxis_title = plotly_cfg.get("xaxis_title", x)
    yaxis_title = plotly_cfg.get("yaxis_title", y)

    try:
        if chart_type == "bar":
            if orientation == "h" and x and y:
                fig = px.bar(df, x=y, y=x, color=color, orientation="h",
                             title=title, labels={x: xaxis_title, y: yaxis_title})
            else:
                fig = px.bar(df, x=x, y=y, color=color, orientation="v",
                             title=title, labels={x: xaxis_title, y: yaxis_title})

        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, color=color, title=title,
                          labels={x: xaxis_title, y: yaxis_title}, markers=True)

        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=title)

        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, title=title,
                             labels={x: xaxis_title, y: yaxis_title})

        elif chart_type == "heatmap":
            pivot = df.pivot_table(index=x, columns=color, values=y, aggfunc="sum")
            fig = px.imshow(pivot, title=title, aspect="auto")

        elif chart_type == "kpi_card":
            value = df.iloc[0, 0] if not df.empty else "N/A"
            fig = go.Figure(go.Indicator(
                mode="number",
                value=float(value) if str(value).replace('.', '').replace('-', '').isdigit() else None,
                title={"text": title},
                number={"valueformat": ",.2f"},
            ))

        else:  # table fallback
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(df.columns), fill_color="#1f77b4",
                            font=dict(color="white"), align="left"),
                cells=dict(values=[df[c].tolist() for c in df.columns],
                           align="left"),
            )])
            fig.update_layout(title=title)

        # Common layout tweaks
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial, sans-serif", size=12),
            title_font_size=16,
            margin=dict(t=60, b=60, l=60, r=40),
        )
        if chart_type not in ("pie", "kpi_card", "table", "heatmap"):
            fig.update_layout(
                xaxis_title=xaxis_title,
                yaxis_title=yaxis_title,
            )

    except Exception as e:
        # Fallback: render as table
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df.columns), fill_color="#d62728",
                        font=dict(color="white"), align="left"),
            cells=dict(values=[df[c].tolist() for c in df.columns], align="left"),
        )])
        fig.update_layout(title=f"{title} (table fallback — chart error: {e})")

    return fig


# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def recommend_visualization(user_question: str, query_results: dict) -> dict:
    """
    Recommend the best visualization for a set of SQL query results.

    Args:
        user_question: Original natural language question from the user.
        query_results: Output from generate_and_run_sql().

    Returns:
        dict with keys: chart_type, x_axis, y_axis, color_by, title,
                        orientation, plotly_config, powerbi_suggestion,
                        reasoning, figure (Plotly Figure object)
    """
    df: pd.DataFrame = query_results.get("results", pd.DataFrame())
    domain = _load_json(DOMAIN_KNOWLEDGE_PATH)

    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No data to display")
        return {
            "chart_type": "table",
            "x_axis": None,
            "y_axis": None,
            "color_by": None,
            "title": "No data returned",
            "orientation": "v",
            "plotly_config": {},
            "powerbi_suggestion": "No data to visualize.",
            "reasoning": "Query returned no rows.",
            "figure": empty_fig,
        }

    df_description = _describe_dataframe(df)
    prompt = _build_prompt(user_question, df_description, domain)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.split("\n") if not line.startswith("```")
        ).strip()

    try:
        viz_config = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback to a sensible default
        cols = list(df.columns)
        viz_config = {
            "chart_type": "table",
            "x_axis": cols[0] if cols else None,
            "y_axis": cols[1] if len(cols) > 1 else cols[0] if cols else None,
            "color_by": None,
            "title": user_question[:80],
            "orientation": "v",
            "plotly_config": {},
            "powerbi_suggestion": "Use a table visual.",
            "reasoning": "Could not parse visualization recommendation; defaulting to table.",
        }

    # Build the actual Plotly figure
    figure = _build_plotly_figure(df, viz_config)
    viz_config["figure"] = figure

    return viz_config


if __name__ == "__main__":
    import sys
    from agents.table_recommender import recommend_tables
    from agents.sql_generator import generate_and_run_sql

    q = sys.argv[1] if len(sys.argv) > 1 else "What are the top 5 product categories by total revenue?"
    recs = recommend_tables(q)
    sql_results = generate_and_run_sql(q, recs)
    viz = recommend_visualization(q, sql_results)
    print("Chart type:", viz["chart_type"])
    print("Title:", viz["title"])
    print("X:", viz["x_axis"], "| Y:", viz["y_axis"])
    print("Reasoning:", viz["reasoning"])
    print("Power BI:", viz["powerbi_suggestion"])
