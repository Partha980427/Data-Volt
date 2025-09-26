import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile

# ======================================================
# 🔹 Page Setup
# ======================================================
st.set_page_config(page_title="JSC Industries – Advanced Fastener Intelligence", layout="wide")
st.markdown("<h1 style='text-align:center; color:#2C3E50;'>JSC Industries – Advanced Fastener Intelligence</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>Innovating Precision in Every Fastener</h4>", unsafe_allow_html=True)

# ======================================================
# 🔹 Load Databases
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"
me_chem_path = r"Mechanical and Chemical.xlsx"

thread_files = {
    "ASME B1.1": "ASME B1.1 New.xlsx",
    "ISO 965-2-98 Coarse": "ISO 965-2-98 Coarse.xlsx",
    "ISO 965-2-98 Fine": "ISO 965-2-98 Fine.xlsx",
}

@st.cache_data
def load_data(url):
    try:
        return pd.read_excel(url)
    except:
        if os.path.exists(local_excel_path):
            return pd.read_excel(local_excel_path)
        return pd.DataFrame()

df = load_data(url)

@st.cache_data
def load_thread_data(file):
    try:
        return pd.read_excel(file)
    except:
        return pd.DataFrame()

@st.cache_data
def load_mechem_data(file):
    if os.path.exists(file):
        return pd.read_excel(file)
    return pd.DataFrame()

df_mechem = load_mechem_data(me_chem_path)

# ======================================================
# 🔹 Helper Functions
# ======================================================
def size_to_float(size_str):
    try:
        size_str = str(size_str).strip()
        if "-" in size_str and not size_str.replace("-", "").isdigit():
            parts = size_str.split("-")
            return float(parts[0]) + float(Fraction(parts[1]))
        else:
            return float(Fraction(size_str))
    except:
        return None

def calculate_weight(product, size_in, length_in):
    size_mm = size_in * 25.4
    length_mm = length_in * 25.4
    density = 0.00785
    multiplier = 1.0
    if product == "Heavy Hex Bolt":
        multiplier = 1.05
    elif product == "Hex Cap Screw":
        multiplier = 0.95
    elif product == "Heavy Hex Screw":
        multiplier = 1.1
    vol = 3.1416 * (size_mm / 2) ** 2 * length_mm * multiplier
    weight_kg = vol * density / 1000
    return round(weight_kg, 3)

# ======================================================
# 🔹 Tabs
# ======================================================
tab1, tab2, tab3 = st.tabs(["📂 Database Search Panel", "📝 Manual Weight Calculator", "📤 Batch Excel Uploader"])

# ======================================================
# 📂 Tab 1 – Database Search Panel
# ======================================================
with tab1:
    st.header("📊 Search Panel")
    if df.empty and df_mechem.empty:
        st.warning("No data available.")
    else:
        st.sidebar.header("🔍 Search Panel")
        # ... [Tab1 code unchanged] ...

# ======================================================
# 📝 Tab 2 – Manual Weight Calculator (Modified)
# ======================================================
with tab2:
    st.header("Manual Weight Calculator")

    # 1. Select Product (Drop Down with all available products)
    product_options = sorted(df['Product'].dropna().unique())
    selected_product = st.selectbox("Select Product", product_options)

    # 2. Select Series (Drop Down Inch/Metric)
    series_options = ["Inch", "Metric"]
    selected_series = st.selectbox("Select Series", series_options, key="manual_series")

    # 3. Standard (Drop Down Based on Product and Series)
    standard_options = []
    temp_std_df = df[(df["Product"] == selected_product) & (df["Standards"].notnull())]
    if selected_series == "Inch":
        standard_options = ["ASME B18.2.1"]
    elif selected_series == "Metric" and not temp_std_df.empty:
        standard_options = sorted(temp_std_df["Standards"].dropna().unique())
    selected_standard = st.selectbox("Select Standard", standard_options)

    # 4. Size (Drop Down fetch data from database as per standard)
    size_options = []
    temp_size_df = df[(df["Product"] == selected_product) & (df["Standards"] == selected_standard)]
    if not temp_size_df.empty and "Size" in temp_size_df.columns:
        size_options = sorted(temp_size_df["Size"].dropna().unique(), key=size_to_float)
    selected_size = st.selectbox("Select Size", size_options)

    # 5. Select Length Unit
    length_unit = st.selectbox("Select Length Unit", ["inch", "mm"], key="manual_length_unit")

    # 6. Enter Length
    length_val = st.number_input("Enter Length", min_value=0.1, step=0.1)

    # 7. Diameter (Drop down Body Diameter/Pitch Diameter)
    dia_type = st.selectbox("Select Diameter Type", ["Body Diameter", "Pitch Diameter"])

    diameter_mm = None
    if dia_type == "Body Diameter":
        diameter_input = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1)
        diameter_mm = diameter_input * 25.4 if length_unit == "inch" else diameter_input

    elif dia_type == "Pitch Diameter":
        # 9. For pitch diameter, choose standard based on series
        thread_standards = []
        if selected_series == "Inch":
            thread_standards = ["ASME B1.1"]
        elif selected_series == "Metric":
            thread_standards = ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]

        selected_thread_standard = st.selectbox("Select Thread Standard for Pitch Diameter", thread_standards)

        # Fetch from "Pitch Diameter (Min)" column only
        if selected_thread_standard in thread_files:
            df_thread = load_thread_data(thread_files[selected_thread_standard])
            if not df_thread.empty and "Thread" in df_thread.columns and "Pitch Diameter (Min)" in df_thread.columns:
                pitch_row = df_thread[(df_thread["Thread"] == selected_size)]
                if not pitch_row.empty:
                    pitch_val = pitch_row["Pitch Diameter (Min)"].values[0]
                    diameter_mm = pitch_val * 25.4 if selected_series == "Inch" else pitch_val
                else:
                    st.warning("⚠️ Pitch Diameter not found for selected product and size.")

    # Convert length to mm
    length_mm = length_val * 25.4 if length_unit == "inch" else length_val

    # Weight Calculation
    if st.button("Calculate Weight"):
        if diameter_mm is None or length_mm <= 0:
            st.error("❌ Please provide valid diameter and length.")
        else:
            density = 0.00785
            weight_kg = 0
            if selected_product in ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw"]:
                multiplier = 1.0
                if selected_product == "Heavy Hex Bolt":
                    multiplier = 1.05
                elif selected_product == "Hex Cap Screw":
                    multiplier = 0.95
                elif selected_product == "Heavy Hex Screw":
                    multiplier = 1.1
                vol = 3.1416 * (diameter_mm / 2) ** 2 * length_mm * multiplier
                weight_kg = vol * density / 1000
            elif selected_product in ["Threaded Rod", "Stud"]:
                vol = 3.1416 * (diameter_mm / 2) ** 2 * length_mm
                weight_kg = vol * density / 1000

            st.success(f"✅ Estimated Weight/pc: **{round(weight_kg,3)} Kg**")

# ======================================================
# 📤 Tab 3 – Batch Excel Uploader
# ======================================================
with tab3:
    st.header("Batch Weight Calculator")
    # ... [Tab3 code unchanged] ...

# ======================================================
# 🔹 Footer
# ======================================================
st.markdown("""
<hr>
<div style='text-align:center; color:gray'>
    © JSC Industries Pvt Ltd | Born to Perform
</div>
""", unsafe_allow_html=True)
