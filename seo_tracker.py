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

    # Store keyword performance
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

    # Store page performance
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

    # Store notes for each keyword
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            keyword TEXT,
            date TEXT,
            note TEXT
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

    # Clean CTR column
    if "CTR" in df.columns:
        df["CTR"] = df["CTR"].astype(str).str.replace("%", "", regex=False)
        df["CTR"] = pd.to_numeric(df["CTR"], errors="coerce")

    df.to_sql(table, conn, if_exists="append", index=False)
    conn.close()


# ----------------------
# Load Data
# ----------------------
def load_data(table):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df


# ----------------------
# Add Note
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
# Streamlit App
# ----------------------
def main():
    st.title("📊 SEO Keyword & Page Tracker")

    init_db()

    # Upload data
    uploaded_file = st.file_uploader("Upload GSC CSV (Pages or Queries)", type=["csv"])
    month = st.text_input("Enter month (e.g., Aug, Sep)", datetime.now().strftime("%b"))

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview:", df.head())

        if st.button("Save to Database"):
            if "Top queries" in df.columns:
                save_data(df.rename(columns={"Top queries": "keyword"}), "queries", month)
                st.success("Queries saved.")
            elif "Top pages" in df.columns:
                save_data(df.rename(columns={"Top pages": "url"}), "pages", month)
                st.success("Pages saved.")
            else:
                st.error("CSV must contain 'Top queries' or 'Top pages'.")

    # Keyword Explorer
    st.subheader("🔑 Keyword Explorer")
    queries_df = load_data("queries")
    if not queries_df.empty:
        keyword_list = sorted(queries_df["keyword"].unique())
        keyword = st.selectbox("Choose a keyword", keyword_list)

        # Show history
        history = queries_df[queries_df["keyword"] == keyword].sort_values("month")
        st.write("📈 Performance History")
        st.dataframe(history)

        # Notes section
        st.write("📝 Notes")
        note = st.text_area("Add a note")
        if st.button("Save Note"):
            add_note(keyword, note)
            st.success("Note added!")

        notes_df = get_notes(keyword)
        if not notes_df.empty:
            st.write("📜 Notes History")
            st.dataframe(notes_df)

    # Pages Explorer
    st.subheader("🌐 Pages Explorer")
    pages_df = load_data("pages")
    if not pages_df.empty:
        st.dataframe(pages_df)


if __name__ == "__main__":
    main()
