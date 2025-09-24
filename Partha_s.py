import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill
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
me_chem_path = r"Mechanical and Chemical.xlsx"  # ME&CERT file in same folder as .py

# Thread databases
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
    """Simplified cylinder formula (steel)"""
    size_mm = size_in * 25.4
    length_mm = length_in * 25.4
    density = 0.00785  # g/mm³
    multiplier = 1.0
    if product == "Heavy Hex Bolt":
        multiplier = 1.05
    elif product == "Hex Cap Screw":
        multiplier = 0.95
    elif product == "Heavy Hex Screw":
        multiplier = 1.1
    vol = 3.1416 * (size_mm/2)**2 * length_mm * multiplier
    weight_kg = vol * density / 1000
    return round(weight_kg, 3)

def style_excel_sheet(ws):
    fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
    for i, row in enumerate(ws.iter_rows(min_row=2), start=2):
        if i % 2 == 0:
            for cell in row:
                cell.fill = fill
    # Auto column width
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = length + 2

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

        # -----------------------------
        # 1. Product Name & Series
        # -----------------------------
        product_types = ["All"] + sorted(df['Product'].dropna().unique())
        product_type = st.sidebar.selectbox("Select Product Name", product_types)

        series_options = ["Inch", "Metric"]
        series = st.sidebar.selectbox("Select Series", series_options)

        # -----------------------------
        # 2. Dimensional Specification
        # -----------------------------
        st.sidebar.subheader("Dimensional Specification")
        dimensional_standards = []
        if series == "Inch":
            dimensional_standards = ["ASME B18.2.1"]
        dimensional_standard = st.sidebar.selectbox("Dimensional Standard", ["All"] + dimensional_standards)

        dimensional_size_options = ["All"]
        if dimensional_standard != "All" and "Size" in df.columns:
            temp_df = df.copy()
            if product_type != "All":
                temp_df = temp_df[temp_df['Product'] == product_type]
            if dimensional_standard != "All":
                temp_df = temp_df[temp_df['Standards'] == dimensional_standard]
            dimensional_size_options += sorted(temp_df['Size'].dropna().unique(), key=size_to_float)
        dimensional_size = st.sidebar.selectbox("Dimensional Size", dimensional_size_options)

        # -----------------------------
        # 3. Thread Specification
        # -----------------------------
        st.sidebar.subheader("Thread Specification")
        thread_standards = []
        if series == "Inch":
            thread_standards = ["ASME B1.1"]
        elif series == "Metric":
            thread_standards = ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
        thread_standard = st.sidebar.selectbox("Thread Standard", ["All"] + thread_standards)

        # Thread Size & Class Dropdown
        thread_size_options = ["All"]
        thread_class_options = ["All"]
        if thread_standard != "All":
            df_thread = load_thread_data(thread_files[thread_standard])
            if not df_thread.empty:
                if "Thread" in df_thread.columns:
                    thread_size_options += sorted(df_thread['Thread'].dropna().unique())
                if "Class" in df_thread.columns:
                    thread_class_options += sorted(df_thread['Class'].dropna().unique())
        thread_size = st.sidebar.selectbox("Thread Size", thread_size_options)
        thread_class = st.sidebar.selectbox("Class", thread_class_options)

        # -----------------------------
        # 4. ME&CERT Specification
        # -----------------------------
        st.sidebar.subheader("ME&CERT Specification")
        mecert_standard_options = ["All"]
        mecert_property_options = ["All"]

        if not df_mechem.empty:
            mecert_standard_options += sorted(df_mechem['Standard'].dropna().unique())
        mecert_standard = st.sidebar.selectbox("ME&CERT Standard", mecert_standard_options)

        if mecert_standard != "All":
            temp_df_me = df_mechem[df_mechem['Standard'] == mecert_standard]
            if "Property class" in temp_df_me.columns:
                mecert_property_options = ["All"] + sorted(temp_df_me['Property class'].dropna().unique())
        mecert_property = st.sidebar.selectbox("Property Class", mecert_property_options)

        # -----------------------------
        # Filtering Main Database
        # -----------------------------
        filtered_df = df.copy()
        if product_type != "All":
            filtered_df = filtered_df[filtered_df['Product'] == product_type]
        if dimensional_standard != "All":
            filtered_df = filtered_df[filtered_df['Standards'] == dimensional_standard]
        if dimensional_size != "All":
            filtered_df = filtered_df[filtered_df['Size'] == dimensional_size]

        st.subheader(f"Found {len(filtered_df)} Bolt Records")
        st.dataframe(filtered_df)

        # Show thread data
        if thread_standard != "All":
            df_thread = load_thread_data(thread_files[thread_standard])
            if not df_thread.empty:
                if thread_size != "All" and "Thread" in df_thread.columns:
                    df_thread = df_thread[df_thread["Thread"] == thread_size]
                if thread_class != "All" and "Class" in df_thread.columns:
                    df_thread = df_thread[df_thread["Class"] == thread_class]
                st.subheader(f"Thread Data: {thread_standard}")
                st.dataframe(df_thread)

        # Show ME&CERT data
        filtered_mecert_df = df_mechem.copy()
        if mecert_standard != "All":
            filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Standard'] == mecert_standard]
        if mecert_property != "All":
            filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Property class'] == mecert_property]

        st.subheader(f"ME&CERT Records: {len(filtered_mecert_df)}")
        st.dataframe(filtered_mecert_df)

        # -----------------------------
        # Download All Data Button
        # -----------------------------
        if st.button("⬇️ Download All Filtered Data"):
            temp_wb = Workbook()
            # Dimensional
            ws_dim = temp_wb.active
            ws_dim.title = "Dimensional"
            for r in dataframe_to_rows(filtered_df, index=False, header=True):
                ws_dim.append(r)
            style_excel_sheet(ws_dim)
            # Thread
            ws_thread = temp_wb.create_sheet("Thread")
            for r in dataframe_to_rows(df_thread, index=False, header=True):
                ws_thread.append(r)
            style_excel_sheet(ws_thread)
            # ME&CERT
            ws_me = temp_wb.create_sheet("ME&CERT")
            for r in dataframe_to_rows(filtered_mecert_df, index=False, header=True):
                ws_me.append(r)
            style_excel_sheet(ws_me)

            output_file = "Filtered_Fasteners.xlsx"
            temp_wb.save(output_file)
            with open(output_file, "rb") as f:
                st.download_button("Download Excel File", f, file_name=output_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ======================================================
# 📝 Tab 2 – Manual Weight Calculator
# ======================================================
with tab2:
    st.header("Manual Weight Calculator")
    product_type = st.selectbox("Select Product Type", sorted(df['Product'].dropna().unique()))
    size_str = st.selectbox("Select Size", sorted(df['Size'].dropna().unique(), key=size_to_float))
    length_val = st.number_input("Enter Length", min_value=0.1, step=0.1)

    size_unit_manual = st.selectbox("Select Size Unit (Manual)", ["inch", "mm"], key="size_manual")
    length_unit_manual = st.selectbox("Select Length Unit (Manual)", ["inch", "mm"], key="length_manual")

    if st.button("Calculate Weight"):
        size_in = size_to_float(size_str)
        length_in = float(length_val)
        if size_unit_manual == "mm":
            size_in /= 25.4
        if length_unit_manual == "mm":
            length_in /= 25.4
        if size_in:
            weight = calculate_weight(product_type, size_in, length_in)
            st.success(f"Estimated Weight/pc: **{weight} Kg**")
        else:
            st.error("Invalid size format")

# ======================================================
# 📤 Tab 3 – Batch Excel Uploader
# ======================================================
# (No changes here, keep your existing batch uploader code)

# ======================================================
# 🔹 Footer
# ======================================================
st.markdown("""
<hr>
<div style='text-align:center; color:gray'>
    © JSC Industries Pvt Ltd | Born to Perform
</div>
""", unsafe_allow_html=True)
