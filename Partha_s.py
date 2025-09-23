import streamlit as st
import pandas as pd
import openpyxl
from fractions import Fraction
import math
from io import BytesIO
import os

# ======================================================
# 🌟 Page Config & Styling
# ======================================================
st.set_page_config(page_title="🔩 Bolt & Rod Pro", layout="wide")

st.markdown("""
    <style>
        .main {
            background-color: #f8f9fa;
        }
        h1, h2, h3 {
            color: #1a1a2e;
            font-family: 'Helvetica Neue', sans-serif;
        }
        .stButton>button {
            background-color: #1a73e8;
            color: white;
            border-radius: 8px;
            padding: 8px 20px;
            font-size: 16px;
        }
        .stButton>button:hover {
            background-color: #1558b0;
            color: #f1f1f1;
        }
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ======================================================
# 🔹 Header Section
# ======================================================
st.title("🔩 Bolt & Rod Professional App")
st.subheader("Smart Database Search + Automatic Weight Calculation")
st.markdown("<h4 style='text-align:center; color:gray;'>JSC Industries Pvt Ltd | Born to Perform</h4>", unsafe_allow_html=True)

# ======================================================
# 🔹 Load Bolt Database (Google Sheets link or local path)
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

@st.cache_data
def load_data(url):
    return pd.read_excel(url)

try:
    df = load_data(url)
except:
    if os.path.exists(local_excel_path):
        df = pd.read_excel(local_excel_path)
    else:
        df = pd.DataFrame()

# ======================================================
# 🔹 Helper Functions
# ======================================================
def size_to_float(size_str):
    try:
        if "-" in str(size_str):
            parts = str(size_str).split("-")
            return float(parts[0]) + float(Fraction(parts[1]))
        else:
            return float(Fraction(str(size_str)))
    except:
        return float('inf')

def parse_size_in_inches(size):
    if isinstance(size, (int, float)):
        return float(size)
    s = str(size).strip()
    try:
        if "-" in s:
            whole, frac = s.split("-")
            return float(whole) + float(Fraction(frac))
        else:
            return float(Fraction(s))
    except:
        return None

def calculate_weight(product, size_str, length_mm):
    dia_mm = parse_size_in_inches(size_str) * 25.4  # inch → mm
    density = 0.00785  # g/mm³ steel

    if product == "Hex Bolt":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm
    elif product == "Heavy Hex Bolt":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm * 1.05
    elif product == "Hex Cap Screw":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm * 0.95
    elif product == "Heavy Hex Screw":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm * 1.1
    else:
        return None

    return round(vol * density / 1000, 3)  # kg

# ======================================================
# 📌 Tabs
# ======================================================
tab1, tab2 = st.tabs(["📊 Database Search", "⚖️ Weight Calculator"])

# ======================================================
# 📊 TAB 1: Database Search
# ======================================================
with tab1:
    st.header("📊 Search Bolts in Database")

    if df.empty:
        st.warning("⚠️ Database not loaded. Check your Google Sheets or local path.")
    else:
        st.sidebar.header("Search Filters")

        standards_options = ["All"] + sorted(df['Standards'].dropna().unique())
        standard = st.sidebar.selectbox("Select Standard", standards_options)

        size_options = ["All"] + sorted(df['Size'].dropna().unique(), key=size_to_float)
        size = st.sidebar.selectbox("Select Size", size_options)

        product_options = ["All"] + sorted(df['Product'].dropna().unique())
        product = st.sidebar.selectbox("Select Product", product_options)

        filtered_df = df.copy()
        if standard != "All":
            filtered_df = filtered_df[filtered_df['Standards'] == standard]
        if size != "All":
            filtered_df = filtered_df[filtered_df['Size'] == size]
        if product != "All":
            filtered_df = filtered_df[filtered_df['Product'] == product]

        st.subheader(f"Found {len(filtered_df)} matching items")
        st.dataframe(filtered_df, use_container_width=True)

        st.download_button(
            "📥 Download Filtered Results (CSV)",
            filtered_df.to_csv(index=False),
            file_name="filtered_bolts.csv",
            mime="text/csv"
        )

# ======================================================
# ⚖️ TAB 2: Weight Calculator
# ======================================================
with tab2:
    st.header("⚖️ Automatic Weight Calculator")

    product_type = st.selectbox(
        "Select Product Type",
        ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw"]
    )

    weight_col_name = st.text_input("Enter column name for Weight/pc (Kg):", "Weight/pc (Kg)")
    weight_col_index = st.number_input(
        "Enter column index to write Weight/pc (Kg) (numeric, e.g., 3 = C column)",
        min_value=1, value=3
    )

    uploaded_files = st.file_uploader(
        "📤 Upload Excel file(s) to update weights",
        type=["xlsx"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            wb = openpyxl.load_workbook(uploaded_file)
            ws = wb.active

            headers = {cell.value: idx for idx, cell in enumerate(ws[1], 1)}
            size_cols = [name for name in headers if "size" in str(name).lower()]
            length_cols = [name for name in headers if "length" in str(name).lower()]

            if not size_cols or not length_cols:
                st.warning(f"{uploaded_file.name} missing Size or Length column. Skipping.")
                continue

            size_col_index_detected = headers[size_cols[0]]
            length_col_index_detected = headers[length_cols[0]]

            # Add weight column if not exist
            if ws.cell(row=1, column=weight_col_index).value != weight_col_name:
                ws.insert_cols(weight_col_index)
                ws.cell(row=1, column=weight_col_index, value=weight_col_name)

            # Calculate weight row by row
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                size_val = row[size_col_index_detected - 1].value
                length_val = row[length_col_index_detected - 1].value
                if size_val is not None and length_val is not None:
                    row[weight_col_index - 1].value = calculate_weight(product_type, size_val, length_val)

            # Save updated Excel
            output = BytesIO()
            wb.save(output)
            output.seek(0)

            st.success(f"✅ Weights updated for {uploaded_file.name}")
            st.download_button(
                label=f"📥 Download Updated {uploaded_file.name}",
                data=output,
                file_name=f"updated_{uploaded_file.name}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ======================================================
# 🔻 Footer
# ======================================================
st.markdown("""
    <hr>
    <div style='text-align:center; color:gray'>
        © JSC Industries Pvt Ltd | Born to Perform
    </div>
""", unsafe_allow_html=True)
