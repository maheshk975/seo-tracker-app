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
    # normalize column names
    df.columns = df.columns.str.strip()
    # remove % from CTR and convert to numeric where present
    if "CTR" in df.columns:
        df["CTR"] = df["CTR"].astype(str).str.replace("%", "", regex=False)
        df["CTR"] = pd.to_numeric(df["CTR"], errors="coerce")
    return df

def save_data(df, table, month):
    conn = sqlite3.connect(DB_FILE)
    df = clean_and_prepare_df(df.copy())
    df["month"] = month

    # ensure numeric columns are numeric
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
    cursor.execute(
        "INSERT INTO notes (keyword, date, note) VALUES (?, ?, ?)",
        (keyword, datetime.now().strftime("%Y-%m-%d"), note)
    )
    conn.commit()
    conn.close()

def get_notes(keyword):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(
        "SELECT * FROM notes WHERE keyword = ? ORDER BY date DESC",
        conn,
        params=(keyword,)
    )
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
    """
    Aggregate Clicks/Impressions by summing, compute CTR and average Position.
    Returns dict with Clicks, Impressions, CTR, Position (floats/ints or NaN).
    """
    subset = df[(df[filter_col] == filter_val) & (df["month"] == month)]
    if subset.empty:
        return None

    clicks = subset["Clicks"].sum() if "Clicks" in subset.columns else 0
    impressions = subset["Impressions"].sum() if "Impressions" in subset.columns else 0
    # CTR: use (clicks / impressions * 100) if impressions > 0 else NaN
    ctr = (clicks / impressions * 100) if impressions > 0 else float("nan")
    # Position: average of position values if present
    position = subset["Position"].dropna()
    position_val = position.mean() if not position.empty else float("nan")
    return {"Clicks": int(clicks), "Impressions": int(impressions),
            "CTR": round(ctr, 2) if not math.isnan(ctr) else float("nan"),
            "Position": round(position_val, 2) if not math.isnan(position_val) else float("nan")}

def color_change(val):
    """Return CSS style string for value coloring."""
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

    # Upload Section
    st.markdown("### Upload GSC CSV (Pages or Queries)")
    uploaded_file = st.file_uploader("Drag & drop CSV (Pages or Queries)", type=["csv"])
    month = st.text_input("Enter month label (e.g., Aug, Sep 2025)", datetime.now().strftime("%b %Y"))

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            df = None

        if df is not None:
            st.write("Preview of uploaded file:")
            st.dataframe(df.head(), use_container_width=True)

            if st.button("Save to Database"):
                if "Top queries" in df.columns:
                    save_data(df.rename(columns={"Top queries": "keyword"}), "queries", month)
                    st.success("Queries saved to DB.")
                elif "Top pages" in df.columns:
                    save_data(df.rename(columns={"Top pages": "url"}), "pages", month)
                    st.success("Pages saved to DB.")
                else:
                    st.error("CSV must contain 'Top queries' or 'Top pages' column names.")

    # Load dataframes
    queries_df = load_data("queries")
    pages_df = load_data("pages")

    # Layout: two columns for explorers
    col1, col2 = st.columns(2)

    # ----------------------
    # Keyword Explorer (left)
    # ----------------------
    with col1:
        st.subheader("🔑 Keyword Explorer")
        if queries_df.empty:
            st.info("No queries data yet. Upload Queries CSV to get started.")
        else:
            kw_list = sorted(queries_df["keyword"].dropna().unique())
            keyword = st.selectbox("Choose a keyword (type to search)", kw_list)
            if keyword:
                history = queries_df[queries_df["keyword"] == keyword].sort_values("month")
                st.write("📈 Performance History")
                st.dataframe(history, use_container_width=True, height=220)

                # Linked pages
                st.write("🔗 Linked Pages")
                linked_pages = get_pages_for_keyword(keyword)
                if not linked_pages.empty:
                    st.dataframe(linked_pages, use_container_width=True, height=120)
                else:
                    st.info("No pages linked yet for this keyword.")

                # Notes section (highlight + all)
                st.write("📝 Notes")
                notes_df = get_notes(keyword)
                if not notes_df.empty:
                    notes_df = notes_df.sort_values("date", ascending=False)
                    latest_note = notes_df.iloc[0]
                    st.markdown(
                        f"""<div style="
                            background-color:#d1fae5; padding:14px; border-radius:8px; margin-bottom:12px;
                        ">
                            <b style="font-size:16px; color:#065f46;">Latest Note ({latest_note['date']}):</b><br>
                            <span style="font-size:15px; color:#064e3b; white-space:pre-wrap;">{latest_note['note']}</span>
                        </div>""",
                        unsafe_allow_html=True
                    )

                    st.write("📜 All Notes History")
                    for _, row in notes_df.iterrows():
                        st.markdown(
                            f"""<div style="background-color:#f9fafb; padding:10px; border-radius:6px; margin-bottom:8px;">
                                <b style="color:#111827;">{row['date']}</b> — <i style="color:#374151;">{row['keyword']}</i><br>
                                <span style="font-size:14px; color:#1f2937; white-space:pre-wrap;">{row['note']}</span>
                            </div>""",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No notes yet for this keyword.")

                note_text = st.text_area("Add a new note")
                if st.button("Save Note", key="save_note_kw"):
                    if note_text.strip():
                        add_note(keyword, note_text.strip())
                        st.success("Note added.")
                        st.experimental_rerun()
                    else:
                        st.warning("Note cannot be empty.")

    # ----------------------
    # Page Explorer (right)
    # ----------------------
    with col2:
        st.subheader("🌐 Pages Explorer")
        if pages_df.empty:
            st.info("No pages data yet. Upload Pages CSV to get started.")
        else:
            page_list = sorted(pages_df["url"].dropna().unique())
            page = st.selectbox("Choose a page (type to search)", page_list, key="page_select")
            if page:
                history_p = pages_df[pages_df["url"] == page].sort_values("month")
                st.write("📈 Performance History")
                st.dataframe(history_p, use_container_width=True, height=220)

                st.write("🔗 Linked Keywords")
                linked_kws = get_keywords_for_page(page)
                if not linked_kws.empty:
                    st.dataframe(linked_kws, use_container_width=True, height=120)
                else:
                    st.info("No keywords linked yet for this page.")

    # ----------------------
    # Mapping Section (below explorers)
    # ----------------------
    st.markdown("---")
    st.subheader("🔗 Keyword ↔ Page Mapping")

    if (not queries_df.empty) and (not pages_df.empty):
        left_col, right_col = st.columns(2)

        with left_col:
            st.write("Link from Keyword → Pages")
            kw_map = st.selectbox("Select Keyword", sorted(queries_df["keyword"].unique()), key="map_kw")
            pages_mult = st.multiselect("Select one or more Pages", sorted(pages_df["url"].unique()), key="map_pages")
            if st.button("Save Mapping from Keyword → Pages"):
                if pages_mult and kw_map:
                    for p in pages_mult:
                        add_mapping(kw_map, p)
                    st.success(f"Linked '{kw_map}' to {len(pages_mult)} page(s).")
                    st.experimental_rerun()
                else:
                    st.warning("Select a keyword and at least one page.")

        with right_col:
            st.write("Link from Page → Keywords")
            pg_map = st.selectbox("Select Page", sorted(pages_df["url"].unique()), key="map_pg")
            keywords_mult = st.multiselect("Select one or more Keywords", sorted(queries_df["keyword"].unique()), key="map_kws")
            if st.button("Save Mapping from Page → Keywords"):
                if keywords_mult and pg_map:
                    for k in keywords_mult:
                        add_mapping(k, pg_map)
                    st.success(f"Linked '{pg_map}' to {len(keywords_mult)} keyword(s).")
                    st.experimental_rerun()
                else:
                    st.warning("Select a page and at least one keyword.")
    else:
        st.info("For mapping, please upload both Pages and Queries data first.")

    # ----------------------
    # Comparison Tool
    # ----------------------
    st.markdown("---")
    st.subheader("📊 Compare Two Months (Keyword or Page)")

    compare_mode = st.radio("Compare for:", ["Keyword", "Page"], horizontal=True)

    if compare_mode == "Keyword":
        if queries_df.empty:
            st.info("Upload queries data to use comparison.")
        else:
            kw_cmp = st.selectbox("Select Keyword to compare", sorted(queries_df["keyword"].unique()), key="cmp_kw")
            months = sorted(queries_df["month"].dropna().unique())
            if len(months) < 2:
                st.warning("Need at least two months of data for comparison.")
            else:
                m1 = st.selectbox("First month", months, index=0, key="cmp_kw_m1")
                m2 = st.selectbox("Second month", months, index=1, key="cmp_kw_m2")
                if m1 == m2:
                    st.warning("Choose two different months.")
                else:
                    a = aggregate_metrics(queries_df, "keyword", kw_cmp, m1)
                    b = aggregate_metrics(queries_df, "keyword", kw_cmp, m2)
                    if (a is None) or (b is None):
                        st.warning("One or both months have no data for this keyword.")
                    else:
                        comp = pd.DataFrame({
                            "Metric": ["Clicks", "Impressions", "CTR", "Position"],
                            m1: [a["Clicks"], a["Impressions"], a["CTR"], a["Position"]],
                            m2: [b["Clicks"], b["Impressions"], b["CTR"], b["Position"]],
                            "Change": [b["Clicks"] - a["Clicks"],
                                       b["Impressions"] - a["Impressions"],
                                       round(b["CTR"] - a["CTR"], 2) if not (math.isnan(a["CTR"]) or math.isnan(b["CTR"])) else float("nan"),
                                       round(b["Position"] - a["Position"], 2) if not (math.isnan(a["Position"]) or math.isnan(b["Position"])) else float("nan")]
                        })
                        styled = comp.style.applymap(color_change, subset=["Change"])
                        st.dataframe(styled, use_container_width=True)

    else:  # Page mode
        if pages_df.empty:
            st.info("Upload pages data to use comparison.")
        else:
            pg_cmp = st.selectbox("Select Page to compare", sorted(pages_df["url"].unique()), key="cmp_pg")
            months_pg = sorted(pages_df["month"].dropna().unique())
            if len(months_pg) < 2:
                st.warning("Need at least two months of data for comparison.")
            else:
                m1 = st.selectbox("First month", months_pg, index=0, key="cmp_pg_m1")
                m2 = st.selectbox("Second month", months_pg, index=1, key="cmp_pg_m2")
                if m1 == m2:
                    st.warning("Choose two different months.")
                else:
                    a = aggregate_metrics(pages_df, "url", pg_cmp, m1)
                    b = aggregate_metrics(pages_df, "url", pg_cmp, m2)
                    if (a is None) or (b is None):
                        st.warning("One or both months have no data for this page.")
                    else:
                        comp = pd.DataFrame({
                            "Metric": ["Clicks", "Impressions", "CTR", "Position"],
                            m1: [a["Clicks"], a["Impressions"], a["CTR"], a["Position"]],
                            m2: [b["Clicks"], b["Impressions"], b["CTR"], b["Position"]],
                            "Change": [b["Clicks"] - a["Clicks"],
                                       b["Impressions"] - a["Impressions"],
                                       round(b["CTR"] - a["CTR"], 2) if not (math.isnan(a["CTR"]) or math.isnan(b["CTR"])) else float("nan"),
                                       round(b["Position"] - a["Position"], 2) if not (math.isnan(a["Position"]) or math.isnan(b["Position"])) else float("nan")]
                        })
                        styled = comp.style.applymap(color_change, subset=["Change"])
                        st.dataframe(styled, use_container_width=True)

if __name__ == "__main__":
    main()
