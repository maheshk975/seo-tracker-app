import streamlit as st
import pandas as pd
import sqlite3
import os
import re

# ==========================
# Database Setup
# ==========================
DB_FILE = "seo_tracker.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Keywords table
    c.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            month TEXT
        )
    """)
    # Pages table
    c.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            month TEXT
        )
    """)
    # Notes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT,   -- 'keyword' or 'page'
            item_name TEXT,
            note TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

# ==========================
# Utility Functions
# ==========================
def extract_month_from_filename(filename):
    # Simple regex to capture month from filename
    match = re.search(r"(jan|feb|mar|apr|may|jun|july|aug|sept|oct|nov|dec)", filename, re.IGNORECASE)
    return match.group(0).capitalize() if match else "Unknown"

def save_keywords(df, month):
    conn = sqlite3.connect(DB_FILE)
    df["month"] = month
    df.to_sql("keywords", conn, if_exists="append", index=False)
    conn.close()

def save_pages(df, month):
    conn = sqlite3.connect(DB_FILE)
    df["month"] = month
    df.to_sql("pages", conn, if_exists="append", index=False)
    conn.close()

def get_months(table):
    conn = sqlite3.connect(DB_FILE)
    months = pd.read_sql_query(f"SELECT DISTINCT month FROM {table}", conn)["month"].tolist()
    conn.close()
    return months

def get_data(table, month):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM {table} WHERE month = ?", conn, params=(month,))
    conn.close()
    return df

def save_note(item_type, item_name, note, date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO notes (item_type, item_name, note, date) VALUES (?, ?, ?, ?)",
              (item_type, item_name, note, date))
    conn.commit()
    conn.close()

def get_notes(item_type, item_name):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT note, date FROM notes WHERE item_type = ? AND item_name = ? ORDER BY id DESC",
        conn, params=(item_type, item_name)
    )
    conn.close()
    return df

# ==========================
# Streamlit App
# ==========================
init_db()
st.title("📊 SEO Tracker Dashboard")

# File uploader
uploaded_file = st.file_uploader("Upload your GSC Excel file", type=["xlsx"])

if uploaded_file:
    month = extract_month_from_filename(uploaded_file.name)
    st.success(f"✅ Detected month: {month}")

    # Read Excel
    xls = pd.ExcelFile(uploaded_file)
    if "query" in xls.sheet_names:
        df_keywords = pd.read_excel(uploaded_file, sheet_name="query")
        save_keywords(df_keywords, month)
    if "pages" in xls.sheet_names:
        df_pages = pd.read_excel(uploaded_file, sheet_name="pages")
        save_pages(df_pages, month)

# Tabs
tab1, tab2, tab3 = st.tabs(["📌 Keywords", "🌐 Pages", "📝 Notes"])

# ==========================
# Keywords Tab
# ==========================
with tab1:
    months = get_months("keywords")
    if months:
        selected_month = st.selectbox("Select Month", months)
        df = get_data("keywords", selected_month)
        st.subheader(f"Keyword Performance - {selected_month}")
        st.dataframe(df[["keyword", "clicks", "impressions", "ctr", "position"]])
    else:
        st.info("No keyword data available yet. Upload a file to begin.")

# ==========================
# Pages Tab
# ==========================
with tab2:
    months = get_months("pages")
    if months:
        selected_month = st.selectbox("Select Month", months, key="pages_month")
        df = get_data("pages", selected_month)
        st.subheader(f"Page Performance - {selected_month}")
        st.dataframe(df[["page", "clicks", "impressions", "ctr", "position"]])
    else:
        st.info("No page data available yet. Upload a file to begin.")

# ==========================
# Notes Tab
# ==========================
with tab3:
    note_type = st.radio("Choose type", ["Keyword", "Page"])
    item_type = "keyword" if note_type == "Keyword" else "page"
    item_name = st.text_input(f"Enter {note_type} name")
    note = st.text_area("Enter your note")
    date = st.date_input("Date")
    if st.button("Save Note"):
        if item_name and note:
            save_note(item_type, item_name, note, str(date))
            st.success("Note saved successfully!")
        else:
            st.warning("Please enter both item name and note.")

    # Show notes history
    if item_name:
        st.subheader(f"Notes for {item_name}")
        notes_df = get_notes(item_type, item_name)
        if not notes_df.empty:
            st.table(notes_df)
        else:
            st.info("No notes yet for this item.")
