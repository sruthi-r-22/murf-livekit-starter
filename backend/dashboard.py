import streamlit as st
import pandas as pd
from src.db import get_dashboard_stats

# Page Configuration
st.set_page_config(
    page_title="Farm Memory Dashboard", 
    page_icon="🌾", 
    layout="wide"
)

# Title & Header
st.title("🌾 Farm Memory — Call Analytics Dashboard")
st.caption("Real-time performance metrics for #VoiceForBharat Day 8")

# Fetch metrics from backend/src/db.py
stats = get_dashboard_stats()

# Manual Refresh Button
if st.button("Refresh Data"):
    st.rerun()

st.divider()

# Core Metric Cards
col1, col2, col3 = st.columns(3)
col1.metric(label="Total Calls", value=stats["total"])
col2.metric(label="Successful Calls", value=stats["successful"])
col3.metric(label="Failed Calls", value=stats["failed"])

st.divider()

# Recent Calls Table
st.subheader("Recent Call History")
if stats["recent"]:
    df = pd.DataFrame(stats["recent"])
    # Rename columns nicely for display
    df.columns = ["Call ID", "Channel", "Status", "Reason", "Timestamp"]
    st.dataframe(df, use_container_width=True)
else:
    st.info("No calls recorded yet. Connect to the voice agent to generate your first call log!")