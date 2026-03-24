# PHASE 3: Build the Frontend and Power BI Export (Steps 8-9)

Phase 2 is complete. The agents and orchestrator are working.
Now build the Power BI export handler and the Streamlit frontend that users 
interact with.

The agents are in the agents/ folder and work correctly. Use them as-is — 
call orchestrator.process_query() from the frontend.

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
       into Claude Desktop to trigger the Power BI Modeling MCP server. 
       For example:
       "Connect to 'Sales Dashboard' in Power BI Desktop. Create a table 
        called 'MonthlySales' with columns: month (date), category (text), 
        revenue (decimal). Add a measure 'Total Revenue' = SUM(MonthlySales[revenue]). 
        Add a measure 'MoM Growth' = ..."
     - User can copy these prompts and paste them into Claude Desktop

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

## END OF PHASE 3

After building everything above:
1. Run: streamlit run app/streamlit_app.py
2. Test Path A with: "What are the top 10 product categories by total revenue?"
3. Test Path B with: "Create a dashboard showing monthly revenue trend by category"
4. Verify the Data Catalog page loads correctly
5. Make a git commit: "feat: Streamlit frontend with dual-tab architecture + Power BI export"
6. STOP and show me the results before proceeding to Phase 4 (documentation)
