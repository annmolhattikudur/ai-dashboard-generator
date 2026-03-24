import os
from pathlib import Path

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
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# App settings
APP_TITLE = "AI Dashboard Generator"
APP_SUBTITLE = "Natural Language to Insights — No SQL Required"
