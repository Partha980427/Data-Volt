import streamlit as st
import pandas as pd
import openpyxl
from fractions import Fraction
import math

# ======================================================
# 📂 Load Database from GitHub
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"

@st.cache_data
def load_data(url):
    return pd.read_excel(url)

df = load_data(url)

st.title("🔩 Bolt & Rod Search + Weight Calculator")

if df.empty:
    st.warning("No data available.")
    st.stop()

# ======================================================
# 🔹 Fractional size parser
# ======================================================
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

# ======================================================
# 🔹 Weight calculation function
# ======================================================
def calculate_weight(product, size_str, length_mm):
    dia_mm = parse_size_in_inches(size_str) * 25.4  # inches -> mm
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
# 🔹 Sidebar Filters for Database
# ======================================================
st.sidebar.header("Search Filters")

standards_options = ["All"] + sorted(df['Standards'].dropna().unique())
standard = st.sidebar.selectbox("Select Standard", standards_options)

size_options = ["All"] + sorted(df['Size'].dropna().unique(), key=parse_size_in_inches)
size = st.sidebar.selectbox("Select Size", size_options)

product_options = ["All"] + sorted(df['Product'].dropna().unique())
product = st.sidebar.selectbox("Select Product", product_options)

# Filter database
filtered_df = df.copy()
if standard != "All":
    filtered_df = filtered_df[filtered_df["Standards"] == standard]
if size != "All":
    filtered_df = filtered_df[filtered_df["Size"] == size]
if product != "All":
    filtered_df = filtered_df[filtered_df["Product"] == product]

st.subheader(f"Found {len(filtered_df)} matching items")
st.dataframe(filtered_df)

# ======================================================
# ⚖️ Manual Weight Calculator
# ======================================================
st.header("⚖️ Manual Weight Calculator")

calc_product = st.selectbox("Select Product for Weight", product_options[1:])
calc_size = st.selectbox("Select Size for Weight", size_options[1:])
calc_length = st.number_input("Enter Length (mm)", min_value=1, value=100)

if st.button("Calculate Weight"):
    result = calculate_weight(calc_product, calc_size, calc_length)
    if result is not None:
        st.success(f"Estimated Weight/pc: {result} kg")
    else:
        st.error("No formula available for this combination.")

# ======================================================
# 📂 Batch Excel Update via File Upload
# ======================================================
st.header("📂 Batch Excel Update via File Upload")

product_type = st.selectbox(
    "Select Product Type for Batch Update",
    ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw"]
)

weight_col_name = st.text_input("Enter column name to write Weight/pc (Kg):", "Weight/pc (Kg)")
weight_col_index = st.number_input(
    "Enter column index to write Weight/pc (Kg) (if not exist, will be created at this position)",
    min_value=1, value=3
)

uploaded_files = st.file_uploader(
    "Upload Excel file(s) from folder",
    type=["xlsx"],
    accept_multiple_files=True
)

if st.button("Update Weights in Uploaded Excel"):
    if not uploaded_files:
        st.warning("Please upload at least one Excel file.")
    else:
        updated_files = []
        for uploaded_file in uploaded_files:
            wb = openpyxl.load_workbook(uploaded_file)
            ws = wb.active

            # Auto-detect Size and Length columns
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

            # Save updated Excel (overwrite)
            wb.save(uploaded_file.name)
            updated_files.append(uploaded_file.name)

        st.success(f"Updated weights in {len(updated_files)} file(s): {updated_files}")
