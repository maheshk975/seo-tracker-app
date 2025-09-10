# seo_tracker.py
import streamlit as st
import pandas as pd
import sqlite3
import io
import re
from datetime import datetime

DB_FILE = "seo_tracker.db"

# -------------------------
# DB init
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            month TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            month TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT,
            item_name TEXT,
            note TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

# -------------------------
# Helpers: find column / sheet
# -------------------------
def extract_month_from_filename(filename):
    filename = filename.lower()
    months = [
        ("jan", "Jan"), ("feb", "Feb"), ("mar", "Mar"), ("apr", "Apr"),
        ("may", "May"), ("jun", "Jun"), ("jul", "Jul"), ("aug", "Aug"),
        ("sep", "Sep"), ("sept", "Sep"), ("oct", "Oct"), ("nov", "Nov"), ("dec", "Dec")
    ]
    for token, label in months:
        if token in filename:
            return label
    return datetime.now().strftime("%b")  # fallback short name

def find_sheet_name(sheet_names, candidates):
    # case-insensitive search, allow partial match
    sheet_names_clean = [s.strip() for s in sheet_names]
    for cand in candidates:
        for sheet in sheet_names_clean:
            if cand.lower() == sheet.lower():
                return sheet
    # partial contains
    for cand in candidates:
        for sheet in sheet_names_clean:
            if cand.lower() in sheet.lower():
                return sheet
    return None

def find_column(df_cols, candidates):
    cols = [c.strip() for c in df_cols]
    for cand in candidates:
        for c in cols:
            if cand.lower() == c.lower():
                return c
    for cand in candidates:
        for c in cols:
            if cand.lower() in c.lower():
                return c
    return None

def clean_numeric_series(s):
    # remove commas, percent, spaces
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.replace("%", "").str.strip(), errors='coerce')

def standardize_sheet(df, kind):
    """
    kind: "keyword" or "page"
    Returns standardized DataFrame with columns: name, clicks, impressions, ctr, position
    """
    # normalize column names in memory
    cols_orig = list(df.columns)
    # Candidates
    if kind == "keyword":
        name_cands = ["query", "keyword", "queries", "top queries", "top query"]
    else:
        name_cands = ["page", "url", "link", "page url", "page_url", "page/path"]

    clicks_cands = ["clicks", "click"]
    impr_cands = ["impressions", "impr", "impression"]
    ctr_cands = ["ctr", "click-through rate", "click through rate"]
    pos_cands = ["position", "avg position", "average position"]

    name_col = find_column(cols_orig, name_cands)
    clicks_col = find_column(cols_orig, clicks_cands)
    impr_col = find_column(cols_orig, impr_cands)
    ctr_col = find_column(cols_orig, ctr_cands)
    pos_col = find_column(cols_orig, pos_cands)

    # Debug mapping info
    mapping = {
        "name_col": name_col,
        "clicks_col": clicks_col,
        "impr_col": impr_col,
        "ctr_col": ctr_col,
        "pos_col": pos_col
    }

    # Build standardized df
    std = pd.DataFrame()
    if name_col:
        std["name"] = df[name_col].astype(str).str.strip()
    else:
        std["name"] = None

    if clicks_col:
        std["clicks"] = clean_numeric_series(df[clicks_col]).fillna(0).astype(int)
    else:
        std["clicks"] = 0

    if impr_col:
        std["impressions"] = clean_numeric_series(df[impr_col]).fillna(0).astype(int)
    else:
        std["impressions"] = 0

    if ctr_col:
        std["ctr"] = clean_numeric_series(df[ctr_col]).fillna(0.0)
    else:
        std["ctr"] = 0.0

    if pos_col:
        std["position"] = clean_numeric_series(df[pos_col]).fillna(0.0)
    else:
        std["position"] = 0.0

    # drop rows with empty name
    std = std[std["name"].notna()].copy()
    std["name"] = std["name"].str.strip()
    return std, mapping

# -------------------------
# Save functions
# -------------------------
def save_to_db(std_df, month, table):
    if std_df.empty:
        return 0
    conn = sqlite3.connect(DB_FILE)
    std_df = std_df.copy()
    std_df["month"] = month
    std_df = std_df.rename(columns={"name": "name", "clicks": "clicks", "impressions": "impressions", "ctr": "ctr", "position": "position"})
    std_df.to_sql(table, conn, if_exists="append", index=False)
    conn.close()
    return len(std_df)

# -------------------------
# Read existing months
# -------------------------
def get_months(table):
    conn = sqlite3.connect(DB_FILE)
    try:
        months = pd.read_sql_query(f"SELECT DISTINCT month FROM {table} ORDER BY month", conn)
        months_list = months['month'].tolist()
    except Exception:
        months_list = []
    conn.close()
    return months_list

def get_data(table, month):
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table} WHERE month = ?", conn, params=(month,))
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def add_note(item_type, item_name, note_text, date_str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO notes (item_type, item_name, note, date) VALUES (?, ?, ?, ?)",
              (item_type, item_name, note_text, date_str))
    conn.commit()
    conn.close()

def get_notes(item_type, item_name):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT date, note FROM notes WHERE item_type = ? AND item_name = ? ORDER BY id DESC",
                           conn, params=(item_type, item_name))
    conn.close()
    return df

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="SEO Tracker", layout="wide")
init_db()
st.title("📊 SEO Tracker Dashboard (robust reader + debug)")

uploaded_file = st.file_uploader("Upload your GSC Excel file (single file with Keywords & Pages tabs)", type=["xlsx"])

debug_info = {}

if uploaded_file:
    # read bytes once
    data = uploaded_file.getvalue()
    xls = pd.ExcelFile(io.BytesIO(data))
    sheet_names = [s for s in xls.sheet_names]
    debug_info["sheet_names_detected"] = sheet_names

    # detect month
    month = extract_month_from_filename(uploaded_file.name)
    st.success(f"Detected month: {month}")

    # Try to find keyword sheet (common names)
    kw_sheet = find_sheet_name(sheet_names, ["keywords", "query", "queries", "top queries", "top queries "])
    page_sheet = find_sheet_name(sheet_names, ["pages", "page", "top pages", "top pages "])

    debug_info["keyword_sheet_found"] = kw_sheet
    debug_info["page_sheet_found"] = page_sheet

    # Read and standardize keywords
    if kw_sheet:
        df_kw = pd.read_excel(io.BytesIO(data), sheet_name=kw_sheet)
        std_kw, mapping_kw = standardize_sheet(df_kw, "keyword")
        debug_info["keyword_mapping"] = mapping_kw
        debug_info["keyword_preview_raw"] = df_kw.head().to_dict(orient="records")
        debug_info["keyword_preview_clean"] = std_kw.head().to_dict(orient="records")
        saved_count = save_to_db(std_kw, month, "keywords")
        st.info(f"Keywords: {saved_count} rows saved to DB.")
    else:
        st.warning("No keyword sheet found automatically. Upload file with a sheet named 'Keywords' or similar.")
    # Read and standardize pages
    if page_sheet:
        df_page = pd.read_excel(io.BytesIO(data), sheet_name=page_sheet)
        std_page, mapping_page = standardize_sheet(df_page, "page")
        debug_info["page_mapping"] = mapping_page
        debug_info["page_preview_raw"] = df_page.head().to_dict(orient="records")
        debug_info["page_preview_clean"] = std_page.head().to_dict(orient="records")
        saved_count_p = save_to_db(std_page, month, "pages")
        st.info(f"Pages: {saved_count_p} rows saved to DB.")
    else:
        st.warning("No pages sheet found automatically. Upload file with a sheet named 'Pages' or similar.")

# -------------------------
# Tabs for UI
# -------------------------
tab1, tab2, tab3 = st.tabs(["🔑 Keywords", "📄 Pages", "📝 Notes"])

with tab1:
    months = get_months("keywords")
    if months:
        selected_month = st.selectbox("Select month", months, index=max(0, len(months)-1))
        df = get_data("keywords", selected_month)
        if not df.empty:
            st.write(f"Keyword performance for {selected_month}")
            st.dataframe(df[["name","clicks","impressions","ctr","position"]])
        else:
            st.info("No keyword rows for this month.")
    else:
        st.info("No keyword data in database yet.")

with tab2:
    months_p = get_months("pages")
    if months_p:
        selected_month_p = st.selectbox("Select month for pages", months_p, index=max(0, len(months_p)-1), key="pages_month")
        dfp = get_data("pages", selected_month_p)
        if not dfp.empty:
            st.write(f"Page performance for {selected_month_p}")
            st.dataframe(dfp[["name","clicks","impressions","ctr","position"]])
        else:
            st.info("No page rows for this month.")
    else:
        st.info("No page data in database yet.")

with tab3:
    st.subheader("Add a note")
    note_type = st.radio("Note type", ["Keyword","Page"])
    item = st.text_input("Enter exact Keyword or Page (full URL) to link note")
    note_text = st.text_area("Note")
    date = st.date_input("Date")
    if st.button("Save note"):
        if item.strip() and note_text.strip():
            itype = "keyword" if note_type=="Keyword" else "page"
            add_note(itype, item.strip(), note_text.strip(), str(date))
            st.success("Note saved.")
        else:
            st.warning("Please enter item name and note.")
    if item.strip():
        notes_df = get_notes("keyword" if note_type=="Keyword" else "page", item.strip())
        if not notes_df.empty:
            st.table(notes_df)
        else:
            st.info("No notes for this item yet.")

# -------------------------
# Debug area (shows what was read)
# -------------------------
st.markdown("---")
st.header("Debug Info (what the app read)")
if uploaded_file:
    st.write("Detected sheet names:", debug_info.get("sheet_names_detected", []))
    st.write("Keyword sheet:", debug_info.get("keyword_sheet_found"))
    st.write("Page sheet:", debug_info.get("page_sheet_found"))
    st.write("Keyword mapping (columns found):", debug_info.get("keyword_mapping"))
    st.write("Page mapping (columns found):", debug_info.get("page_mapping"))
    st.write("Keyword raw preview (first rows):")
    st.write(debug_info.get("keyword_preview_raw"))
    st.write("Keyword cleaned preview (first rows):")
    st.write(debug_info.get("keyword_preview_clean"))
    st.write("Page raw preview (first rows):")
    st.write(debug_info.get("page_preview_raw"))
    st.write("Page cleaned preview (first rows):")
    st.write(debug_info.get("page_preview_clean"))
else:
    st.write("Upload a file to see debug info here.")
