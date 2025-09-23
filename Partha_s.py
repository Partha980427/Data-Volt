import streamlit as st
import pandas as pd
import os
from fractions import Fraction
import math

# ======================================================
# 📂 Load Data
# ======================================================

# Google Sheets direct download link
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"

# Local path for backup Excel
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

@st.cache_data
def load_data(url):
    return pd.read_excel(url)

df = load_data(url)

st.title("🔩 Bolt & Rod Search App")
st.write("Search ASME B18.2.1 Hex Bolts and Heavy Hex Bolts by Standard, Size, and Product")

if df.empty:
    st.warning("No data available.")
    st.stop()

# ======================================================
# 🔍 Sidebar Filters
# ======================================================

st.sidebar.header("Search Filters")

# --- Standards ---
standards_options = ["All"] + sorted(df['Standards'].dropna().unique())
standard = st.sidebar.selectbox("Select Standard", standards_options)

# --- Size (supports fractions like 1/2, 1-1/2) ---
def size_to_float(size_str):
    try:
        if "-" in str(size_str):
            parts = str(size_str).split("-")
            return float(parts[0]) + float(Fraction(parts[1]))
        else:
            return float(Fraction(str(size_str)))
    except:
        return float("inf")

size_options = ["All"] + sorted(df['Size'].dropna().unique(), key=size_to_float)
size = st.sidebar.selectbox("Select Size", size_options)

# --- Product ---
product_options = ["All"] + sorted(df['Product'].dropna().unique())
product = st.sidebar.selectbox("Select Product", product_options)

# ======================================================
# 📊 Filter & Display
# ======================================================

filtered_df = df.copy()
if standard != "All":
    filtered_df = filtered_df[filtered_df["Standards"] == standard]
if size != "All":
    filtered_df = filtered_df[filtered_df["Size"] == size]
if product != "All":
    filtered_df = filtered_df[filtered_df["Product"] == product]

st.subheader(f"Found {len(filtered_df)} matching items")
st.dataframe(filtered_df)

# Download Filtered Data
st.download_button(
    "Download Filtered Results as CSV",
    filtered_df.to_csv(index=False),
    file_name="filtered_bolts.csv",
    mime="text/csv",
)

# Download Original Excel
if os.path.exists(local_excel_path):
    with open(local_excel_path, "rb") as f:
        st.download_button(
            "Download Original Excel",
            f,
            file_name="ASME_B18.2.1_Hex_Bolt_and_Heavy_Hex_Bolt.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.warning("Original Excel file not found at local path.")

# ======================================================
# ⚖️ Weight Calculator
# ======================================================

st.header("⚖️ Weight Calculator")

# --- Formula Function (replace with actual formulas later) ---
def calculate_weight(product, size, length):
    try:
        # Handle size conversion (fraction → float, inch → mm, metric M sizes)
        if isinstance(size, str):
            try:
                dia = float(Fraction(size)) * 25.4  # inch → mm
            except:
                if size.startswith("M"):
                    dia = float(size.replace("M", ""))  # metric
                else:
                    dia = float(size)
        else:
            dia = float(size)

        density = 0.00785  # g/mm³ steel

        if product == "Hex Bolt":
            vol = math.pi * (dia / 2) ** 2 * length
            weight = vol * density / 1000
        elif product == "Heavy Hex Bolt":
            vol = math.pi * (dia / 2) ** 2 * length * 1.05
            weight = vol * density / 1000
        elif product == "Hex Cap Screw":
            vol = math.pi * (dia / 2) ** 2 * length * 0.95
            weight = vol * density / 1000
        elif product == "Heavy Hex Screw":
            vol = math.pi * (dia / 2) ** 2 * length * 1.1
            weight = vol * density / 1000
        else:
            weight = None

        return round(weight, 3)

    except Exception:
        return None

# --- User Inputs ---
calc_product = st.selectbox("Select Product for Weight", product_options[1:])
calc_size = st.selectbox("Select Size for Weight", size_options[1:])
calc_length = st.number_input("Enter Length (mm)", min_value=1, value=100)

# --- Calculate & Show ---
if st.button("Calculate Weight"):
    result = calculate_weight(calc_product, calc_size, calc_length)
    if result:
        st.success(f"Estimated Weight/pc: {result} kg")
    else:
        st.error("No formula available for this combination.")
