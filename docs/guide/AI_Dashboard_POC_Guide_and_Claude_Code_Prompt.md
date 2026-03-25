# AI-Powered Dashboard Generator — POC Guide & Claude Code Prompt

## For: L'Oréal Data Product Manager Interview Preparation

---

## SECTION A: Claude Code Prompt (Copy-Paste Ready)

Below is the complete prompt you will give to Claude Code. Copy everything between the `---START---` and `---END---` markers.

---START---

```
# PROJECT: AI-Powered Natural Language Dashboard Generator (POC)

## CONTEXT
I am building a proof-of-concept for an AI-powered system where users can create 
insight-rich dashboards and find the right data tables using natural language — no 
SQL or DAX knowledge required. This is for an E-Commerce / FMCG retail context.

The dataset is the Olist Brazilian E-Commerce dataset with 8 tables:
- olist_customers_dataset (customer info, location)
- olist_orders_dataset (order status, timestamps)
- olist_order_items_dataset (items per order, price, freight)
- olist_order_payments_dataset (payment type, installments, value)
- olist_order_reviews_dataset (review scores, comments)
- olist_products_dataset (product categories in English, dimensions, weight)
- olist_sellers_dataset (seller info, location)
- olist_geolocation_dataset (lat/lng by zip code prefix)

Note: The translation table is NOT included. Product category names in 
olist_products_dataset are already in English.

The system has TWO output paths:
- Path A (Quick Insights): Instant Plotly visualizations in Streamlit for analysts
- Path B (Power BI Dashboard): Prepares data and generates DAX measures for Power BI,
  with export to Excel and detailed Power BI setup instructions

## GITHUB SETUP

Before building anything, initialize the project as a Git repository:

1. Run: git init
2. Create a .gitignore file that ignores:
   - database/*.db
   - __pycache__/
   - *.pyc
   - .env
   - venv/
   - .streamlit/secrets.toml
   - data/raw/*.csv  (large CSV files should not be in git)
3. Make an initial commit: "Initial project setup"
4. I will manually add the remote origin after project creation

Throughout the build, make meaningful git commits after each major step with 
descriptive messages like:
- "feat: database setup and CSV loader"
- "feat: auto-generate metadata and data dictionary"
- "feat: table recommender agent with RAG context"
- "feat: SQL generator agent with validation and self-correction"
- "feat: visualization recommender agent"
- "feat: orchestrator connecting all agents"
- "feat: Power BI export handler with DAX generation"
- "feat: Streamlit frontend with dual-tab architecture"
- "docs: comprehensive README with architecture diagrams"

## WHAT I NEED YOU TO BUILD

A full working POC with the following components. Build them in the exact order listed.

---

### STEP 1: Project Setup

Create a project directory called `ai-dashboard-generator/` with this structure:

ai-dashboard-generator/
├── data/
│   └── raw/                    # I will place my Kaggle CSV files here
├── docs/
│   ├── architecture.md         # Detailed architecture explanation
│   └── enterprise-roadmap.md   # How this scales to enterprise (GCP/BigQuery)
├── metadata/
│   ├── table_registry.json     # Master list of all tables
│   ├── data_dictionary.json    # Column-level descriptions 
│   ├── relationships.json      # How tables join together
│   ├── domain_knowledge.json   # E-commerce metric definitions & SQL patterns
│   └── use_case_log.json       # Feedback loop storage
├── database/
│   └── fmcg_warehouse.db       # SQLite database
├── agents/
│   ├── query_decomposer.py     # Agent 1: detects single vs. multi-chart (added Phase 5)
│   ├── table_recommender.py    # Agent 2: finds right tables
│   ├── sql_generator.py        # Agent 3: writes & runs SQL
│   ├── viz_recommender.py      # Agent 4: suggests visualizations
│   └── orchestrator.py         # Agent 5: coordinates all agents
├── app/
│   └── streamlit_app.py        # Frontend with dual-tab architecture
├── powerbi/
│   └── export_handler.py       # Exports data + DAX for Power BI
├── config.py                   # API keys, settings
├── setup_database.py           # Loads CSVs into SQLite
├── generate_metadata.py        # Auto-generates metadata from data
├── requirements.txt
├── .gitignore
└── README.md

Initialize a Python virtual environment and install dependencies:
- streamlit
- anthropic
- pandas
- plotly
- openpyxl

---

### DATASET CONTEXT (The Olist Brazilian E-Commerce Dataset)

The dataset is the Brazilian E-Commerce Public Dataset by Olist from Kaggle. 
It contains ~100k orders from 2016-2018 made at multiple marketplaces in Brazil.
The CSV files and their contents are:

1. olist_orders_dataset.csv (CORE TABLE)
   - order_id, customer_id, order_status, order_purchase_timestamp,
     order_approved_at, order_delivered_carrier_date, 
     order_delivered_customer_date, order_estimated_delivery_date
   - This is the central table. From each order you can find all other info.

2. olist_order_items_dataset.csv
   - order_id, order_item_id, product_id, seller_id, 
     shipping_limit_date, price, freight_value
   - Each row is one item in an order. An order can have multiple items.
   - Total order value = SUM(price) + SUM(freight_value) for that order_id

3. olist_products_dataset.csv
   - product_id, product_category_name, product_name_lenght,
     product_description_lenght, product_photos_qty, product_weight_g,
     product_length_cm, product_height_cm, product_width_cm
   - Note: category names are in Portuguese

4. product_category_name_translation.csv
   - product_category_name, product_category_name_english
   - Maps Portuguese category names to English

5. olist_customers_dataset.csv
   - customer_id, customer_unique_id, customer_zip_code_prefix,
     customer_city, customer_state
   - customer_id is per-order, customer_unique_id is the actual unique customer

6. olist_sellers_dataset.csv
   - seller_id, seller_zip_code_prefix, seller_city, seller_state

7. olist_order_payments_dataset.csv
   - order_id, payment_sequential, payment_type, payment_installments,
     payment_value
   - An order can have multiple payment methods

8. olist_order_reviews_dataset.csv
   - review_id, order_id, review_score (1-5), review_comment_title,
     review_comment_message, review_creation_date, review_answer_timestamp

9. olist_geolocation_dataset.csv
   - geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
     geolocation_city, geolocation_state

KEY RELATIONSHIPS:
- orders.customer_id → customers.customer_id
- order_items.order_id → orders.order_id
- order_items.product_id → products.product_id
- order_items.seller_id → sellers.seller_id
- order_payments.order_id → orders.order_id
- order_reviews.order_id → orders.order_id
- products.product_category_name → translation.product_category_name
- customers.customer_zip_code_prefix → geolocation.geolocation_zip_code_prefix

BUSINESS CONTEXT:
- Olist is a Brazilian marketplace connecting small businesses to customers
- Revenue = SUM(payment_value) from payments table, or SUM(price) from order_items
- Product categories are in Portuguese — always join with translation table
- customer_unique_id is needed for unique customer counts (not customer_id)
- Average review score across all products is ~4.0
- Top categories by order volume: bed_bath_table, health_beauty, sports_leisure
- Computers category has highest average order value
- Order cancellation rate is ~0.6%
- Data spans Sep 2016 to Oct 2018, most analysis uses Jan 2017 to Aug 2018

Use this context when generating metadata descriptions. Pre-fill the description 
fields in table_registry.json and data_dictionary.json using this information 
instead of leaving them blank.

---

### STEP 2: Database Setup Script (setup_database.py)

Write a script that:
1. Reads ALL CSV files from `data/raw/`
2. Cleans column names (lowercase, replace spaces with underscores)
3. Loads each CSV into SQLite as a separate table in `database/fmcg_warehouse.db`
4. Prints a summary: table name, row count, column count for each table loaded
5. Creates an index on any column that looks like an ID or key column

The script should handle:
- Different CSV encodings (utf-8, latin-1)
- Mixed data types gracefully
- Duplicate column names

---

### STEP 3: Metadata Generation Script (generate_metadata.py)

This is CRITICAL for the RAG architecture. Write a script that auto-generates:

#### 3a. table_registry.json
For each table in SQLite, generate:
```json
{
  "table_name": "sales_transactions",
  "description": "",  // Leave blank for me to fill in manually
  "row_count": 50000,
  "columns": ["col1", "col2", ...],
  "primary_key_candidate": "transaction_id",
  "date_columns": ["order_date", "ship_date"],
  "numeric_columns": ["quantity", "revenue", "profit"],
  "categorical_columns": ["category", "region", "segment"],
  "sample_values": {
    "category": ["Beverages", "Snacks", "Dairy"],
    "region": ["North", "South", "East", "West"]
  }
}
```

#### 3b. data_dictionary.json
For each column in each table:
```json
{
  "table_name.column_name": {
    "data_type": "TEXT",
    "nullable": true,
    "unique_count": 145,
    "sample_values": ["value1", "value2", "value3"],
    "min_value": null,
    "max_value": null,
    "description": ""  // Leave blank for manual enrichment
  }
}
```

#### 3c. relationships.json
Attempt to auto-detect relationships by finding columns with matching names across 
tables (e.g., product_id in both sales and products tables):
```json
{
  "relationships": [
    {
      "from_table": "sales",
      "from_column": "product_id",
      "to_table": "products",
      "to_column": "product_id",
      "relationship_type": "many-to-one",
      "confidence": "auto-detected"
    }
  ]
}
```

#### 3d. use_case_log.json
Initialize as an empty array. This stores feedback:
```json
{
  "use_cases": []
}
```
Each entry will eventually look like:
```json
{
  "id": "uc_001",
  "user_question": "What are the top 10 products by revenue in each region?",
  "tables_recommended": ["sales", "products", "regions"],
  "tables_actually_used": ["sales", "products"],
  "sql_generated": "SELECT ...",
  "sql_used": "SELECT ...",
  "was_helpful": true,
  "timestamp": "2025-03-22T10:00:00"
}
```

After generating metadata, USE THE DATASET CONTEXT section above to pre-fill 
description fields. Do NOT leave them blank — you have enough information 
about the Olist dataset to write meaningful descriptions for every table and 
most columns.

#### 3e. domain_knowledge.json
Create a domain knowledge file that teaches the LLM e-commerce business concepts
specific to the Olist Brazilian E-Commerce dataset. This file is loaded into 
every agent's prompt as additional RAG context.

```json
{
  "domain": "Brazilian E-Commerce (Olist Marketplace)",
  "dataset_notes": [
    "Product categories are in Portuguese — ALWAYS join with product_category_name_translation table",
    "Use customer_unique_id for unique customer counts, NOT customer_id (customer_id is per-order)",
    "Revenue = SUM(payment_value) from payments table OR SUM(price + freight_value) from order_items",
    "Data spans Sep 2016 to Oct 2018. Best analysis window: Jan 2017 to Aug 2018",
    "An order can have multiple items (order_items) and multiple payments (order_payments)",
    "Total order value = SUM(price) + SUM(freight_value) for all items in that order"
  ],
  "metrics": {
    "total_revenue": {
      "definition": "Total monetary value of all completed orders",
      "formula": "SUM(payment_value) from order_payments WHERE order_status = 'delivered'",
      "tables_needed": ["olist_orders_dataset", "olist_order_payments_dataset"],
      "sql_pattern": "SELECT SUM(p.payment_value) as total_revenue FROM olist_order_payments_dataset p JOIN olist_orders_dataset o ON p.order_id = o.order_id WHERE o.order_status = 'delivered'"
    },
    "revenue_trend": {
      "definition": "Revenue aggregated over time periods to show growth or decline",
      "formula": "SUM(payment_value) grouped by month/quarter/year",
      "tables_needed": ["olist_orders_dataset", "olist_order_payments_dataset"],
      "sql_pattern": "SELECT strftime('%Y-%m', o.order_purchase_timestamp) as month, SUM(p.payment_value) as revenue FROM olist_order_payments_dataset p JOIN olist_orders_dataset o ON p.order_id = o.order_id GROUP BY month ORDER BY month"
    },
    "average_order_value": {
      "definition": "Average revenue per order",
      "formula": "Total Revenue / Number of Unique Orders",
      "tables_needed": ["olist_order_payments_dataset"],
      "sql_pattern": "SELECT ROUND(SUM(payment_value) / COUNT(DISTINCT order_id), 2) as aov FROM olist_order_payments_dataset"
    },
    "assortment": {
      "definition": "Number of unique products available in a category or overall",
      "formula": "COUNT(DISTINCT product_id)",
      "tables_needed": ["olist_products_dataset", "product_category_name_translation"],
      "sql_pattern": "SELECT t.product_category_name_english as category, COUNT(DISTINCT p.product_id) as assortment FROM olist_products_dataset p JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name GROUP BY category ORDER BY assortment DESC"
    },
    "customer_satisfaction": {
      "definition": "Average review score given by customers (1-5 scale)",
      "formula": "AVG(review_score)",
      "tables_needed": ["olist_order_reviews_dataset"],
      "sql_pattern": "SELECT ROUND(AVG(review_score), 2) as avg_satisfaction FROM olist_order_reviews_dataset",
      "known_insight": "Average across all products is approximately 4.0"
    },
    "order_cancellation_rate": {
      "definition": "Percentage of orders that were cancelled",
      "formula": "(COUNT orders WHERE status='canceled' / COUNT all orders) * 100",
      "tables_needed": ["olist_orders_dataset"],
      "sql_pattern": "SELECT ROUND(100.0 * SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) / COUNT(*), 2) as cancellation_rate FROM olist_orders_dataset",
      "known_insight": "Cancellation rate is approximately 0.6%"
    },
    "delivery_performance": {
      "definition": "How actual delivery compares to estimated delivery date",
      "formula": "julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)",
      "tables_needed": ["olist_orders_dataset"],
      "sql_pattern": "SELECT ROUND(AVG(julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)), 1) as avg_days_diff FROM olist_orders_dataset WHERE order_delivered_customer_date IS NOT NULL"
    },
    "sales_growth": {
      "definition": "Percentage change in revenue between two consecutive periods",
      "formula": "((Current Period Revenue - Previous Period Revenue) / Previous Period Revenue) * 100",
      "tables_needed": ["olist_orders_dataset", "olist_order_payments_dataset"]
    },
    "top_categories": {
      "definition": "Product categories ranked by order volume or revenue",
      "tables_needed": ["olist_order_items_dataset", "olist_products_dataset", "product_category_name_translation"],
      "known_insight": "Top categories by volume: bed_bath_table, health_beauty, sports_leisure, furniture_decor, computers_accessories"
    },
    "seller_performance": {
      "definition": "Revenue, order count, and review scores per seller",
      "tables_needed": ["olist_order_items_dataset", "olist_sellers_dataset", "olist_order_reviews_dataset", "olist_orders_dataset"]
    },
    "payment_analysis": {
      "definition": "Breakdown of orders by payment method and installment patterns",
      "tables_needed": ["olist_order_payments_dataset"],
      "known_insight": "Credit card is the most common payment method with highest AOV"
    },
    "customer_geography": {
      "definition": "Distribution of customers and orders by state/city",
      "tables_needed": ["olist_customers_dataset", "olist_orders_dataset"],
      "known_insight": "Sao Paulo (SP) has the highest customer density"
    },
    "freight_analysis": {
      "definition": "Shipping cost analysis by product weight, category, or distance",
      "formula": "AVG(freight_value) or SUM(freight_value) / SUM(price) for freight-to-price ratio",
      "tables_needed": ["olist_order_items_dataset", "olist_products_dataset"]
    }
  },
  "common_dimensions": {
    "time": ["daily", "weekly", "monthly", "quarterly", "yearly", "YoY", "MoM"],
    "product": ["category (English)", "product_id"],
    "geography": ["customer_state", "customer_city", "seller_state", "seller_city"],
    "customer": ["customer_unique_id", "customer_state"],
    "payment": ["payment_type", "payment_installments"],
    "order_status": ["delivered", "shipped", "canceled", "processing"]
  },
  "business_rules": [
    "ALWAYS join products with product_category_name_translation to get English category names",
    "Use customer_unique_id for counting unique customers, NOT customer_id",
    "When calculating revenue, prefer SUM(payment_value) from payments table for accuracy",
    "Filter order_status = 'delivered' for completed order analysis unless user wants all statuses",
    "When user says 'top products', default to top 10 by revenue unless specified otherwise",
    "When user says 'trend', use a line chart with time on X-axis",
    "When user says 'compare', use a grouped bar chart",
    "When user says 'breakdown' or 'distribution', use stacked bar or pie chart",
    "For growth calculations, compare same period (e.g. Jan 2018 vs Jan 2017 for YoY)",
    "Be aware that Sep-Oct 2018 data is incomplete — warn user if their query includes this period"
  ]
}
```

This file is critical — it teaches the LLM HOW to calculate business metrics,
not just WHERE the data lives. When a user asks "show me the assortment by 
category," Agent 1 knows which tables to use (from metadata) AND Agent 2 knows 
that assortment means COUNT(DISTINCT product_id) (from domain knowledge).

After auto-generating the initial file, prompt me to add more domain-specific 
metrics relevant to my dataset.

---

### STEP 4: Agent — Table Recommender (agents/table_recommender.py)

Build a function `recommend_tables(user_question: str) -> dict` that:

1. Loads all metadata files (table_registry, data_dictionary, relationships, 
   use_case_log) AND the domain_knowledge.json file
2. Constructs a SYSTEM PROMPT for Claude that includes:
   - All table metadata as context (this is the RAG part)
   - The domain knowledge with metric definitions and SQL patterns
   - The relationships between tables
   - Any previous use cases from the feedback log that are similar
   - Instructions to recommend which tables are needed, explain WHY each table 
     is needed, and suggest JOIN conditions
3. Sends the user's question + system prompt to Claude API (claude-sonnet-4-20250514)
4. Returns a structured response:
```python
{
    "recommended_tables": ["table1", "table2"],
    "reasoning": "You need table1 for revenue data and table2 for product names...",
    "suggested_joins": [
        {"left": "table1.product_id", "right": "table2.product_id", "type": "INNER JOIN"}
    ],
    "relevant_columns": {
        "table1": ["revenue", "quantity", "order_date"],
        "table2": ["product_name", "category"]
    },
    "similar_past_use_cases": []  // From use_case_log if any match
}
```

Use the Anthropic Python SDK. The API key should come from an environment variable 
ANTHROPIC_API_KEY.

---

### STEP 5: Agent — SQL Generator (agents/sql_generator.py)

Build a function `generate_and_run_sql(user_question: str, table_recommendations: dict) -> dict` that:

1. Takes the user's natural language question and the table recommender's output
2. Constructs a system prompt with:
   - The recommended tables' full metadata (column types, sample values)
   - The join conditions
   - Instructions to write SQLite-compatible SQL
   - Instructions to include comments in the SQL explaining each part
3. Sends to Claude API to generate SQL
4. VALIDATES the SQL: 
   - Parse it to check for syntax errors
   - Verify all referenced tables and columns exist in the database
   - If invalid, send the error back to Claude for self-correction (max 3 retries)
5. EXECUTES the SQL against SQLite
6. Returns:
```python
{
    "sql_query": "SELECT ...",
    "sql_explanation": "This query joins sales with products to...",
    "results": pandas.DataFrame,
    "row_count": 150,
    "column_names": ["product_name", "total_revenue", "region"],
    "execution_time_ms": 45,
    "errors": []  # Any errors encountered during generation/execution
}
```

IMPORTANT: Add safety checks — the generated SQL should NEVER contain DROP, DELETE, 
UPDATE, INSERT, ALTER, or CREATE statements. Read-only queries only.

---

### STEP 6: Agent — Visualization Recommender (agents/viz_recommender.py)

Build a function `recommend_visualization(user_question: str, query_results: dict) -> dict` that:

1. Takes the user question and the SQL results
2. Analyzes the result shape (number of rows, columns, data types)
3. Sends to Claude API with instructions to recommend:
   - The best chart type (bar, line, pie, scatter, heatmap, table, KPI card)
   - Which columns go on which axis
   - Any grouping, coloring, or filtering suggestions
   - A title for the chart
4. Returns:
```python
{
    "chart_type": "bar",
    "x_axis": "product_name",
    "y_axis": "total_revenue",
    "color_by": "region",
    "title": "Top Products by Revenue Across Regions",
    "plotly_config": { ... },  # Ready-to-use Plotly configuration
    "powerbi_suggestion": "Use a clustered bar chart with product_name on axis, 
                           total_revenue as values, region as legend"
}
```

Also generate the actual Plotly figure code so Streamlit can render it directly.

---

### STEP 7: Orchestrator (agents/orchestrator.py)

Build the master orchestrator function `process_query(user_question: str) -> dict` that:

1. Calls table_recommender → gets table recommendations
2. Shows recommendations to user (via return value) and allows them to 
   accept/modify before proceeding
3. Calls sql_generator → generates and runs SQL
4. Calls viz_recommender → gets visualization recommendation
5. Returns everything packaged together:
```python
{
    "user_question": "...",
    "table_recommendations": { ... },
    "sql_results": { ... },
    "visualization": { ... },
    "timestamp": "..."
}
```

Include error handling at each step with clear error messages.

---

### STEP 8: Power BI Export Handler (powerbi/export_handler.py)

Build functions to:
1. `export_to_excel(results_df, filepath)` — exports query results to .xlsx with 
   formatting (headers bold, auto-column-width)
2. `export_to_csv(results_df, filepath)` — exports to CSV
3. `generate_powerbi_instructions(viz_config)` — generates a text file with 
   step-by-step Power BI instructions:
   - Which Power BI visual to use
   - How to configure the fields
   - Any DAX measures to create
   - Formatting suggestions
4. `export_standardized_excel(results_df, viz_config, filepath)` — exports results 
   into a standardized Excel format with two sheets:
   - Sheet "Data": the query results with clean headers
   - Sheet "ChartConfig": a configuration sheet with rows like:
     chart_type | bar
     x_axis     | category
     y_axis     | total_revenue
     color_by   | region
     title      | Top Products by Revenue
   This standardized format lets a pre-built Power BI template auto-connect 
   to any exported file.
5. `generate_dax_measures(viz_config, user_question)` — sends the visualization 
   config and user question to Claude API and asks it to generate any useful 
   DAX measures (e.g., YoY growth, running totals, % of total). Returns a list 
   of DAX measure definitions with explanations that the user can paste into 
   Power BI.

---

### STEP 9: Streamlit Frontend (app/streamlit_app.py)

Build a Streamlit app with a DUAL-TAB main interface and sidebar navigation.
The app should use st.session_state throughout to maintain conversation state.

#### MAIN INTERFACE — Two Primary Tabs

Use st.tabs() to create two main tabs at the top of the page:

**Tab 1: "⚡ Quick Insights" (Path A)**
This is for instant exploration — user asks a question, gets a chart in seconds.

- A large text input: "What would you like to know about your data?"
- A "Get Insights" button
- After submission, show in sequence:
  1. **Table Recommendations Panel** (expandable):
     - Which tables were selected and why
     - A checkbox list where users can accept/reject tables
     - A "Proceed with selected tables" button
  2. **Generated SQL Panel** (expandable, code-formatted):
     - The SQL query with syntax highlighting
     - An "Edit SQL" text area for manual modifications
     - An "Execute" button
  3. **Results & Visualization Panel**:
     - The data table (first 100 rows)
     - The Plotly interactive chart (rendered directly)
     - Download buttons: "Export to Excel", "Export to CSV"
  4. **Confidence Badge**:
     - GREEN for HIGH confidence
     - YELLOW for MEDIUM ("Review recommended")
     - RED for LOW ("Results may not match your question")

**Tab 2: "📊 Build Power BI Dashboard" (Path B)**
This is for creating governed Power BI reports.

- A large text input: "Describe the Power BI dashboard you want to create"
- Helpful hint text below: "Example: Create a sales dashboard showing monthly 
  revenue trend by category, top 10 products by profit margin, and a regional 
  performance comparison"
- A "Prepare for Power BI" button
- After submission, show in sequence:
  1. **Table Recommendations Panel** (same as Path A)
  2. **Generated SQL Panel** (same as Path A)
  3. **Power BI Preparation Panel**:
     - Generated DAX measures with explanations (copyable code blocks)
     - Recommended Power BI visuals with field configuration
     - "Download Excel for Power BI" button (standardized format)
     - "Download Power BI Setup Guide" button (text file with step-by-step 
       instructions for building the report in Power BI Desktop)
     - A note: "If you have the Power BI Modeling MCP server configured, 
       these measures and tables can be created automatically in Power BI 
       Desktop via VS Code + GitHub Copilot"
  4. **MCP Command Generator Panel** (expandable):
     - Auto-generates the natural language prompts that a user would paste 
       into VS Code / GitHub Copilot chat to trigger the Power BI Modeling 
       MCP server. For example:
       "Connect to 'Sales Dashboard' in Power BI Desktop. Create a table 
        called 'MonthlySales' with columns: month (date), category (text), 
        revenue (decimal). Add a measure 'Total Revenue' = SUM(MonthlySales[revenue]). 
        Add a measure 'MoM Growth' = ..."
     - User can copy these prompts and paste them into VS Code

#### SIDEBAR NAVIGATION — Additional Pages

**Page: "📚 Data Catalog"**
- Shows all available tables with descriptions
- For each table: column list, data types, sample values
- Table relationships visualization (use a simple Plotly network graph or text)
- A search bar to find tables by column name or description

**Page: "🔄 Feedback & Learning"**
- Shows history of all queries
- For each query, editable fields:
  - "Which tables did you actually use?" (multiselect)
  - "Did you modify the SQL? Paste your final SQL here" (text area)
  - "Was this helpful?" (thumbs up/down)
  - "Save Feedback" button that writes to use_case_log.json
- Accuracy metrics dashboard:
  - Total queries processed
  - % queries executed successfully
  - % queries marked helpful
  - % queries where SQL was modified

**Page: "💡 Example Queries"**
- Pre-built example questions users can click to try:
  - "What are the top 10 product categories by total revenue?"
  - "Show me monthly order trend over time"
  - "Which states have the highest average order value?"
  - "What is the average delivery time by seller state?"
  - "Compare payment methods — what percentage of orders use each type?"
  - "Which product categories have the highest review scores?"
  - "Show me revenue by customer state on a map-like breakdown"
  - "What is the average number of installments by payment type?"
  - "Which sellers have the most orders and highest revenue?"
  - "What is the order cancellation rate over time?"
- Each example should have a "Try in Quick Insights" button and a 
  "Try in Power BI Builder" button

#### Styling:
- Use a clean, professional theme
- Add a sidebar with a modern e-commerce color scheme (deep blue/teal) 
  for demo aesthetics
- Add a header: "AI Dashboard Generator — Proof of Concept"
- Add a footer: "Powered by Claude AI | RAG + Agentic Architecture"

---

### STEP 10: Configuration (config.py)

```python
import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-sonnet-4-20250514"
DATABASE_PATH = "database/fmcg_warehouse.db"
METADATA_DIR = "metadata/"
MAX_SQL_RETRIES = 3
MAX_RESULTS_DISPLAY = 500
```

---

### STEP 11: README.md (GitHub-Ready — This Must Be Impressive)

Write a comprehensive, professional README.md that would impress someone visiting 
the GitHub repository. Include:

1. **Project Title & Badges**: 
   - "# 🤖 AI Dashboard Generator"
   - Subtitle: "Natural language to insights — powered by RAG + Agentic AI"
   - Add badge-style text: Python 3.11 | Claude API | Streamlit | Power BI MCP

2. **What This Does** (3-4 sentences, non-technical):
   - Users ask questions in plain English
   - AI finds the right data, writes queries, generates visualizations
   - Two paths: instant Plotly charts OR governed Power BI dashboards
   - Zero SQL/DAX knowledge required

3. **Architecture Diagram** (ASCII art):
   - Show the full flow: User → Streamlit → Agents → SQLite → Path A/Path B
   - Label each component clearly

4. **AI Architecture Explanation**:
   - Explain RAG: metadata retrieval + prompt augmentation + generation
   - Explain Agentic: Table Recommender → SQL Generator → Viz Recommender
   - Explain Feedback Loop: user feedback → growing knowledge base → better recs
   - Keep it accessible for non-AI-engineers

5. **Screenshots** (placeholder section):
   - Add a section "## Screenshots" with placeholder text:
     "Screenshots will be added after initial deployment"
   - Create placeholder image references for: main interface, quick insights tab,
     power BI builder tab, data catalog page

6. **Quick Start** (step-by-step):
   - Prerequisites (Python 3.11, Anthropic API key)
   - Clone repo
   - Install dependencies
   - Add CSV data
   - Run setup_database.py
   - Run generate_metadata.py
   - Enrich metadata descriptions
   - Run streamlit app

7. **Power BI MCP Integration** (separate section):
   - Explain what the Power BI Modeling MCP server is
   - How to set it up (VS Code + GitHub Copilot)
   - How Path B generates MCP-ready prompts
   - Current limitations (cannot create visuals, only semantic model)

8. **Project Structure**: show the full directory tree with descriptions

9. **Enterprise Roadmap** section:
   - BigQuery instead of SQLite
   - Vector database for metadata at scale
   - Power BI Remote MCP for querying existing models
   - Authentication & RBAC
   - Cost controls & audit logging

10. **Technologies Used**: 
    - Python, Streamlit, Claude API (Anthropic), SQLite, Plotly, 
      Power BI Modeling MCP Server, Pandas

11. **License**: MIT

Also create these additional docs:

**docs/architecture.md**: 
- Detailed architecture with diagrams
- RAG explanation with code-level details
- Agent interaction patterns
- Data flow diagrams

**docs/enterprise-roadmap.md**:
- Full enterprise mapping table (POC → GCP)
- Security considerations
- Cost estimation framework
- MCP integration roadmap (BigQuery MCP + Power BI MCP)

---

### STEP 12: Final Git Commit

After everything is built:
1. Stage all files
2. Commit with message: "feat: complete POC - AI Dashboard Generator with 
   dual-path architecture (Streamlit + Power BI MCP)"
3. Print instructions for the user to push to GitHub:
   - git remote add origin https://github.com/YOUR_USERNAME/ai-dashboard-generator.git
   - git branch -M main
   - git push -u origin main

---

## IMPORTANT TECHNICAL REQUIREMENTS

1. All Claude API calls must use the Anthropic Python SDK with claude-sonnet-4-20250514
2. All API calls must have proper error handling and timeout settings
3. The system prompt for each agent should be detailed and include the metadata 
   as context (this IS the RAG pattern — retrieval of metadata, augmented into 
   the prompt, for generation)
4. SQL queries must be read-only (SELECT only) with safety validation
5. The feedback loop must persist to JSON and be loaded on next startup
6. Use st.session_state in Streamlit to maintain conversation state
7. Add logging throughout for debugging

## CODING STANDARDS
- Type hints on all functions
- Docstrings on all functions
- Clear variable names
- Comments explaining the AI/RAG logic at key points
```

---END---

### Supplementary Prompt — Add After Main Build

Give this to Claude Code after the main POC is built and working:

```
Add a validation and accuracy layer to the POC:

1. In sql_generator.py, add a function `validate_results(user_question, sql_query, 
   results_df)` that sends the user's original question, the SQL, and a summary 
   of the results (column names, row count, first 5 rows, basic stats) to Claude 
   and asks: "Does this SQL correctly answer the user's question? Rate confidence 
   as HIGH, MEDIUM, or LOW. If LOW, explain what might be wrong."

2. In the Streamlit UI, show a colored confidence badge next to results:
   - GREEN for HIGH confidence
   - YELLOW for MEDIUM (with a note: "Review recommended")
   - RED for LOW (with a note: "Results may not match your question — please verify")

3. Add a "hallucination check" in table_recommender.py: after recommending tables, 
   verify that every recommended table and column actually exists in 
   table_registry.json. If any don't exist, remove them and log a warning.

4. Track accuracy metrics in a new file `metadata/accuracy_log.json`:
   - Total queries processed
   - Queries where SQL executed successfully (no errors)
   - Queries where user marked "helpful" in feedback
   - Queries where user modified the SQL (indicating the generated version was wrong)
   - Calculate and display these percentages on the Feedback page as a simple 
     accuracy dashboard
```

---

## SECTION A.1: Frequently Asked Questions

### Do I need Python installed locally?
Yes. Python is required. Install Python 3.11 from python.org (free, 10 minutes). 
SQLite comes bundled with Python automatically — no separate install needed. 
After building locally, deploy to Streamlit Community Cloud (free) to get a 
shareable URL for the interviewer.

### Do I need Power BI before running Claude Code?
No. Install Power BI Desktop (free, Windows only) at the end, just for the demo. 
The POC exports Excel/CSV files and generates written Power BI setup instructions. 
On Mac, use the Streamlit charts as your dashboard demo.

### Who writes the metadata?
70% is auto-generated by the script (column names, types, sample values, stats, 
auto-detected joins). You manually add business descriptions for the remaining 30% 
(~30-45 minutes of work). This manual step is what makes the LLM understand 
business meaning rather than just column names.

### Where is the RAG data stored?
NOT in SQLite. SQLite holds business data (sales, products). The RAG knowledge 
(metadata, data dictionary, relationships, use case logs) lives in JSON files 
that get injected into the LLM prompt. Vector databases are only needed at 
enterprise scale (1000+ tables).

### How do we prevent hallucination?
Three layers: (1) schema validation — LLM can only reference tables/columns that 
actually exist, (2) SQL self-correction loop with up to 3 retries, (3) confidence 
scoring where the LLM evaluates its own output. Use the supplementary prompt above 
to add the confidence scoring after the main build.

---

## SECTION B: Pre-Work Before Running the Prompt

### B1. Dataset: Olist Brazilian E-Commerce (Already Downloaded)

You are using the Olist Brazilian E-Commerce dataset from Kaggle with 8 CSV files.
Place all 8 files in the `data/raw/` folder. The translation table is NOT used 
(product category names have been manually translated to English).

**The 8 tables and their relationships:**

```
olist_customers_dataset.csv
  └─ customer_id (PK), customer_unique_id, customer_zip_code_prefix, 
     customer_city, customer_state

olist_orders_dataset.csv
  └─ order_id (PK), customer_id (FK → customers)
     order_status, order_purchase_timestamp, order_approved_at,
     order_delivered_carrier_date, order_delivered_customer_date,
     order_estimated_delivery_date

olist_order_items_dataset.csv
  └─ order_id (FK → orders), order_item_id, product_id (FK → products),
     seller_id (FK → sellers), shipping_limit_date, price, freight_value

olist_order_payments_dataset.csv
  └─ order_id (FK → orders), payment_sequential, payment_type,
     payment_installments, payment_value

olist_order_reviews_dataset.csv
  └─ review_id, order_id (FK → orders), review_score,
     review_comment_title, review_comment_message,
     review_creation_date, review_answer_timestamp

olist_products_dataset.csv
  └─ product_id (PK), product_category_name (in English),
     product_name_length, product_description_length,
     product_photos_qty, product_weight_g, product_length_cm,
     product_height_cm, product_width_cm

olist_sellers_dataset.csv
  └─ seller_id (PK), seller_zip_code_prefix, seller_city, seller_state

olist_geolocation_dataset.csv
  └─ geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
     geolocation_city, geolocation_state
```

**Key join paths:**
- orders → customers (via customer_id)
- order_items → orders (via order_id)
- order_items → products (via product_id)
- order_items → sellers (via seller_id)
- order_payments → orders (via order_id)
- order_reviews → orders (via order_id)
- geolocation → customers/sellers (via zip_code_prefix)

**This is a rich dataset for the POC** because it covers the full e-commerce 
lifecycle: customers, orders, items, payments, reviews, products, sellers, 
and geography. The agents can answer questions about revenue, order trends, 
customer behavior, seller performance, delivery times, payment patterns, 
product categories, and geographic analysis.

### B2. Complete Installation Checklist (Windows 11)

#### PHASE 1: Install Before Running Claude Code

Step 1 — Python 3.11:
  Download from https://www.python.org/downloads/
  CRITICAL: Check "Add Python to PATH" during installation
  Verify: Open PowerShell → type `python --version`

Step 2 — Git:
  Download from https://git-scm.com/download/win
  Install with default settings
  Verify: Open PowerShell → type `git --version`

Step 3 — Set Anthropic API Key:
  Open PowerShell as Administrator and run:
  [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-key-here", "User")
  Close and reopen PowerShell for it to take effect
  Verify: type `echo $env:ANTHROPIC_API_KEY`

Step 4 — Create GitHub Repository:
  Go to github.com → click "+" → New Repository
  Name: ai-dashboard-generator
  Description: "AI-powered natural language dashboard generator — RAG + Agentic AI"
  Public repository (so interviewer can see it)
  Do NOT initialize with README (Claude Code creates it)

Step 5 — Verify Claude Code:
  Open PowerShell → type `claude --version`

Note: You already have Cursor which is a fork of VS Code. Use Cursor as your 
code editor — no need to install VS Code separately.

#### PHASE 2: Install After Claude Code Builds the Project

Step 6 — Power BI Desktop (Free):
  Download from Microsoft Store or https://powerbi.microsoft.com/desktop/
  Install and open once to verify it works

Step 7 — Claude Desktop (for Power BI MCP — Free):
  Download from https://claude.ai/download
  This acts as the MCP client that connects to the Power BI Modeling MCP server
  No GitHub Copilot subscription needed — Claude Desktop is free

Step 8 — Power BI Modeling MCP Server Setup:
  a) Download the VSIX package from VS Code marketplace:
     https://marketplace.visualstudio.com/_apis/public/gallery/publishers/analysis-services/vsextensions/powerbi-modeling-mcp/0.1.9/vspackage?targetPlatform=win32-x64
  b) Rename the downloaded .vsix file to .zip
  c) Unzip to a folder, e.g.: C:\MCPServers\PowerBIModelingMCP
  d) Add this to Claude Desktop's MCP config (Settings → Developer → Edit Config):
     {
       "mcpServers": {
         "powerbi-modeling-mcp": {
           "command": "C:\\MCPServers\\PowerBIModelingMCP\\extension\\server\\powerbi-modeling-mcp.exe",
           "args": ["--start"]
         }
       }
     }
  e) Restart Claude Desktop
  f) Verify: In Claude Desktop chat, type "What Power BI modeling tools are available?"
     It should list the MCP tools

  Alternative: If you prefer, you can also configure the MCP server in Cursor 
  directly using Cursor's built-in MCP support (Settings → MCP Servers).

#### Things You Do NOT Need to Install:
  - VS Code (you have Cursor, which is equivalent)
  - GitHub Copilot (Claude Desktop replaces it as the MCP client — saves $10/month)
  - SQLite (comes built into Python)
  - Streamlit account (just pip install streamlit)
  - Docker, Node.js, or any database server
  - Everything is completely free

### B3. After Claude Code Builds It

Once Claude Code has built the project:

```bash
# 1. Place your CSV files in data/raw/
copy C:\Users\YourName\Downloads\*.csv ai-dashboard-generator\data\raw\

# 2. Load data into SQLite
cd ai-dashboard-generator
python setup_database.py

# 3. Generate metadata
python generate_metadata.py

# 4. CRITICAL: Manually enrich the metadata
# Open metadata/table_registry.json and metadata/data_dictionary.json
# Fill in ALL the empty "description" fields with business context
# Example: "revenue" → "Total revenue in USD from the sale, calculated as 
#           unit_price × quantity before discounts"

# 5. Launch the app
streamlit run app/streamlit_app.py
```

---

## SECTION C: Architecture Deep-Dive (For Interview Discussion)

### C1. Why This Is RAG (Retrieval-Augmented Generation)

```
Traditional LLM Call:
  User Question → LLM → Answer (LLM guesses based on training data)

RAG in Your System:
  User Question → RETRIEVE metadata/dictionaries → AUGMENT the prompt 
  with this context → LLM GENERATES an informed answer

What's being retrieved:
  - Table schemas and descriptions (from table_registry.json)
  - Column meanings and sample values (from data_dictionary.json)
  - Table relationships (from relationships.json)
  - Past similar use cases (from use_case_log.json)
```

The LLM never "memorizes" your data. Every time it answers, it reads the metadata 
fresh from your files. This means:
- You can update metadata without retraining anything
- The system adapts immediately when new tables are added
- Different users can get different context based on their permissions (enterprise)

### C2. Why This Is Agentic

A single LLM call can't do everything. Your system has multiple specialized agents 
that work in sequence, each making decisions:

```
User: "Show me top products by profit margin in each region"
                    │
                    ▼
     ┌──────────────────────────┐
     │  AGENT 1: Table Finder   │  ← Reads metadata, decides which tables
     │  "You need: sales,       │     are relevant. This is a DECISION.
     │   products, regions"     │
     └────────────┬─────────────┘
                  │
                  ▼
     ┌──────────────────────────┐
     │  AGENT 2: SQL Writer     │  ← Writes SQL, executes it, self-corrects
     │  "SELECT p.name,        │     if errors occur. This is AUTONOMOUS
     │   r.region, ..."        │     ACTION with error recovery.
     └────────────┬─────────────┘
                  │
                  ▼
     ┌──────────────────────────┐
     │  AGENT 3: Viz Advisor    │  ← Analyzes results shape, recommends
     │  "Use grouped bar chart  │     best visualization. Another DECISION.
     │   with region coloring"  │
     └────────────┬─────────────┘
                  │
                  ▼
           Dashboard Output
```

Each agent is "agentic" because it:
- Receives a goal, not step-by-step instructions
- Makes decisions based on context
- Can self-correct (SQL agent retries on errors)
- Passes structured output to the next agent

### C3. The Feedback Loop (Not Fine-Tuning)

```
                    ┌──────────────────┐
                    │   User asks a    │
                    │   question       │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  System answers  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  User provides   │
                    │  feedback:       │
                    │  - Actual tables │
                    │  - Modified SQL  │
                    │  - Helpful Y/N   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Stored in       │
                    │  use_case_log    │◄─── This is your "training"
                    └────────┬─────────┘     It's really a growing
                             │               knowledge base
                    ┌────────▼─────────┐
                    │  Next time a     │
                    │  similar question│
                    │  is asked, the   │
                    │  log is included │
                    │  in the RAG      │
                    │  context         │
                    └──────────────────┘
```

This is NOT model fine-tuning. The model weights don't change. Instead, you're 
building an ever-growing knowledge base that gets injected into the prompt context 
each time. This is sometimes called "few-shot learning from user feedback" or 
"dynamic RAG with feedback augmentation."

### C4. Enterprise Scale-Up Mapping

| POC Component             | Enterprise (GCP) Equivalent                          |
|---------------------------|------------------------------------------------------|
| CSV files in data/raw/    | Raw data landing in GCS buckets                      |
| SQLite database           | BigQuery datasets and tables                         |
| JSON metadata files       | Google Data Catalog / Dataplex + custom metadata store|
| JSON metadata (RAG)       | Vector DB (Pinecone/Vertex AI) for 1000+ table search |
| use_case_log.json         | BigQuery table with analyst usage analytics           |
| Streamlit app             | Internal web app (Cloud Run) or Power BI embedded     |
| Claude API direct calls   | Claude API behind Apigee gateway with auth + logging  |
| Local Python agents       | Cloud Functions or Cloud Run microservices             |
| Manual metadata entry     | Automated via BigQuery INFORMATION_SCHEMA + DBT docs  |
| File-based feedback       | Pub/Sub event pipeline → BigQuery analytics table     |

Key enterprise additions:
- **Authentication & RBAC**: Users only see tables they have access to
- **Cost controls**: Token budgets per department, query cost estimation
- **Audit logging**: Every generated query logged for compliance
- **Data governance**: PII detection, query result masking
- **Power BI Modeling MCP**: Claude creates semantic models (tables, measures, 
  relationships) directly inside Power BI via Microsoft's official MCP server
- **Power BI Remote MCP**: Claude queries existing Power BI datasets using 
  natural language DAX generation — no export step needed
- **BigQuery MCP**: Claude queries BigQuery directly via MCP server
- **Caching layer**: Common queries cached to reduce API costs

### C5. Power BI MCP Server — The Bridge to Automated Dashboards

Microsoft released two official Power BI MCP servers at Ignite 2025. These are 
game-changers for your architecture:

**Modeling MCP Server (Local):**
- Runs alongside Power BI Desktop on your machine
- Lets AI agents create/modify tables, columns, measures, and relationships 
  inside Power BI using natural language
- Works via Claude Desktop or VS Code with GitHub Copilot
- LIMITATION: Cannot create report visuals (bar charts, etc.) — only the 
  semantic model (data layer)
- Best for: bulk operations, creating measures, setting up data models

**Remote MCP Server (Cloud):**
- Hosted endpoint at api.fabric.microsoft.com
- Lets AI agents query existing Power BI semantic models
- Generates and executes DAX queries using Copilot's engine
- Uses the authenticated user's permissions for security
- Best for: "chat with your data" scenarios against existing enterprise models

**Key capability of the Modeling MCP Server (available tools):**
- connection_operations: Connect to Power BI Desktop or Fabric workspaces
- table_operations: Create, update, delete, list, rename tables
- column_operations: Manage columns in tables
- measure_operations: Create, update, delete DAX measures
- relationship_operations: Create relationships between tables
- dax_query_operations: Execute and validate DAX queries
- calculation_group_operations: Create calculation groups for time intelligence
- security_role_operations: Configure row-level security
- culture_operations: Multi-language translations

**What the MCP server CAN vs CANNOT do:**

```
✅ CAN DO (Semantic Model / Data Layer):
   - Create tables with columns and data types
   - Write and add DAX measures (Total Revenue, YoY Growth, etc.)
   - Set up relationships between tables
   - Execute and validate DAX queries
   - Bulk rename, translate, document hundreds of objects
   - Apply modeling best practices automatically
   - Work with Power BI Project (PBIP) files

❌ CANNOT DO (Report Visual Layer):
   - Create report pages
   - Add bar charts, line charts, KPI cards, slicers
   - Set colors, titles, formatting on visuals
   - Modify diagram layouts
   - Create or modify dashboards/report pages
```

**POC Demo Strategy (Two-Part Demo):**

```
DEMO PART 1 — Automated Intelligence Pipeline (Streamlit):
   User types question → Agents find tables → Generate SQL → 
   Run query → Show Plotly charts → Export data to Excel
   → Runs end-to-end automatically, no manual steps

DEMO PART 2 — Power BI MCP Showcase (VS Code + PBI Desktop):
   Open VS Code with GitHub Copilot → Connect to Power BI Desktop 
   via Modeling MCP → Prompt: "Create a semantic model with a Sales 
   table containing product_category, month, total_revenue. Add a 
   MoM growth measure. Set up relationships." → Watch it build the 
   model live → Open a pre-built report template → Dashboard populates

This two-part approach shows:
1. The intelligence layer works (Streamlit demo)
2. The Power BI integration path exists (MCP demo)
   Without risking the entire demo on preview software
```

**Dual-Path Output Architecture:**

```
                YOUR INTELLIGENCE LAYER
                (Same for both paths)
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
   PATH A: STREAMLIT           PATH B: POWER BI
   (Quick exploration)         (Enterprise, governed)
   - Plotly charts             - Modeling MCP creates
   - Real-time answers           semantic model
   - For analysts on           - Pre-built templates
     the go                      for visual layer
                               - Row-level security
                               - Shared & embedded
```

**Important caveats to mention in the interview (shows you did your homework):**
- The MCP server is still in Public Preview — not GA yet
- Complex DAX generation by LLMs can be unreliable for sophisticated 
  business logic — simple aggregations and measures work well
- The Modeling MCP server cannot create report visuals, only the semantic 
  model — you still need pre-built report templates for the visual layer
- Enterprise deployment needs Entra ID authentication and admin tenant settings
- Data retrieved by the MCP server may be sent to the LLM provider — 
  governance should cover AI data-handling policies

---

## SECTION D: Interview Talking Points

### D1. Why This Approach Over Traditional Power BI

Frame it as: "This doesn't replace Power BI. It makes Power BI accessible to 
100% of the organization instead of the 10% who know DAX."

Key arguments:
- **Time to insight drops from days to minutes**: No more waiting for the BI team 
  to build a report
- **Institutional knowledge is captured**: The feedback loop means tribal knowledge 
  about "which table has what" is systematically recorded
- **Self-service that actually works**: Unlike Power BI self-service which still 
  requires data modeling skills, this needs zero technical knowledge
- **The AI layer improves over time**: More feedback = better recommendations
- **Microsoft is going this direction too**: The Power BI MCP server at Ignite 2025 
  validates that Microsoft themselves see AI agents interacting with Power BI as 
  the future — your POC aligns with Microsoft's own roadmap

### D2. Risks to Acknowledge (Shows Maturity)

- **Accuracy**: LLM-generated SQL and DAX needs human review before business-critical 
  decisions — especially complex DAX where LLMs can produce plausible-looking code 
  with wrong semantics
- **Hallucination**: The metadata layer (RAG) dramatically reduces hallucination 
  but doesn't eliminate it
- **Cost**: Claude API calls at enterprise scale need budgeting (show you've thought 
  about this)
- **Data security**: Sensitive data going through an external API needs encryption 
  and governance
- **Change management**: Analysts may resist a tool that automates part of their role; 
  position it as augmentation, not replacement
- **MCP maturity**: The Power BI MCP server is in Public Preview — production 
  deployment needs careful evaluation of stability and security

### D3. Quick Demo Script (For Showing the POC)

1. Open the Streamlit app
2. Type: "What are the top 5 products by total revenue in each region?"
3. Show: table recommendations with reasoning
4. Show: generated SQL with explanation
5. Show: the chart auto-generated
6. Show: the Data Catalog page (metadata explorer)
7. Show: the Feedback page (training loop)
8. Export to Excel → open in Power BI → show the final dashboard
9. Close with: "This is Phase 1 — the intelligence layer. Phase 2 integrates 
   Microsoft's Power BI Modeling MCP server so the semantic model is built 
   automatically. At enterprise scale with BigQuery and the Remote MCP server, 
   users would query existing Power BI models directly through natural language."

---

## SECTION E: Additional Recommendations

### E1. What to Add If You Have Extra Time

1. **Conversation memory**: Let the user ask follow-up questions 
   ("Now filter that by Q4 only") by maintaining chat history in Streamlit session state

2. **Data quality checker**: Before generating SQL, have an agent that checks if the 
   data has issues (nulls, outliers, date range gaps) and warns the user

3. **Multi-dashboard mode**: User describes 3-4 charts → system generates all of them 
   → exports as a single Power BI page layout specification

### E2. Technologies to Mention in the Interview

- **Power BI MCP Server**: Microsoft's official MCP integration (released at 
  Ignite 2025) lets AI agents create semantic models inside Power BI. The Modeling 
  MCP server handles tables, measures, and relationships. The Remote MCP server 
  enables natural language querying of existing Power BI datasets. This validates 
  that Microsoft themselves see AI agents as the future of BI.
- **Claude's tool use / function calling**: Your agents could use Claude's native 
  tool-use capability to call functions directly, making the architecture even cleaner
- **MCP (Model Context Protocol)**: For production, Claude would connect to BigQuery, 
  Power BI, GCS, and Slack natively via MCP servers — no custom API wrappers needed
- **Evaluation frameworks**: Mention that in production, you'd use systematic 
  evaluation to measure SQL accuracy, table recommendation precision, and user 
  satisfaction over time
- **Vector search for metadata**: At enterprise scale with 1000+ tables, you'd use 
  embedding-based search to find the most relevant tables instead of stuffing all 
  metadata into the prompt
