import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os
import logging
from dotenv import load_dotenv

from src.agent import DataAgent
from src.tools import get_sample_queries, get_schema

load_dotenv()

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
log = logging.getLogger("3DPrintAnalytics")

st.set_page_config(
    page_title="3D Print Analytics",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "data/print_analytics.db"

def get_conn():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}. Run database_setup.py first!")
        st.stop()
    return sqlite3.connect(DB_PATH)

def get_stats():
    conn = get_conn()
    stats = {}
    
    # Basic counts
    stats['total_prints'] = conn.execute("SELECT COUNT(*) FROM print_jobs").fetchone()[0]
    stats['success_count'] = conn.execute("SELECT COUNT(*) FROM print_jobs WHERE success_status = 1").fetchone()[0]
    
    if stats['total_prints'] > 0:
        stats['success_rate'] = (stats['success_count'] / stats['total_prints']) * 100
    else:
        stats['success_rate'] = 0
        
    # Totals
    res = conn.execute("""
        SELECT 
            SUM(weight_used_grams) / 1000.0,
            SUM(print_time_hours),
            SUM(cost_usd)
        FROM print_jobs
    """).fetchone()
    
    stats['total_kg'] = res[0] or 0
    stats['total_hours'] = res[1] or 0
    stats['total_cost'] = res[2] or 0
    
    # Grouped data for charts
    stats['by_material'] = pd.read_sql("SELECT material_type, count(*) as count FROM print_jobs GROUP BY material_type", conn)
    stats['by_printer'] = pd.read_sql("SELECT printer_name, AVG(success_status)*100 as success_rate FROM print_jobs GROUP BY printer_name", conn)
    
    conn.close()
    return stats

def sidebar():
    st.sidebar.title("🧊 Print Lab Stats")
    
    try:
        s = get_stats()
    except Exception as e:
        st.sidebar.error(f"DB Error: {e}")
        return

    # Key Metrics
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Total Prints", f"{s['total_prints']}")
    col2.metric("Success Rate", f"{s['success_rate']:.1f}%")
    
    col3, col4 = st.sidebar.columns(2)
    col3.metric("Filament (kg)", f"{s['total_kg']:.1f}")
    col4.metric("Print Hours", f"{s['total_hours']:.0f}")
    
    st.sidebar.metric("Total Material Cost", f"${s['total_cost']:,.2f}")
    
    st.sidebar.markdown("---")
    
    # Mini Charts
    st.sidebar.subheader("Materials Used")
    if not s['by_material'].empty:
        fig = px.pie(s['by_material'], values='count', names='material_type', hole=0.4)
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
        st.sidebar.plotly_chart(fig, use_container_width=True)
        
    st.sidebar.subheader("Printer Reliability")
    if not s['by_printer'].empty:
        fig2 = px.bar(s['by_printer'], x='success_rate', y='printer_name', orientation='h')
        fig2.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), xaxis_title="Success %", yaxis_title=None)
        st.sidebar.plotly_chart(fig2, use_container_width=True)

    # Queries
    st.sidebar.markdown("---")
    st.sidebar.subheader("Quick Queries")
    
    queries = get_sample_queries()
    for q in queries:
        if st.sidebar.button(q['label'], key=q['label']):
            st.session_state.prompt_input = q['text']

def init_agent():
    if "agent" not in st.session_state:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            st.warning("Needs OPENAI_API_KEY to run agent.")
            return None
            
        config = {
            "db_path": DB_PATH,
            "github_token": os.environ.get("GITHUB_TOKEN")
        }
        st.session_state.agent = DataAgent(key, config=config)
        log.info("Agent started")
    return st.session_state.agent

def chat_interface():
    st.title("🖨️ 3D Printing Analytics Assistant")
    st.markdown("Ask about your print history, failures, costs, or printer stats.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant", 
            "content": "Hey! I'm your print lab assistant. Ask me anything about your 3D printing logs. \n\nExample: 'What's my failure rate with ABS?' or 'How much did I spend on filament last month?'"
        }]

    # Handle button clicks from sidebar
    if "prompt_input" in st.session_state:
        user_input = st.session_state.prompt_input
        del st.session_state.prompt_input
    else:
        user_input = st.chat_input("Ask about your prints...")

    # Render history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        agent = init_agent()
        if agent:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing print logs..."):
                    try:
                        resp = agent.chat_sync(user_input)
                        st.markdown(resp)
                        st.session_state.messages.append({"role": "assistant", "content": resp})
                    except Exception as e:
                        st.error(f"Agent crashed: {e}")
                        log.error(f"Agent failed: {e}")

    # Utilities
    with st.expander("🛠️ Tools & Settings"):
        c1, c2 = st.columns(2)
        if c1.button("Clear Chat"):
            st.session_state.messages = []
            if "agent" in st.session_state:
                st.session_state.agent.reset()
            st.rerun()
            
        if c2.button("Report Issue"):
            st.session_state.messages.append({
                "role": "user", 
                "content": "I need help debugging a print failure, please create a support ticket."
            })
            st.rerun()

def main():
    sidebar()
    chat_interface()

if __name__ == "__main__":
    main()
