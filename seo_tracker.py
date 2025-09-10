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
# Comparison Helper
# ----------------------
def color_change(val):
    """Color numbers: green if positive, red if negative."""
    if pd.isna(val):
        return ""
    if val > 0:
        return "color: green; font-weight: bold;"
    elif val < 0:
        return "color: red; font-weight: bold;"
    return ""

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
        st.dataframe(history, use_container_width=True)

        st.write("🔗 Linked Pages")
        linked_pages = get_pages_for_keyword(keyword)
        if not linked_pages.empty:
            st.dataframe(linked_pages)
        else:
            st.info("No pages linked yet for this keyword.")

        # Notes Section
        st.write("📝 Notes")
        notes_df = get_notes(keyword)
        if not notes_df.empty:
            notes_df = notes_df.sort_values("date", ascending=False)

            # Highlight latest note
            latest_note = notes_df.iloc[0]
            st.markdown(
                f"""<div style="background-color:#d1fae5; padding:10px; border-radius:8px;">
                <b>Latest Note ({latest_note['date']}):</b><br>{latest_note['note']}
                </div>""",
                unsafe_allow_html=True
            )

            # Show older notes
            if len(notes_df) > 1:
                st.write("📜 Older Notes")
                st.dataframe(notes_df.iloc[1:], use_container_width=True, height=200)
        else:
            st.info("No notes yet for this keyword.")

        note = st.text_area("Add a new note")
        if st.button("Save Note"):
            if note.strip():
                add_note(keyword, note)
                st.success("Note added!")
            else:
                st.warning("Note cannot be empty.")

    # ----------------------
    # Pages Explorer
    # ----------------------
    st.subheader("🌐 Pages Explorer")
    pages_df = load_data("pages")
    if not pages_df.empty:
        url = st.selectbox("Choose a page (searchable)", sorted(pages_df["url"].unique()))

        history = pages_df[pages_df["url"] == url].sort_values("month")
        st.write("📈 Performance History")
        st.dataframe(history, use_container_width=True)

        st.write("🔗 Linked Keywords")
        linked_keywords = get_keywords_for_page(url)
        if not linked_keywords.empty:
            st.dataframe(linked_keywords)
        else:
            st.info("No keywords linked yet for this page.")

    # ----------------------
    # Mapping Section
    # ----------------------
    st.subheader("🔗 Link Keyword to Pages")
    if not queries_df.empty and not pages_df.empty:
        kw = st.selectbox("Select Keyword", sorted(queries_df["keyword"].unique()), key="map_kw")
        pgs = st.multiselect("Select one or more Pages", sorted(pages_df["url"].unique()), key="map_pg")

        if st.button("Save Mapping from Keyword → Pages"):
            if pgs:
                for pg in pgs:
                    add_mapping(kw, pg)
                st.success(f"Linked keyword '{kw}' to pages: {', '.join(pgs)}")
            else:
                st.warning("Please select at least one page.")

    st.subheader("🔗 Link Page to Keywords")
    if not queries_df.empty and not pages_df.empty:
        pg = st.selectbox("Select Page", sorted(pages_df["url"].unique()), key="map_pg_rev")
        kws = st.multiselect("Select one or more Keywords", sorted(queries_df["keyword"].unique()), key="map_kw_rev")

        if st.button("Save Mapping from Page → Keywords"):
            if kws:
                for kw in kws:
                    add_mapping(kw, pg)
                st.success(f"Linked page '{pg}' to keywords: {', '.join(kws)}")
            else:
                st.warning("Please select at least one keyword.")

    # ----------------------
    # Comparison Tool
    # ----------------------
    st.subheader("📊 Compare Two Months")

    compare_mode = st.radio("Compare for:", ["Keyword", "Page"])

    if compare_mode == "Keyword" and not queries_df.empty:
        kw = st.selectbox("Select Keyword", sorted(queries_df["keyword"].unique()), key="compare_kw")
        months = sorted(queries_df["month"].unique())
        m1 = st.selectbox("Select First Month", months, key="kw_m1")
        m2 = st.selectbox("Select Second Month", months, key="kw_m2")

        if m1 != m2:
            df1 = queries_df[(queries_df["keyword"] == kw) & (queries_df["month"] == m1)]
            df2 = queries_df[(queries_df["keyword"] == kw) & (queries_df["month"] == m2)]
            if not df1.empty and not df2.empty:
                comparison = pd.DataFrame({
                    "Metric": ["Clicks", "Impressions", "CTR", "Position"],
                    m1: [df1["Clicks"].values[0], df1["Impressions"].values[0], df1["CTR"].values[0], df1["Position"].values[0]],
                    m2: [df2["Clicks"].values[0], df2["Impressions"].values[0], df2["CTR"].values[0], df2["Position"].values[0]],
                    "Change": [
                        df2["Clicks"].values[0] - df1["Clicks"].values[0],
                        df2["Impressions"].values[0] - df1["Impressions"].values[0],
                        df2["CTR"].values[0] - df1["CTR"].values[0],
                        df2["Position"].values[0] - df1["Position"].values[0],
                    ]
                })
                st.dataframe(comparison.style.applymap(color_change, subset=["Change"]), use_container_width=True)
            else:
                st.warning("Data not available for one or both months.")

    elif compare_mode == "Page" and not pages_df.empty:
        pg = st.selectbox("Select Page", sorted(pages_df["url"].unique()), key="compare_pg")
        months = sorted(pages_df["month"].unique())
        m1 = st.selectbox("Select First Month", months, key="pg_m1")
        m2 = st.selectbox("Select Second Month", months, key="pg_m2")

        if m1 != m2:
            df1 = pages_df[(pages_df["url"] == pg) & (pages_df["month"] == m1)]
            df2 = pages_df[(pages_df["url"] == pg) & (pages_df["month"] == m2)]
            if not df1.empty and not df2.empty:
                comparison = pd.DataFrame({
                    "Metric": ["Clicks", "Impressions", "CTR", "Position"],
                    m1: [df1["Clicks"].values[0], df1["Impressions"].values[0], df1["CTR"].values[0], df1["Position"].values[0]],
                    m2: [df2["Clicks"].values[0], df2["Impressions"].values[0], df2["CTR"].values[0], df2["Position"].values[0]],
                    "Change": [
                        df2["Clicks"].values[0] - df1["Clicks"].values[0],
                        df2["Impressions"].values[0] - df1["Impressions"].values[0],
                        df2["CTR"].values[0] - df1["CTR"].values[0],
                        df2["Position"].values[0] - df1["Position"].values[0],
                    ]
                })
                st.dataframe(comparison.style.applymap(color_change, subset=["Change"]), use_container_width=True)
            else:
                st.warning("Data not available for one or both months.")

if __name__ == "__main__":
    main()
