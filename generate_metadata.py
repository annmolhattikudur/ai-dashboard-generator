"""
generate_metadata.py
Auto-generates metadata from the SQLite database:
  - table_registry.json
  - data_dictionary.json
  - relationships.json
  - use_case_log.json
  - domain_knowledge.json (pre-filled with Olist domain knowledge)
"""

import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime

from config import (
    DATABASE_PATH,
    METADATA_DIR,
    TABLE_REGISTRY_PATH,
    DATA_DICTIONARY_PATH,
    RELATIONSHIPS_PATH,
    DOMAIN_KNOWLEDGE_PATH,
    USE_CASE_LOG_PATH,
)

# ─────────────────────────────────────────────
# Pre-filled descriptions from dataset context
# ─────────────────────────────────────────────

TABLE_DESCRIPTIONS = {
    "olist_orders_dataset": (
        "Central fact table containing all orders. Each row is one order. "
        "Links to customers, items, payments, and reviews. "
        "Includes order status (delivered, shipped, canceled, etc.) and timestamps "
        "from purchase to delivery. Data spans Sep 2016 – Oct 2018."
    ),
    "olist_order_items_dataset": (
        "Line-item table where each row is one product in an order. "
        "An order can have multiple items. "
        "Contains price and freight_value per item. "
        "Total order value = SUM(price) + SUM(freight_value) for all items in an order."
    ),
    "olist_products_dataset": (
        "Product catalog with dimensions, weight, and category information. "
        "Product category names are in English. "
        "Used to analyze assortment, category mix, and physical product attributes."
    ),
    "olist_customers_dataset": (
        "Customer dimension table. customer_id is a per-order identifier; "
        "customer_unique_id is the true unique customer identifier. "
        "Always use customer_unique_id for counting unique customers. "
        "Includes customer location (city, state, zip code prefix)."
    ),
    "olist_sellers_dataset": (
        "Seller/vendor dimension table. Contains seller location data "
        "(city, state, zip code prefix). "
        "Used for seller performance analysis and geographic distribution of sellers."
    ),
    "olist_order_payments_dataset": (
        "Payment records for each order. An order can have multiple payment entries "
        "(e.g., split between credit card and voucher). "
        "payment_value is the authoritative revenue figure. "
        "Credit card is the most common payment type with the highest average order value."
    ),
    "olist_order_reviews_dataset": (
        "Customer review data linked to orders. review_score is 1–5; "
        "the dataset average is approximately 4.0. "
        "Contains optional review comment title and message. "
        "Used for customer satisfaction and NPS-style analysis."
    ),
    "olist_geolocation_dataset": (
        "Geographic lookup table mapping zip code prefixes to lat/lng coordinates. "
        "Used for mapping customer and seller locations. "
        "Joins to customers and sellers on zip_code_prefix."
    ),
    "product_category_name_translation": (
        "Maps Portuguese product category names to English equivalents. "
        "ALWAYS join with olist_products_dataset on product_category_name "
        "when displaying category names to users."
    ),
}

COLUMN_DESCRIPTIONS = {
    # olist_orders_dataset
    "olist_orders_dataset.order_id": "Unique identifier for each order. Primary key. Used to join to all other order-related tables.",
    "olist_orders_dataset.customer_id": "Per-order customer identifier. Foreign key to olist_customers_dataset.customer_id. NOT the unique customer — use customer_unique_id for that.",
    "olist_orders_dataset.order_status": "Current status of the order. Values: delivered, shipped, canceled, processing, invoiced, unavailable, approved, created.",
    "olist_orders_dataset.order_purchase_timestamp": "Timestamp when the customer placed the order.",
    "olist_orders_dataset.order_approved_at": "Timestamp when payment was approved.",
    "olist_orders_dataset.order_delivered_carrier_date": "Timestamp when the order was handed to the logistics carrier.",
    "olist_orders_dataset.order_delivered_customer_date": "Actual delivery timestamp to the customer.",
    "olist_orders_dataset.order_estimated_delivery_date": "Estimated delivery date shown to customer at time of purchase.",
    # olist_order_items_dataset
    "olist_order_items_dataset.order_id": "Foreign key to olist_orders_dataset. An order can have multiple rows here (one per item).",
    "olist_order_items_dataset.order_item_id": "Sequential item number within the order (1, 2, 3...).",
    "olist_order_items_dataset.product_id": "Foreign key to olist_products_dataset.",
    "olist_order_items_dataset.seller_id": "Foreign key to olist_sellers_dataset.",
    "olist_order_items_dataset.shipping_limit_date": "Deadline for the seller to hand the item to the carrier.",
    "olist_order_items_dataset.price": "Item price in BRL. Does not include freight.",
    "olist_order_items_dataset.freight_value": "Freight cost for this item in BRL.",
    # olist_products_dataset
    "olist_products_dataset.product_id": "Unique product identifier. Primary key.",
    "olist_products_dataset.product_category_name": "Product category name in English.",
    "olist_products_dataset.product_name_lenght": "Character length of the product name (note: original column has typo 'lenght').",
    "olist_products_dataset.product_description_lenght": "Character length of the product description.",
    "olist_products_dataset.product_photos_qty": "Number of product photos listed.",
    "olist_products_dataset.product_weight_g": "Product weight in grams.",
    "olist_products_dataset.product_length_cm": "Product length in centimeters.",
    "olist_products_dataset.product_height_cm": "Product height in centimeters.",
    "olist_products_dataset.product_width_cm": "Product width in centimeters.",
    # olist_customers_dataset
    "olist_customers_dataset.customer_id": "Per-order customer ID. This changes per order — NOT the unique customer identifier.",
    "olist_customers_dataset.customer_unique_id": "True unique customer identifier. Use this for counting unique customers.",
    "olist_customers_dataset.customer_zip_code_prefix": "5-digit zip code prefix. Joins to olist_geolocation_dataset.",
    "olist_customers_dataset.customer_city": "Customer city name.",
    "olist_customers_dataset.customer_state": "Brazilian state abbreviation (e.g., SP, RJ, MG).",
    # olist_sellers_dataset
    "olist_sellers_dataset.seller_id": "Unique seller identifier. Primary key.",
    "olist_sellers_dataset.seller_zip_code_prefix": "5-digit zip code prefix for seller location.",
    "olist_sellers_dataset.seller_city": "City where the seller is located.",
    "olist_sellers_dataset.seller_state": "Brazilian state abbreviation for the seller.",
    # olist_order_payments_dataset
    "olist_order_payments_dataset.order_id": "Foreign key to olist_orders_dataset. An order can have multiple payment rows.",
    "olist_order_payments_dataset.payment_sequential": "Sequence number when multiple payment methods are used for one order.",
    "olist_order_payments_dataset.payment_type": "Payment method. Values: credit_card, boleto, voucher, debit_card.",
    "olist_order_payments_dataset.payment_installments": "Number of installments chosen. Credit card purchases are often in multiple installments in Brazil.",
    "olist_order_payments_dataset.payment_value": "Amount paid in BRL. Use SUM(payment_value) for total order revenue.",
    # olist_order_reviews_dataset
    "olist_order_reviews_dataset.review_id": "Unique review identifier.",
    "olist_order_reviews_dataset.order_id": "Foreign key to olist_orders_dataset.",
    "olist_order_reviews_dataset.review_score": "Customer satisfaction score from 1 (worst) to 5 (best). Dataset average ≈ 4.0.",
    "olist_order_reviews_dataset.review_comment_title": "Optional short title for the review.",
    "olist_order_reviews_dataset.review_comment_message": "Optional detailed review message from the customer.",
    "olist_order_reviews_dataset.review_creation_date": "Date when the review was created.",
    "olist_order_reviews_dataset.review_answer_timestamp": "Timestamp when the review survey was answered.",
    # olist_geolocation_dataset
    "olist_geolocation_dataset.geolocation_zip_code_prefix": "5-digit zip code prefix. Joins to customer and seller zip code columns.",
    "olist_geolocation_dataset.geolocation_lat": "Latitude coordinate for the zip code prefix.",
    "olist_geolocation_dataset.geolocation_lng": "Longitude coordinate for the zip code prefix.",
    "olist_geolocation_dataset.geolocation_city": "City name for this zip code prefix.",
    "olist_geolocation_dataset.geolocation_state": "Brazilian state abbreviation.",
    # product_category_name_translation
    "product_category_name_translation.product_category_name": "Product category name in Portuguese. Joins to olist_products_dataset.product_category_name.",
    "product_category_name_translation.product_category_name_english": "English translation of the product category name.",
}

DOMAIN_KNOWLEDGE = {
    "domain": "Brazilian E-Commerce (Olist Marketplace)",
    "dataset_notes": [
        "Product categories are in Portuguese — ALWAYS join with product_category_name_translation table",
        "Use customer_unique_id for unique customer counts, NOT customer_id (customer_id is per-order)",
        "Revenue = SUM(payment_value) from payments table OR SUM(price + freight_value) from order_items",
        "Data spans Sep 2016 to Oct 2018. Best analysis window: Jan 2017 to Aug 2018",
        "An order can have multiple items (order_items) and multiple payments (order_payments)",
        "Total order value = SUM(price) + SUM(freight_value) for all items in that order",
    ],
    "metrics": {
        "total_revenue": {
            "definition": "Total monetary value of all completed orders",
            "formula": "SUM(payment_value) from order_payments WHERE order_status = 'delivered'",
            "tables_needed": ["olist_orders_dataset", "olist_order_payments_dataset"],
            "sql_pattern": "SELECT SUM(p.payment_value) as total_revenue FROM olist_order_payments_dataset p JOIN olist_orders_dataset o ON p.order_id = o.order_id WHERE o.order_status = 'delivered'",
        },
        "revenue_trend": {
            "definition": "Revenue aggregated over time periods to show growth or decline",
            "formula": "SUM(payment_value) grouped by month/quarter/year",
            "tables_needed": ["olist_orders_dataset", "olist_order_payments_dataset"],
            "sql_pattern": "SELECT strftime('%Y-%m', o.order_purchase_timestamp) as month, SUM(p.payment_value) as revenue FROM olist_order_payments_dataset p JOIN olist_orders_dataset o ON p.order_id = o.order_id GROUP BY month ORDER BY month",
        },
        "average_order_value": {
            "definition": "Average revenue per order",
            "formula": "Total Revenue / Number of Unique Orders",
            "tables_needed": ["olist_order_payments_dataset"],
            "sql_pattern": "SELECT ROUND(SUM(payment_value) / COUNT(DISTINCT order_id), 2) as aov FROM olist_order_payments_dataset",
        },
        "distinct_sku_sold": {
            "definition": "Number of unique products available in a category or overall",
            "formula": "COUNT(DISTINCT product_id)",
            "tables_needed": ["olist_products_dataset", "product_category_name_translation"],
            "sql_pattern": "SELECT t.product_category_name_english as category, COUNT(DISTINCT p.product_id) as assortment FROM olist_products_dataset p JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name GROUP BY category ORDER BY assortment DESC",
        },
        "customer_satisfaction": {
            "definition": "Average review score given by customers (1-5 scale)",
            "formula": "AVG(review_score)",
            "tables_needed": ["olist_order_reviews_dataset"],
            "sql_pattern": "SELECT ROUND(AVG(review_score), 2) as avg_satisfaction FROM olist_order_reviews_dataset",
            "known_insight": "Average across all products is approximately 4.0",
        },
        "order_cancellation_rate": {
            "definition": "Percentage of orders that were cancelled",
            "formula": "(COUNT orders WHERE status='canceled' / COUNT all orders) * 100",
            "tables_needed": ["olist_orders_dataset"],
            "sql_pattern": "SELECT ROUND(100.0 * SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) / COUNT(*), 2) as cancellation_rate FROM olist_orders_dataset",
            "known_insight": "Cancellation rate is approximately 0.6%",
        },
        "delivery_performance": {
            "definition": "How actual delivery compares to estimated delivery date",
            "formula": "julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)",
            "tables_needed": ["olist_orders_dataset"],
            "sql_pattern": "SELECT ROUND(AVG(julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date)), 1) as avg_days_diff FROM olist_orders_dataset WHERE order_delivered_customer_date IS NOT NULL",
        },
        "sales_growth": {
            "definition": "Percentage change in revenue between two consecutive periods",
            "formula": "((Current Period Revenue - Previous Period Revenue) / Previous Period Revenue) * 100",
            "tables_needed": ["olist_orders_dataset", "olist_order_payments_dataset"],
        },
        "top_categories": {
            "definition": "Product categories ranked by order volume or revenue",
            "tables_needed": ["olist_order_items_dataset", "olist_products_dataset", "product_category_name_translation"],
            "known_insight": "Top categories by volume: bed_bath_table, health_beauty, sports_leisure, furniture_decor, computers_accessories",
        },
        "seller_performance": {
            "definition": "Revenue, order count, and review scores per seller",
            "tables_needed": ["olist_order_items_dataset", "olist_sellers_dataset", "olist_order_reviews_dataset", "olist_orders_dataset"],
        },
        "payment_analysis": {
            "definition": "Breakdown of orders by payment method and installment patterns",
            "tables_needed": ["olist_order_payments_dataset"],
            "known_insight": "Credit card is the most common payment method with highest AOV",
        },
        "customer_geography": {
            "definition": "Distribution of customers and orders by state/city",
            "tables_needed": ["olist_customers_dataset", "olist_orders_dataset"],
            "known_insight": "Sao Paulo (SP) has the highest customer density",
        },
        "freight_analysis": {
            "definition": "Shipping cost analysis by product weight, category, or distance",
            "formula": "AVG(freight_value) or SUM(freight_value) / SUM(price) for freight-to-price ratio",
            "tables_needed": ["olist_order_items_dataset", "olist_products_dataset"],
        },
    },
    "common_dimensions": {
        "time": ["daily", "weekly", "monthly", "quarterly", "yearly", "YoY", "MoM"],
        "product": ["category (English)", "product_id"],
        "geography": ["customer_state", "customer_city", "seller_state", "seller_city"],
        "customer": ["customer_unique_id", "customer_state"],
        "payment": ["payment_type", "payment_installments"],
        "order_status": ["delivered", "shipped", "canceled", "processing"],
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
        "Be aware that Sep-Oct 2018 data is incomplete — warn user if their query includes this period",
    ],
}


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

def get_sample_values(conn, table, column, max_samples=5):
    """Get up to max_samples distinct non-null values for a column."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT {max_samples}'
        )
        return [str(row[0]) for row in cursor.fetchall()]
    except Exception:
        return []


def detect_column_type(conn, table, column):
    """Detect if column is date, numeric, or categorical."""
    samples = get_sample_values(conn, table, column, max_samples=10)
    if not samples:
        return "unknown"

    # Check numeric
    numeric_count = 0
    for v in samples:
        try:
            float(v)
            numeric_count += 1
        except (ValueError, TypeError):
            pass
    if numeric_count == len(samples):
        return "numeric"

    # Check date-like
    date_patterns = [r'\d{4}-\d{2}-\d{2}', r'\d{2}/\d{2}/\d{4}']
    for v in samples:
        for pat in date_patterns:
            if re.match(pat, str(v)):
                return "date"

    return "categorical"


def get_column_stats(conn, table, column, col_type):
    """Get min/max for numeric/date columns."""
    min_val, max_val = None, None
    if col_type in ("numeric", "date"):
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT MIN("{column}"), MAX("{column}") FROM "{table}"')
            row = cursor.fetchone()
            if row:
                min_val = str(row[0]) if row[0] is not None else None
                max_val = str(row[1]) if row[1] is not None else None
        except Exception:
            pass
    return min_val, max_val


def get_unique_count(conn, table, column):
    try:
        cursor = conn.cursor()
        cursor.execute(f'SELECT COUNT(DISTINCT "{column}") FROM "{table}"')
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def is_nullable(conn, table, column):
    try:
        cursor = conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NULL')
        row = cursor.fetchone()
        return (row[0] > 0) if row else True
    except Exception:
        return True


def detect_primary_key_candidate(columns):
    """Return the first column that ends with _id."""
    for col in columns:
        if col.endswith('_id'):
            return col
    return columns[0] if columns else None


def detect_relationships(table_columns: dict) -> list:
    """Auto-detect FK relationships by matching column names across tables."""
    relationships = []
    tables = list(table_columns.keys())

    for i, table_a in enumerate(tables):
        for col_a in table_columns[table_a]:
            for table_b in tables:
                if table_b == table_a:
                    continue
                if col_a in table_columns[table_b]:
                    # Avoid duplicate pairs
                    existing = any(
                        r['from_table'] == table_b and r['from_column'] == col_a
                        and r['to_table'] == table_a
                        for r in relationships
                    )
                    if not existing:
                        relationships.append({
                            "from_table": table_a,
                            "from_column": col_a,
                            "to_table": table_b,
                            "to_column": col_a,
                            "relationship_type": "many-to-one",
                            "confidence": "auto-detected",
                        })
    return relationships


# ─────────────────────────────────────────────
# Main generation logic
# ─────────────────────────────────────────────

def generate_metadata():
    print("=" * 60)
    print("AI Dashboard Generator — Metadata Generation")
    print("=" * 60)

    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print("ERROR: No tables found in database. Run setup_database.py first.")
        return

    print(f"\nFound {len(tables)} table(s): {', '.join(tables)}\n")

    # ── table_registry.json ──
    print("Generating table_registry.json...")
    table_registry = {}
    table_columns_map = {}

    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}")')
        pragma_rows = cursor.fetchall()
        columns = [row[1] for row in pragma_rows]
        table_columns_map[table] = columns

        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        row_count = cursor.fetchone()[0]

        date_cols, numeric_cols, categorical_cols, sample_values = [], [], [], {}

        for col in columns:
            col_type = detect_column_type(conn, table, col)
            if col_type == "date":
                date_cols.append(col)
            elif col_type == "numeric":
                numeric_cols.append(col)
            else:
                categorical_cols.append(col)
                sv = get_sample_values(conn, table, col, max_samples=5)
                if sv:
                    sample_values[col] = sv

        pk_candidate = detect_primary_key_candidate(columns)

        table_registry[table] = {
            "table_name": table,
            "description": TABLE_DESCRIPTIONS.get(table, ""),
            "row_count": row_count,
            "columns": columns,
            "primary_key_candidate": pk_candidate,
            "date_columns": date_cols,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "sample_values": sample_values,
        }

    with open(TABLE_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(table_registry, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Saved {TABLE_REGISTRY_PATH}")

    # ── data_dictionary.json ──
    print("Generating data_dictionary.json...")
    data_dictionary = {}

    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}")')
        pragma_rows = cursor.fetchall()

        for row in pragma_rows:
            col = row[1]
            sqlite_type = row[2] or "TEXT"
            key = f"{table}.{col}"

            col_type = detect_column_type(conn, table, col)
            min_val, max_val = get_column_stats(conn, table, col, col_type)
            unique_count = get_unique_count(conn, table, col)
            nullable = is_nullable(conn, table, col)
            sample_vals = get_sample_values(conn, table, col, max_samples=5)

            data_dictionary[key] = {
                "data_type": sqlite_type,
                "nullable": nullable,
                "unique_count": unique_count,
                "sample_values": sample_vals,
                "min_value": min_val,
                "max_value": max_val,
                "description": COLUMN_DESCRIPTIONS.get(key, ""),
            }

    with open(DATA_DICTIONARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(data_dictionary, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Saved {DATA_DICTIONARY_PATH}")

    # ── relationships.json ──
    print("Generating relationships.json...")
    relationships = detect_relationships(table_columns_map)

    # Add known relationships from project spec
    known_relationships = [
        {"from_table": "olist_orders_dataset", "from_column": "customer_id", "to_table": "olist_customers_dataset", "to_column": "customer_id", "relationship_type": "many-to-one", "confidence": "verified"},
        {"from_table": "olist_order_items_dataset", "from_column": "order_id", "to_table": "olist_orders_dataset", "to_column": "order_id", "relationship_type": "many-to-one", "confidence": "verified"},
        {"from_table": "olist_order_items_dataset", "from_column": "product_id", "to_table": "olist_products_dataset", "to_column": "product_id", "relationship_type": "many-to-one", "confidence": "verified"},
        {"from_table": "olist_order_items_dataset", "from_column": "seller_id", "to_table": "olist_sellers_dataset", "to_column": "seller_id", "relationship_type": "many-to-one", "confidence": "verified"},
        {"from_table": "olist_order_payments_dataset", "from_column": "order_id", "to_table": "olist_orders_dataset", "to_column": "order_id", "relationship_type": "many-to-one", "confidence": "verified"},
        {"from_table": "olist_order_reviews_dataset", "from_column": "order_id", "to_table": "olist_orders_dataset", "to_column": "order_id", "relationship_type": "many-to-one", "confidence": "verified"},
        {"from_table": "olist_customers_dataset", "from_column": "customer_zip_code_prefix", "to_table": "olist_geolocation_dataset", "to_column": "geolocation_zip_code_prefix", "relationship_type": "many-to-one", "confidence": "verified"},
        {"from_table": "olist_sellers_dataset", "from_column": "seller_zip_code_prefix", "to_table": "olist_geolocation_dataset", "to_column": "geolocation_zip_code_prefix", "relationship_type": "many-to-one", "confidence": "verified"},
    ]

    # Merge: prefer verified over auto-detected
    verified_keys = set(
        (r["from_table"], r["from_column"], r["to_table"]) for r in known_relationships
    )
    filtered_auto = [
        r for r in relationships
        if (r["from_table"], r["from_column"], r["to_table"]) not in verified_keys
        and (r["to_table"], r["from_column"], r["from_table"]) not in verified_keys
    ]

    relationships_data = {
        "relationships": known_relationships + filtered_auto
    }

    with open(RELATIONSHIPS_PATH, 'w', encoding='utf-8') as f:
        json.dump(relationships_data, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Saved {RELATIONSHIPS_PATH} ({len(relationships_data['relationships'])} relationships)")

    # ── use_case_log.json ──
    print("Generating use_case_log.json...")
    use_case_log = {"use_cases": []}
    with open(USE_CASE_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(use_case_log, f, indent=2)
    print(f"  [OK] Saved {USE_CASE_LOG_PATH}")

    # ── domain_knowledge.json ──
    print("Generating domain_knowledge.json...")
    with open(DOMAIN_KNOWLEDGE_PATH, 'w', encoding='utf-8') as f:
        json.dump(DOMAIN_KNOWLEDGE, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Saved {DOMAIN_KNOWLEDGE_PATH}")

    conn.close()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("METADATA SUMMARY")
    print("=" * 60)
    for table in tables:
        t = table_registry[table]
        print(f"\n  {table}")
        print(f"    Rows: {t['row_count']:,}  |  Columns: {len(t['columns'])}")
        print(f"    Date cols:     {t['date_columns']}")
        print(f"    Numeric cols:  {t['numeric_columns']}")
        print(f"    Categorical:   {len(t['categorical_columns'])} columns")
    print(f"\n  Total columns in data dictionary: {len(data_dictionary)}")
    print(f"  Relationships detected: {len(relationships_data['relationships'])}")
    print("\nMetadata generation complete!")
    print("\nNEXT STEPS:")
    print("  Review and enrich metadata/table_registry.json and metadata/data_dictionary.json")
    print("  Then proceed to Phase 2: Building the agents")


if __name__ == "__main__":
    generate_metadata()
