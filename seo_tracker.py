import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

DB_FILE = "seo_tracker.db"

# ----------------------
# Database Setup
# ----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            month TEXT,
            Top_pages TEXT,
            Clicks INTEGER,
            Impressions INTEGER,
            CTR REAL,
            Position REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            month TEXT,
            Top_queries TEXT,
            Clicks INTEGER,
            Impressions INTEGER,
            CTR REAL,
            Position REAL
        )
    """)
    conn.commit()
    conn.close()

# ----------------------
# Data Cleaning
# ----------------------
def clean_gsc_data(df):
    # Clean column names
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.replace("%", "", regex=False)
    
    # Handle CTR
    if "CTR" in df.columns:
        df["CTR"] = df["CTR"].astype(str).str.replace("%", "", regex=False)
        df["CTR"] = pd.to_numeric(df["CTR"], errors="coerce")
    
    return df

# ----------------------
# Save to Database
# ----------------------
def save_to_db(df, table, month):
    conn = sqlite3.connect(DB_FILE)
    df["month"] = month
    df = clean_gsc_data(df)

    try:
        df.to_sql(table, conn, if_exists="append", index=False)
        st.success(f"Saved {len(df)} rows to {table} for {month}")
    except Exception as e:
        st.error(f"Error saving to DB: {e}")
    finally:
        conn.close()

# ----------------------
# Load from Database
# ----------------------
def load_data(table):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

# ----------------------
# Streamlit App
# ----------------------
def main():
    st.title("📊 SEO Tracker - GSC Data")

    init_db()

    uploaded_file = st.file_uploader("Upload your GSC CSV file (Pages or Queries)", type=["csv"])
    month = st.text_input("Enter month (e.g., Aug, Sep, 2025)", datetime.now().strftime("%b"))

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of Uploaded File:")
        st.dataframe(df.head())

        if st.button("Save to Database"):
            if "Top pages" in df.columns:
                save_to_db(df, "pages", month)
            elif "Top queries" in df.columns:
                save_to_db(df, "queries", month)
            else:
                st.error("File must contain either 'Top pages' or 'Top queries' column.")

    if st.checkbox("Show Pages Data"):
        st.subheader("Pages Table")
        st.dataframe(load_data("pages"))

    if st.checkbox("Show Queries Data"):
        st.subheader("Queries Table")
        st.dataframe(load_data("queries"))

if __name__ == "__main__":
    main()
