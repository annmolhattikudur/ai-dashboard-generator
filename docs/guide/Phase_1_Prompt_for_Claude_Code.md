# PHASE 1: Project Setup, Database Loading, and Metadata Generation

Build ONLY Steps 1-3 described below. Do NOT build the agents, frontend, or 
Power BI export yet — those come in later phases. After completing these steps, 
stop and let me review the metadata before proceeding.

My CSV files are already placed in data/raw/ at my current working directory.

---

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
│   ├── table_recommender.py    # Agent 1: finds right tables
│   ├── sql_generator.py        # Agent 2: writes & runs SQL
│   ├── viz_recommender.py      # Agent 3: suggests visualizations
│   └── orchestrator.py         # Master agent that coordinates
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
    "distinct_sku_sold": {
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

## END OF PHASE 1

After building everything above:
1. Run setup_database.py and show me the table summary
2. Run generate_metadata.py and show me the metadata summary
3. STOP and let me review the metadata files before proceeding to Phase 2 (agents)

I will then ask you to help me enrich the metadata descriptions before we build 
the agents.

