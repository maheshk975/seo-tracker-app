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
    return df

# ----------------------
# Streamlit App
# ----------------------
def main():
    st.title("📊 SEO Keyword & Page Tracker")

    init_db()

    # ----------------------
    # Upload Section
    # ----------------------
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

    # ----------------------
    # Keyword Explorer
    # ----------------------
    st.subheader("🔑 Keyword Explorer")
    queries_df = load_data("queries")
    if not queries_df.empty:
        keyword = st.selectbox("Choose a keyword (searchable)", sorted(queries_df["keyword"].unique()))

        history = queries_df[queries_df["keyword"] == keyword].sort_values("month")
        st.write("📈 Performance History")
        st.dataframe(history)

        st.write("🔗 Linked Pages")
        linked_pages = get_pages_for_keyword(keyword)
        if not linked_pages.empty:
            st.dataframe(linked_pages)
        else:
            st.info("No pages linked yet for this keyword.")

        st.write("📝 Notes")
        note = st.text_area("Add a note")
        if st.button("Save Note"):
            add_note(keyword, note)
            st.success("Note added!")

        notes_df = get_notes(keyword)
        if not notes_df.empty:
            st.write("📜 Notes History")
            st.dataframe(notes_df)

    # ----------------------
    # Pages Explorer
    # ----------------------
    st.subheader("🌐 Pages Explorer")
    pages_df = load_data("pages")
    if not pages_df.empty:
        url = st.selectbox("Choose a page (searchable)", sorted(pages_df["url"].unique()))

        history = pages_df[pages_df["url"] == url].sort_values("month")
        st.write("📈 Performance History")
        st.dataframe(history)

        st.write("🔗 Linked Keywords")
        linked_keywords = get_keywords_for_page(url)
        if not linked_keywords.empty:
            st.dataframe(linked_keywords)
        else:
            st.info("No keywords linked yet for this page.")

    # ----------------------
    # Mapping Section
    # ----------------------
    st.subheader("🔗 Link Keyword to Page")
    if not queries_df.empty and not pages_df.empty:
        kw = st.selectbox("Select Keyword (searchable)", sorted(queries_df["keyword"].unique()), key="map_kw")
        pgs = st.multiselect("Select one or more Pages (searchable)", sorted(pages_df["url"].unique()), key="map_pg")

        if st.button("Save Mapping from Keyword → Pages"):
            if pgs:
                for pg in pgs:
                    add_mapping(kw, pg)
                st.success(f"Linked keyword '{kw}' to pages: {', '.join(pgs)}")
            else:
                st.warning("Please select at least one page.")

    st.subheader("🔗 Link Page to Keywords")
    if not queries_df.empty and not pages_df.empty:
        pg = st.selectbox("Select Page (searchable)", sorted(pages_df["url"].unique()), key="map_pg_rev")
        kws = st.multiselect("Select one or more Keywords (searchable)", sorted(queries_df["keyword"].unique()), key="map_kw_rev")

        if st.button("Save Mapping from Page → Keywords"):
            if kws:
                for kw in kws:
                    add_mapping(kw, pg)
                st.success(f"Linked page '{pg}' to keywords: {', '.join(kws)}")
            else:
                st.warning("Please select at least one keyword.")

if __name__ == "__main__":
    main()
