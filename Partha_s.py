import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile
from datetime import datetime

# ======================================================
# 🔹 Page Setup
# ======================================================
st.set_page_config(page_title="JSC Industries – Advanced Fastener Intelligence", layout="wide")

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

def calculate_weight(product, diameter_mm, length_mm):
    density = 0.00785  # Steel density g/mm^3
    if product == "Hex Cap Screw":
        factor = 0.95
    elif product == "Heavy Hex Bolt":
        factor = 1.05
    elif product == "Heavy Hex Screw":
        factor = 1.1
    elif product == "Threaded Rod":
        factor = 1.0
    else:
        factor = 1.0
    volume = 3.1416 * (diameter_mm / 2) ** 2 * length_mm
    weight_kg = volume * density * factor / 1000
    return round(weight_kg, 4)

# ======================================================
# 🔹 Initialize Session State
# ======================================================
if "selected_section" not in st.session_state:
    st.session_state.selected_section = None

# ======================================================
# 🔹 Home Dashboard
# ======================================================
def show_home():
    st.markdown("<h1 style='text-align:center; color:#2C3E50;'>🏠 JSC Industries – Workspace</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center; color:gray;'>Click on any section to enter</h4>", unsafe_allow_html=True)
    
    sections = [
        ("📦 Product Database", "database_icon.png"),
        ("🧮 Calculations", "calculator_icon.png"),
        ("🕵️ Inspection", "inspection_icon.png"),
        ("🔬 Research & Development", "rnd_icon.png"),
        ("💬 Team Chat", "chat_icon.png"),
        ("🤖 PiU (AI Assistant)", "ai_icon.png")
    ]
    
    cols = st.columns(3)
    for idx, (title, icon) in enumerate(sections):
        with cols[idx % 3]:
            if st.button(title, key=title):
                st.session_state.selected_section = title

# ======================================================
# 🔹 Product Database Helper
# ======================================================
def generate_tds(template_file, supplier, product_name, length_val, size_val, marking, grade, filtered_df, filtered_mecert_df):
    wb = load_workbook(template_file)
    ws = wb.active
    
    ws["B2"] = supplier
    ws["B3"] = product_name
    ws["B4"] = f"Size: {size_val}, Length: {length_val}"
    ws["B5"] = marking
    ws["B6"] = grade
    
    row_start = 10
    for idx, row in filtered_df.iterrows():
        col = 1
        for val in row:
            ws.cell(row=row_start, column=col, value=val)
            col += 1
        row_start += 1
    
    row_start += 2
    for idx, row in filtered_mecert_df.iterrows():
        col = 1
        for val in row:
            ws.cell(row=row_start, column=col, value=val)
            col += 1
        row_start += 1
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(temp_file.name)
    return temp_file.name

# ======================================================
# 🔹 Section Workspaces
# ======================================================
def show_section(title):
    if title == "📦 Product Database":
        st.header("📦 Product Database")
        if df.empty and df_mechem.empty:
            st.warning("No data available.")
        else:
            st.sidebar.header("🔍 Search Panel")
            product_types = ["All"] + sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
            product_type = st.sidebar.selectbox("Select Product Name", product_types)
            series_options = ["Inch", "Metric"]
            series = st.sidebar.selectbox("Select Series", series_options)

            st.sidebar.subheader("Dimensional Specification")
            dimensional_standards = ["ASME B18.2.1"] if series == "Inch" else ["ISO"]
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

            st.sidebar.subheader("Thread Specification")
            thread_standards = ["ASME B1.1"] if series == "Inch" else ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
            thread_standard = st.sidebar.selectbox("Thread Standard", ["All"] + thread_standards)

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

            st.sidebar.subheader("ME&CERT Specification")
            mecert_standard_options = ["All"] + (sorted(df_mechem['Standard'].dropna().unique()) if not df_mechem.empty else [])
            mecert_standard = st.sidebar.selectbox("ME&CERT Standard", mecert_standard_options)
            mecert_property_options = ["All"]
            if mecert_standard != "All":
                temp_df_me = df_mechem[df_mechem['Standard'] == mecert_standard]
                if "Property class" in temp_df_me.columns:
                    mecert_property_options += sorted(temp_df_me['Property class'].dropna().unique())
            mecert_property = st.sidebar.selectbox("Property Class", mecert_property_options)

            filtered_df = df.copy()
            if product_type != "All":
                filtered_df = filtered_df[filtered_df['Product'] == product_type]
            if dimensional_standard != "All":
                filtered_df = filtered_df[filtered_df['Standards'] == dimensional_standard]
            if dimensional_size != "All":
                filtered_df = filtered_df[filtered_df['Size'] == dimensional_size]

            st.subheader(f"Found {len(filtered_df)} Bolt Records")
            st.dataframe(filtered_df)

            if thread_standard != "All":
                df_thread = load_thread_data(thread_files[thread_standard])
                if not df_thread.empty:
                    if thread_size != "All" and "Thread" in df_thread.columns:
                        df_thread = df_thread[df_thread["Thread"] == thread_size]
                    if thread_class != "All" and "Class" in df_thread.columns:
                        df_thread = df_thread[df_thread["Class"] == thread_class]
                    st.subheader(f"Thread Data: {thread_standard}")
                    st.dataframe(df_thread)

            filtered_mecert_df = df_mechem.copy()
            if mecert_standard != "All":
                filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Standard'] == mecert_standard]
            if mecert_property != "All":
                filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Property class'] == mecert_property]
            st.subheader(f"ME&CERT Records: {len(filtered_mecert_df)}")
            st.dataframe(filtered_mecert_df)

            if st.button("📥 Download All Filtered Data"):
                wb = Workbook()
                ws_dim = wb.active
                ws_dim.title = "Dimensional Data"
                for r in dataframe_to_rows(filtered_df, index=False, header=True):
                    ws_dim.append(r)
                if not df_thread.empty:
                    ws_thread = wb.create_sheet("Thread Data")
                    for r in dataframe_to_rows(df_thread, index=False, header=True):
                        ws_thread.append(r)
                if not filtered_mecert_df.empty:
                    ws_me = wb.create_sheet("ME&CERT Data")
                    for r in dataframe_to_rows(filtered_mecert_df, index=False, header=True):
                        ws_me.append(r)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                wb.save(temp_file.name)
                temp_file.close()
                with open(temp_file.name, "rb") as f:
                    st.download_button("⬇️ Download Excel", f, file_name="Filtered_Fastener_Data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif title == "🧮 Calculations":
        st.header("🧮 Engineering Calculations")
        st.subheader("Manual Weight Calculator")
        # --- Manual Calculator Code (with ft supported)
        # (Your existing manual calculator code goes here, unchanged)
        pass

    st.markdown("<hr>")
    if st.button("⬅️ Back to Home"):
        st.session_state.selected_section = None

# ======================================================
# 🔹 Main Display Logic
# ======================================================
if st.session_state.selected_section is None:
    show_home()
else:
    show_section(st.session_state.selected_section)

# ======================================================
# 🔹 Footer
# ======================================================
st.markdown("""
<hr>
<div style='text-align:center; color:gray'>
    © JSC Industries Pvt Ltd | Born to Perform
</div>
""", unsafe_allow_html=True)
