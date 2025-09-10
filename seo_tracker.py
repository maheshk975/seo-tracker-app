import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import math

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
# Save / Load Data
# ----------------------
def clean_and_prepare_df(df):
    df.columns = df.columns.str.strip()
    if "CTR" in df.columns:
        df["CTR"] = df["CTR"].astype(str).str.replace("%", "", regex=False)
        df["CTR"] = pd.to_numeric(df["CTR"], errors="coerce")
    return df

def save_data(df, table, month):
    conn = sqlite3.connect(DB_FILE)
    df = clean_and_prepare_df(df.copy())
    df["month"] = month
    for col in ["Clicks", "Impressions", "CTR", "Position"]:
        if col in df.columns:
            if col in ["Clicks", "Impressions"]:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    df.to_sql(table, conn, if_exists="append", index=False)
    conn.close()

def load_data(table):
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
    except Exception:
        df = pd.DataFrame()
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
# Mapping Handling
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
# Comparison helpers
# ----------------------
def aggregate_metrics(df, filter_col, filter_val, month):
    subset = df[(df[filter_col] == filter_val) & (df["month"] == month)]
    if subset.empty:
        return None

    clicks = subset["Clicks"].sum() if "Clicks" in subset.columns else 0
    impressions = subset["Impressions"].sum() if "Impressions" in subset.columns else 0
    ctr = (clicks / impressions * 100) if impressions > 0 else float("nan")
    position = subset["Position"].dropna()
    position_val = position.mean() if not position.empty else float("nan")
    return {
        "Clicks": int(clicks),
        "Impressions": int(impressions),
        "CTR": round(ctr, 2) if not math.isnan(ctr) else float("nan"),
        "Position": round(position_val, 2) if not math.isnan(position_val) else float("nan")
    }

def color_change(val):
    try:
        v = float(val)
    except Exception:
        return ""
    if v > 0:
        return "color: green; font-weight: bold;"
    elif v < 0:
        return "color: red; font-weight: bold;"
    return ""

# ----------------------
# Streamlit App
# ----------------------
def main():
    st.set_page_config(page_title="SEO Tracker", layout="wide")
    st.title("📊 SEO Keyword & Page Tracker")

    init_db()

    # ----------------------
    # Upload Section
    # ----------------------
    st.markdown("### Upload GSC CSV (Pages or Queries)")
    uploaded_file = st.file_uploader("Upload CSV (Pages or Queries)", type=["csv"])

    months_list = ["Jan 2025", "Feb 2025", "Mar 2025", "Apr 2025", "May 2025", "Jun 2025",
                   "Jul 2025", "Aug 2025", "Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025"]
    month_choice = st.selectbox("Choose month", options=months_list, index=6)
    month = st.text_input("Or enter custom month label", value=month_choice)

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded file:")
        st.dataframe(df.head(), use_container_width=True)

        if st.button("Save to Database"):
            if "Top queries" in df.columns:
                save_data(df.rename(columns={"Top queries": "keyword"}), "queries", month)
                st.success("Queries saved.")
            elif "Top pages" in df.columns:
                save_data(df.rename(columns={"Top pages": "url"}), "pages", month)
                st.success("Pages saved.")
            else:
                st.error("CSV must contain 'Top queries' or 'Top pages'.")

    queries_df = load_data("queries")
    pages_df = load_data("pages")

    col1, col2 = st.columns(2)

    # ----------------------
    # Keyword Explorer
    # ----------------------
    with col1:
        st.subheader("🔑 Keyword Explorer")
        if queries_df.empty:
            st.info("Upload Queries CSV to see keywords.")
        else:
            kw_input = st.text_input("Type or paste keyword", "")
            keyword = kw_input.strip() if kw_input.strip() else None

            if keyword and keyword in queries_df["keyword"].values:
                history = queries_df[queries_df["keyword"] == keyword].sort_values("month")
                st.write("📈 Performance History")
                st.dataframe(history, use_container_width=True)

                st.write("🔗 Linked Pages")
                linked_pages = get_pages_for_keyword(keyword)
                if not linked_pages.empty:
                    st.dataframe(linked_pages, use_container_width=True)
                else:
                    st.info("No pages linked yet.")

                st.write("📝 Notes")
                notes_df = get_notes(keyword)
                if not notes_df.empty:
                    notes_df = notes_df.sort_values("date", ascending=False)
                    latest_note = notes_df.iloc[0]
                    st.markdown(
                        f"""<div style="background-color:#d1fae5; padding:14px; border-radius:8px; margin-bottom:14px;">
                        <b style="font-size:16px; color:#065f46;">Latest Note ({latest_note['date']}):</b><br>
                        <span style="font-size:15px; color:#064e3b; white-space:pre-wrap;">{latest_note['note']}</span>
                        </div>""",
                        unsafe_allow_html=True
                    )

                    if len(notes_df) > 1:
                        st.write("📜 Older Notes")
                        for _, row in notes_df.iloc[1:].iterrows():
                            st.markdown(
                                f"""<div style="background-color:#f9fafb; padding:10px; border-radius:6px; margin-bottom:8px;">
                                    <b>{row['date']}</b> — <i>{row['keyword']}</i><br>
                                    <span style="font-size:14px; white-space:pre-wrap;">{row['note']}</span>
                                </div>""",
                                unsafe_allow_html=True
                            )
                else:
                    st.info("No notes yet.")

                note_text = st.text_area("Add a new note")
                if st.button("Save Note"):
                    if note_text.strip():
                        add_note(keyword, note_text.strip())
                        st.success("Note added!")
                        st.rerun()

    # ----------------------
    # Page Explorer
    # ----------------------
    with col2:
        st.subheader("🌐 Pages Explorer")
        if pages_df.empty:
            st.info("Upload Pages CSV to see pages.")
        else:
            pg_input = st.text_input("Type or paste page URL", "")
            page = pg_input.strip() if pg_input.strip() else None

            if page and page in pages_df["url"].values:
                history_p = pages_df[pages_df["url"] == page].sort_values("month")
                st.write("📈 Performance History")
                st.dataframe(history_p, use_container_width=True)

                st.write("🔗 Linked Keywords")
                linked_kws = get_keywords_for_page(page)
                if not linked_kws.empty:
                    st.dataframe(linked_kws, use_container_width=True)
                else:
                    st.info("No keywords linked yet.")

    # ----------------------
    # Mapping Section
    # ----------------------
    st.markdown("---")
    st.subheader("🔗 Keyword ↔ Page Mapping")

    if (not queries_df.empty) and (not pages_df.empty):
        left_col, right_col = st.columns(2)

        with left_col:
            st.write("Link from Keyword → Pages")
            kw_map = st.text_input("Enter Keyword to map", "")
            pgs_mult = st.multiselect("Select one or more Pages", sorted(pages_df["url"].unique()))
            if st.button("Save Mapping from Keyword → Pages"):
                if kw_map and pgs_mult:
                    for pg in pgs_mult:
                        add_mapping(kw_map, pg)
                    st.success(f"Linked '{kw_map}' to {len(pgs_mult)} page(s).")
                    st.rerun()

        with right_col:
            st.write("Link from Page → Keywords")
            pg_map = st.text_input("Enter Page URL to map", "")
            kws_mult = st.multiselect("Select one or more Keywords", sorted(queries_df["keyword"].unique()))
            if st.button("Save Mapping from Page → Keywords"):
                if pg_map and kws_mult:
                    for kw in kws_mult:
                        add_mapping(kw, pg_map)
                    st.success(f"Linked '{pg_map}' to {len(kws_mult)} keyword(s).")
                    st.rerun()
    else:
        st.info("Upload both Pages and Queries data to enable mapping.")

    # ----------------------
    # Comparison Tool
    # ----------------------
    st.markdown("---")
    st.subheader("📊 Compare Two Months")

    compare_mode = st.radio("Compare for:", ["Keyword", "Page"], horizontal=True)

    if compare_mode == "Keyword" and not queries_df.empty:
        kw_cmp = st.text_input("Enter Keyword for comparison", "")
        months = sorted(queries_df["month"].dropna().unique())
        if len(months) >= 2 and kw_cmp:
            m1 = st.selectbox("First month", months, index=0, key="cmp_kw_m1")
            m2 = st.selectbox("Second month", months, index=1, key="cmp_kw_m2")
            if m1 != m2:
                a = aggregate_metrics(queries_df, "keyword", kw_cmp, m1)
                b = aggregate_metrics(queries_df, "keyword", kw_cmp, m2)
                if a and b:
                    comp = pd.DataFrame({
                        "Metric": ["Clicks", "Impressions", "CTR", "Position"],
                        m1: [a["Clicks"], a["Impressions"], a["CTR"], a["Position"]],
                        m2: [b["Clicks"], b["Impressions"], b["CTR"], b["Position"]],
                        "Change": [
                            b["Clicks"] - a["Clicks"],
                            b["Impressions"] - a["Impressions"],
                            b["CTR"] - a["CTR"],
                            b["Position"] - a["Position"],
                        ]
                    })
                    st.dataframe(comp.style.applymap(color_change, subset=["Change"]), use_container_width=True)

    elif compare_mode == "Page" and not pages_df.empty:
        pg_cmp = st.text_input("Enter Page URL for comparison", "")
        months_pg = sorted(pages_df["month"].dropna().unique())
        if len(months_pg) >= 2 and pg_cmp:
            m1 = st.selectbox("First month", months_pg, index=0, key="cmp_pg_m1")
            m2 = st.selectbox("Second month", months_pg, index=1, key="cmp_pg_m2")
            if m1 != m2:
                a = aggregate_metrics(pages_df, "url", pg_cmp, m1)
                b = aggregate_metrics(pages_df, "url", pg_cmp, m2)
                if a and b:
                    comp = pd.DataFrame({
                        "Metric": ["Clicks", "Impressions", "CTR", "Position"],
                        m1: [a["Clicks"], a["Impressions"], a["CTR"], a["Position"]],
                        m2: [b["Clicks"], b["Impressions"], b["CTR"], b["Position"]],
                        "Change": [
                            b["Clicks"] - a["Clicks"],
                            b["Impressions"] - a["Impressions"],
                            b["CTR"] - a["CTR"],
                            b["Position"] - a["Position"],
                        ]
                    })
                    st.dataframe(comp.style.applymap(color_change, subset=["Change"]), use_container_width=True)

if __name__ == "__main__":
    main()
