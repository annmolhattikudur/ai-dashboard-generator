"""
Agent 1: Table Recommender
Loads metadata and uses Claude to identify which tables are needed
for a user's natural language question.
"""

import json
from pathlib import Path
from typing import Any

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    TABLE_REGISTRY_PATH,
    DATA_DICTIONARY_PATH,
    RELATIONSHIPS_PATH,
    DOMAIN_KNOWLEDGE_PATH,
    USE_CASE_LOG_PATH,
)


# ─────────────────────────────────────────────
# Metadata loading
# ─────────────────────────────────────────────

def _load_json(path: Path) -> Any:
    """Load a JSON file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_all_metadata() -> dict:
    """Load all metadata files into a single context dict."""
    return {
        "table_registry": _load_json(TABLE_REGISTRY_PATH),
        "data_dictionary": _load_json(DATA_DICTIONARY_PATH),
        "relationships": _load_json(RELATIONSHIPS_PATH),
        "domain_knowledge": _load_json(DOMAIN_KNOWLEDGE_PATH),
        "use_case_log": _load_json(USE_CASE_LOG_PATH),
    }


# ─────────────────────────────────────────────
# Prompt construction
# ─────────────────────────────────────────────

def _find_similar_use_cases(user_question: str, use_cases: list, max_results: int = 3) -> list:
    """
    Keyword-based similarity search over past use cases.
    Returns the most relevant past use cases to include as few-shot examples.
    """
    if not use_cases:
        return []

    q_words = set(user_question.lower().split())
    scored = []
    for uc in use_cases:
        uc_words = set(uc.get("user_question", "").lower().split())
        overlap = len(q_words & uc_words)
        if overlap > 0:
            scored.append((overlap, uc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [uc for _, uc in scored[:max_results]]


def _build_system_prompt(metadata: dict, similar_use_cases: list) -> str:
    """Construct the RAG system prompt with all metadata context."""
    registry = metadata["table_registry"]
    relationships = metadata["relationships"]["relationships"]
    domain = metadata["domain_knowledge"]

    # Table summaries
    table_summaries = []
    for table_name, info in registry.items():
        lines = [
            f"Table: {table_name}",
            f"  Description: {info.get('description', 'N/A')}",
            f"  Rows: {info.get('row_count', 'N/A'):,}",
            f"  Columns: {', '.join(info.get('columns', []))}",
            f"  Date columns: {', '.join(info.get('date_columns', [])) or 'none'}",
            f"  Numeric columns: {', '.join(info.get('numeric_columns', [])) or 'none'}",
            f"  Categorical columns: {', '.join(info.get('categorical_columns', [])) or 'none'}",
        ]
        sample_vals = info.get("sample_values", {})
        if sample_vals:
            lines.append("  Sample values:")
            for col, vals in list(sample_vals.items())[:4]:
                lines.append(f"    {col}: {vals}")
        table_summaries.append("\n".join(lines))

    # Relationships
    rel_lines = [
        f"  {r['from_table']}.{r['from_column']} -> "
        f"{r['to_table']}.{r['to_column']} "
        f"({r['relationship_type']}, {r['confidence']})"
        for r in relationships
    ]

    # Domain knowledge
    dataset_notes = "\n".join(f"  - {n}" for n in domain.get("dataset_notes", []))
    business_rules = "\n".join(f"  - {r}" for r in domain.get("business_rules", []))
    metric_lines = []
    for metric_name, metric_info in domain.get("metrics", {}).items():
        metric_lines.append(
            f"  {metric_name}: {metric_info.get('definition', '')}\n"
            f"    Tables needed: {', '.join(metric_info.get('tables_needed', []))}"
        )

    # Similar past use cases
    use_case_section = ""
    if similar_use_cases:
        uc_lines = [
            f"  Q: {uc.get('user_question', '')}\n"
            f"  Tables used: {', '.join(uc.get('tables_actually_used', []))}"
            for uc in similar_use_cases
        ]
        use_case_section = (
            "\n## SIMILAR PAST USE CASES (for reference)\n"
            + "\n\n".join(uc_lines)
        )

    tables_block = "\n\n".join(table_summaries)
    rels_block = "\n".join(rel_lines) if rel_lines else "No relationships defined"
    metrics_block = "\n".join(metric_lines)

    return f"""You are an expert data analyst and SQL architect for a Brazilian e-commerce platform (Olist marketplace).
Your job is to identify exactly which database tables are needed to answer a user's question.

## AVAILABLE TABLES

{tables_block}

## TABLE RELATIONSHIPS

{rels_block}

## DOMAIN KNOWLEDGE

### Dataset Notes
{dataset_notes}

### Business Metrics
{metrics_block}

### Business Rules
{business_rules}
{use_case_section}

## YOUR TASK

Given the user's question, respond with a JSON object (no markdown, no code fences) with exactly this structure:
{{
  "recommended_tables": ["table1", "table2"],
  "reasoning": "Explanation of why each table is needed...",
  "suggested_joins": [
    {{"left": "table1.column", "right": "table2.column", "type": "INNER JOIN"}}
  ],
  "relevant_columns": {{
    "table1": ["col1", "col2"],
    "table2": ["col3"]
  }},
  "similar_past_use_cases": []
}}

Rules:
- Only recommend tables that actually exist in the list above
- Include ALL tables needed for the complete answer (do not omit join/bridge tables)
- For revenue queries, always include olist_order_payments_dataset
- Product category names in olist_products_dataset are already in English (no translation table needed unless user specifically asks for Portuguese mapping)
- Prefer verified relationships over auto-detected ones for JOIN conditions
- Keep reasoning concise but specific — mention exact columns that will be used
"""


# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def recommend_tables(user_question: str) -> dict:
    """
    Recommend which database tables are needed to answer a user question.

    Args:
        user_question: Natural language question from the user.

    Returns:
        dict with keys: recommended_tables, reasoning, suggested_joins,
                        relevant_columns, similar_past_use_cases
    """
    metadata = _load_all_metadata()
    use_cases = metadata["use_case_log"].get("use_cases", [])
    similar = _find_similar_use_cases(user_question, use_cases)
    system_prompt = _build_system_prompt(metadata, similar)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Question: {user_question}"}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude added them
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.split("\n") if not line.startswith("```")
        ).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "recommended_tables": [],
            "reasoning": raw,
            "suggested_joins": [],
            "relevant_columns": {},
            "similar_past_use_cases": [],
        }

    result.setdefault("recommended_tables", [])
    result.setdefault("reasoning", "")
    result.setdefault("suggested_joins", [])
    result.setdefault("relevant_columns", {})
    result.setdefault("similar_past_use_cases", similar)

    return result


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "What are the top 5 product categories by total revenue?"
    print(json.dumps(recommend_tables(q), indent=2))
