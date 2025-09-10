import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

DB_FILE = "seo_dashboard.db"

# ----------------------
# Database Setup
# ----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            keyword TEXT,
            month TEXT,
            Clicks INTEGER,
            Impressions INTEGER,
            CTR REAL,
            Position REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            url TEXT,
            month TEXT,
            Clicks INTEGER,
            Impressions INTEGER,
            CTR REAL,
            Position REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            keyword TEXT,
            date TEXT,
            note TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keyword_page_map (
            keyword TEXT,
            url TEXT
        )
    """)

    conn.commit()
    conn.close()

# ----------------------
# Save Uploaded Data
# ----------------------
def save_data(df, table, month):
    conn = sqlite3.connect(DB_FILE)
    df["month"] = month

    if "CTR" in df.columns:
        df["CTR"] = df["CTR"].astype(str).str.replace("%", "", regex=False)
        df["CTR"] = pd.to_numeric(df["CTR"], errors="coerce")

    df.to_sql(table, conn, if_exists="append", index=False)
    conn.close()

def load_data(table):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

# ----------------------
# Notes Handling
# ----------------------
def add_note(keyword, note):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (keyword, date, note) VALUES (?, ?, ?)",
                   (keyword, datetime.now().strftime("%Y-%m-%d"), note))
    conn.commit()
    conn.close()

def get_notes(keyword):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM notes WHERE keyword = ? ORDER BY date DESC", conn, params=(keyword,))
    conn.close()
    return df

# ----------------------
# Keyword ↔ Page Mapping
# ----------------------
def add_mapping(keyword, url):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO keyword_page_map (keyword, url) VALUES (?, ?)", (keyword, url))
    conn.commit()
    conn.close()

def get_pages_for_keyword(keyword):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT url FROM keyword_page_map WHERE keyword = ?", conn, params=(keyword,))
    conn.close()
    return df

def get_keywords_for_page(url):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT keyword FROM keyword_page_map WHERE url = ?", conn, params=(url,))
    conn.close()

