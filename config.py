import os
from pathlib import Path

def _get_secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets (cloud) with fallback to env var (local)."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)

# Project root
BASE_DIR = Path(__file__).parent

# Paths
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATABASE_PATH = BASE_DIR / "database" / "fmcg_warehouse.db"
METADATA_DIR = BASE_DIR / "metadata"

# Metadata file paths
TABLE_REGISTRY_PATH = METADATA_DIR / "table_registry.json"
DATA_DICTIONARY_PATH = METADATA_DIR / "data_dictionary.json"
RELATIONSHIPS_PATH = METADATA_DIR / "relationships.json"
DOMAIN_KNOWLEDGE_PATH = METADATA_DIR / "domain_knowledge.json"
USE_CASE_LOG_PATH = METADATA_DIR / "use_case_log.json"

# Anthropic API
ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# App settings
APP_TITLE = "AI Dashboard Generator"
APP_SUBTITLE = "Natural Language to Insights — No SQL Required"

# Access control — change this to any password you want to share with users
APP_PASSWORD = _get_secret("APP_PASSWORD", "insights2024")

# Agent settings
MAX_SQL_RETRIES = 3
MAX_RESULTS_DISPLAY = 500
