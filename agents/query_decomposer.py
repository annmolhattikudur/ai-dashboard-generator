"""
Query Decomposer Agent
Detects whether a user request asks for one or multiple distinct charts/insights,
and splits multi-chart requests into individual focused questions.
"""

import json

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def decompose_query(user_question: str) -> dict:
    """
    Analyse a user question and decompose it into individual chart requests.

    Args:
        user_question: Raw natural language request from the user.

    Returns:
        {
            "is_multi_chart": bool,
            "charts": [
                {"label": "Chart 1: <title>", "question": "<focused question>"},
                ...
            ]
        }
        For a single-chart request, charts contains exactly one item.
    """
    prompt = f"""You are an analytics query decomposer working with an e-commerce retail dataset.

A user has submitted a dashboard or insight request. Your job is to determine whether
the request is asking for ONE chart/insight or MULTIPLE distinct charts/insights, and
if multiple, split it into individual focused questions.

Rules:
- A single metric or analysis — even with filters like "for 2017" — is ONE chart.
- Multiple clearly different analyses (different metrics, different dimensions, or different
  breakdowns mentioned together) are MULTIPLE charts.
- Connector words like "and", "also", "plus", commas between different analyses,
  or enumerated items ("Chart 1 ... Chart 2 ...") signal multiple charts.
- Each resulting question must be self-contained and specific enough to independently
  generate SQL and a visualization.
- Preserve any time filters (e.g. "for 2017", "in Q1") in each sub-question.
- Keep chart labels short and descriptive (5–8 words max after the "Chart N:" prefix).

User request:
\"\"\"{user_question}\"\"\"

Respond with ONLY a JSON object — no markdown, no code fences, no extra text:
{{
  "is_multi_chart": true,
  "charts": [
    {{
      "label": "Chart 1: <short descriptive title>",
      "question": "<focused, standalone question for this chart>"
    }},
    {{
      "label": "Chart 2: <short descriptive title>",
      "question": "<focused, standalone question for this chart>"
    }}
  ]
}}

If is_multi_chart is false, charts must contain exactly one item with the original question unchanged.
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.split("\n") if not line.startswith("```")
        ).strip()

    try:
        result = json.loads(raw)
        charts = result.get("charts", [])
        if not isinstance(charts, list) or not charts:
            raise ValueError("Empty or invalid charts list")
        # Validate each entry has required keys
        for c in charts:
            if "label" not in c or "question" not in c:
                raise ValueError(f"Chart entry missing keys: {c}")
    except (json.JSONDecodeError, ValueError):
        # Fallback: treat as single chart with original question
        result = {
            "is_multi_chart": False,
            "charts": [{"label": "Chart 1", "question": user_question}],
        }

    return result
