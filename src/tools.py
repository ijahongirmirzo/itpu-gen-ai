import sqlite3
import re
import logging
import requests
from typing import Optional
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
log = logging.getLogger("Tools")

# Block dangerous stuff
BAD_WORDS = [
    "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE",
    "REPLACE", "RENAME", "GRANT", "REVOKE", "COMMIT", "ROLLBACK", "PRAGMA"
]

def check_query(query):
    q = query.upper().strip()
    
    # Basic check
    if not q.startswith("SELECT"):
        return False, "Query must start with SELECT"
        
    for w in BAD_WORDS:
        # crude but works
        if f" {w} " in f" {q} " or f"{w} " in f"{q} " or f" {w}" in f" {q}":
            return False, f"Dangerous keyword found: {w}"
            
    if ";" in query.strip() and len(query.split(";")) > 2:
        return False, "One query at a time please"
        
    return True, "OK"

def query_db(query, db_path="data/print_analytics.db"):
    log.info(f"Running SQL: {query}")
    
    ok, msg = check_query(query)
    if not ok:
        log.warning(f"Query blocked: {msg}")
        return {"success": False, "error": msg}

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query)
        cols = [d[0] for d in c.description]
        rows = c.fetchall()
        conn.close()
        
        # Limit results for chat
        limit = 50
        truncated = False
        if len(rows) > limit:
            rows = rows[:limit]
            truncated = True
            
        return {
            "success": True, 
            "data": rows, 
            "columns": cols,
            "count": len(rows),
            "truncated": truncated
        }
    except Exception as e:
        log.error(f"SQL Error: {e}")
        return {"success": False, "error": str(e)}

def get_schema(db_path="data/print_analytics.db"):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        
        schema = {}
        for t in tables:
            c.execute(f"PRAGMA table_info({t})")
            cols = [{
                "name": r[1],
                "type": r[2]
            } for r in c.fetchall()]
            
            c.execute(f"SELECT count(*) FROM {t}")
            row_count = c.fetchone()[0]
            
            schema[t] = {
                "columns": cols,
                "rows": row_count
            }
        conn.close()
        return {"success": True, "schema": schema}
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_issue(title, body, token=None):
    # If no token, just simulate it
    token = token or os.environ.get("GITHUB_TOKEN")
    
    if not token:
        log.info("Simulating ticket creation (no token)")
        return {
            "success": True,
            "simulated": True,
            "url": "https://github.com/jahon/print-analytics/issues/new"
        }
        
    # TODO: Implement actual GitHub API call if user wants
    # For now, simulation is safer/easier for this demo unless explicitly configured
    
    return {
        "success": True,
        "simulated": True,
        "message": "Ticket logged locally (API not fully wired)",
        "ticket": {"title": title, "body": body}
    }

def get_sample_queries():
    return [
        {
            "label": "Success Rate by Printer",
            "text": "What is the success rate for each printer?"
        },
        {
            "label": "Filament Usage",
            "text": "How much PLA vs PETG have I used?"
        },
        {
            "label": "Common Failures",
            "text": "What are the most common reasons for failed prints?"
        },
        {
            "label": "Expensive Prints",
            "text": "List the top 5 most expensive prints"
        }
    ]

# Tools for the Agent
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Run a SQL SELECT query to find data about prints, costs, materials, etc. Table is 'print_jobs'. Fields: id, date, model_name, printer_name, material_type, filament_brand, weight_used_grams, print_time_hours, success_status, failure_reason, cost_usd, project_category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_database_schema",
            "description": "See table fields and types. Useful if you're not sure column names.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Log a ticket for help with printer issues or failures that need human review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short title (e.g. 'Consistent clogging on Ender 3')"},
                    "description": {"type": "string", "description": "Details of the problem"}
                },
                "required": ["title", "description"]
            }
        }
    }
]

def execute_tool(name, args, config=None):
    if name == "query_database":
        return query_db(args.get("query"))
    elif name == "get_database_schema":
        return get_schema()
    elif name == "create_support_ticket":
        return create_issue(args.get("title"), args.get("description"))
    return {"success": False, "error": "Unknown tool"}
