import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile

# ======================================================
# 🔹 Page Setup
# ======================================================
st.set_page_config(page_title="JSC Industries – Advanced Fastener Intelligence", layout="wide")
st.markdown("**App Version: 2.6 – ISO 4014 Metric Standard Fully Integrated ✅**")

# ======================================================
# 🔹 Paths & Files
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"
me_chem_path = r"Mechanical and Chemical.xlsx"

thread_files = {
    "ASME B1.1": "ASME B1.1 New.xlsx",
    "ISO 965-2-98 Coarse": "ISO 965-2-98 Coarse.xlsx",
    "ISO 965-2-98 Fine": "ISO 965-2-98 Fine.xlsx",
}

iso4014_file_url = "https://github.com/Partha980427/Data-Volt/raw/main/ISO%204014%20Hex%20Bolt.xlsx"

# ======================================================
# 🔹 Data Loading
# ======================================================
@st.cache_data
def load_excel_file(path_or_url):
    try:
        return pd.read_excel(path_or_url)
    except Exception as e:
        st.warning(f"Failed to load {path_or_url}: {e}")
        return pd.DataFrame()

df = load_excel_file(url) if url else load_excel_file(local_excel_path)
df_mechem = load_excel_file(me_chem_path)
df_iso4014 = load_excel_file(iso4014_file_url)

# ======================================================
# 🔹 ISO 4014 Mapping & Grade Column
# ======================================================
if not df_iso4014.empty:
    df_iso4014['Product'] = "Hex Bolt"
    df_iso4014['Standards'] = "ISO-4014-2011"
    if 'Grade' not in df_iso4014.columns:
        df_iso4014['Grade'] = "A"  # Default grade, can be filtered later

@st.cache_data
def load_thread_data(file):
    if os.path.exists(file):
        return pd.read_excel(file)
    else:
        st.warning(f"Thread file {file} not found!")
        return pd.DataFrame()

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
    density = 0.00785  # g/mm^3
    V_shank = 3.1416 * (diameter_mm / 2) ** 2 * length_mm
    head_volume = 0
    product_lower = product.lower()
    if "hex cap" in product_lower:
        a = 1.5 * diameter_mm
        h = 0.8 * diameter_mm
        head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
    elif "heavy hex" in product_lower:
        a = 2 * diameter_mm
        h = 1.2 * diameter_mm
        head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
    elif "socket head" in product_lower or "low head cap" in product_lower:
        h = 0.6 * diameter_mm
        r = 0.8 * diameter_mm / 2
        head_volume = 3.1416 * r ** 2 * h
    elif "button head" in product_lower:
        h = 0.4 * diameter_mm
        r = 0.9 * diameter_mm / 2
        head_volume = 3.1416 * r ** 2 * h
    else:
        head_volume = 0.5 * 3.1416 * (diameter_mm / 2) ** 2 * (0.5 * diameter_mm)
    total_volume = V_shank + head_volume
    weight_kg = total_volume * density / 1000
    return round(weight_kg, 4)

def convert_length_to_mm(length_val, unit):
    unit = unit.lower()
    if unit=="inch":
        return length_val * 25.4
    elif unit=="meter":
        return length_val * 1000
    elif unit=="ft":
        return length_val * 304.8
    return length_val

# ======================================================
# 🔹 Session State Initialization
# ======================================================
if "selected_section" not in st.session_state:
    st.session_state.selected_section = None
if "batch_result_df" not in st.session_state:
    st.session_state.batch_result_df = None

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
# 🔹 Product Database Section
# ======================================================
def show_product_database():
    st.header("📦 Product Database Search Panel")
    if df.empty and df_mechem.empty and df_iso4014.empty:
        st.warning("No data available.")
        return

    st.sidebar.header("🔍 Filter Options")
    product_types = ["All"] + sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
    product_type = st.sidebar.selectbox("Select Product", product_types)
    
    series_options = ["Inch", "Metric"]
    series = st.sidebar.selectbox("Select Series", series_options)
    
    dimensional_standards = ["All"] + sorted(df['Standards'].dropna().unique())
    if series == "Metric" and "ISO 4014" not in dimensional_standards:
        dimensional_standards.append("ISO 4014")
    dimensional_standard = st.sidebar.selectbox("Dimensional Standard", dimensional_standards)
    
    # Load appropriate DataFrame
    if dimensional_standard == "ISO 4014":
        temp_df = df_iso4014
    else:
        temp_df = df.copy()
        if product_type != "All":
            temp_df = temp_df[temp_df['Product']==product_type]
        if dimensional_standard != "All":
            temp_df = temp_df[temp_df['Standards']==dimensional_standard]

    size_options = ["All"] + sorted(temp_df['Size'].dropna().unique(), key=size_to_float)
    dimensional_size = st.sidebar.selectbox("Dimensional Size", size_options)
    
    # Thread standard
    thread_standards = ["All"]
    if series=="Inch":
        thread_standards += ["ASME B1.1"]
    else:
        thread_standards += ["ISO 965-2-98 Coarse","ISO 965-2-98 Fine"]
    thread_standard = st.sidebar.selectbox("Thread Standard", thread_standards)
    
    # Thread size/class
    thread_size_options = ["All"]
    thread_class_options = ["All"]
    if thread_standard != "All":
        df_thread = load_thread_data(thread_files.get(thread_standard,""))
        if not df_thread.empty:
            if "Thread" in df_thread.columns:
                thread_size_options += sorted(df_thread['Thread'].dropna().unique())
            if "Class" in df_thread.columns:
                thread_class_options += sorted(df_thread['Class'].dropna().unique())
    thread_size = st.sidebar.selectbox("Thread Size", thread_size_options)
    thread_class = st.sidebar.selectbox("Class", thread_class_options)
    
    # Grade filter for ISO 4014
    grade_options = ["All"]
    if dimensional_standard=="ISO 4014" and not df_iso4014.empty:
        grade_options += sorted(df_iso4014['Grade'].dropna().unique())
    grade_filter = st.sidebar.selectbox("Grade", grade_options)
    
    # ME&CERT filters
    mecert_standards = ["All"]
    if not df_mechem.empty:
        mecert_standards += sorted(df_mechem['Standard'].dropna().unique())
    mecert_standard = st.sidebar.selectbox("ME&CERT Standard", mecert_standards)
    
    mecert_property_options = ["All"]
    if mecert_standard != "All" and not df_mechem.empty:
        temp_me = df_mechem[df_mechem['Standard']==mecert_standard]
        if "Property class" in temp_me.columns:
            mecert_property_options += sorted(temp_me['Property class'].dropna().unique())
    mecert_property = st.sidebar.selectbox("Property Class", mecert_property_options)
    
    # Apply filters
    filtered_df = temp_df.copy()
    if dimensional_size != "All":
        filtered_df = filtered_df[filtered_df['Size']==dimensional_size]
    if grade_filter != "All" and "Grade" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Grade']==grade_filter]
    
    st.subheader(f"Found {len(filtered_df)} records")
    st.dataframe(filtered_df, use_container_width=True)
    
    # Thread data
    if thread_standard != "All" and not df_thread.empty:
        df_thread_filtered = df_thread.copy()
        if thread_size != "All":
            df_thread_filtered = df_thread_filtered[df_thread_filtered['Thread']==thread_size]
        if thread_class != "All":
            df_thread_filtered = df_thread_filtered[df_thread_filtered['Class']==thread_class]
        st.subheader(f"Thread Data: {thread_standard}")
        st.dataframe(df_thread_filtered, use_container_width=True)
    
    # ME&CERT data
    filtered_mecert_df = df_mechem.copy()
    if mecert_standard != "All":
        filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Standard']==mecert_standard]
    if mecert_property != "All":
        filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Property class']==mecert_property]
    st.subheader(f"ME&CERT Records: {len(filtered_mecert_df)}")
    st.dataframe(filtered_mecert_df, use_container_width=True)
    
    # Download all filtered data
    if st.button("📥 Download All Filtered Data"):
        wb = Workbook()
        ws_dim = wb.active
        ws_dim.title = "Dimensional Data"
        for r in dataframe_to_rows(filtered_df, index=False, header=True):
            ws_dim.append(r)
        if thread_standard != "All" and not df_thread.empty:
            ws_thread = wb.create_sheet("Thread Data")
            for r in dataframe_to_rows(df_thread_filtered, index=False, header=True):
                ws_thread.append(r)
        if not filtered_mecert_df.empty:
            ws_me = wb.create_sheet("ME&CERT Data")
            for r in dataframe_to_rows(filtered_mecert_df, index=False, header=True):
                ws_me.append(r)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        wb.save(temp_file.name)
        temp_file.close()
        with open(temp_file.name, "rb") as f:
            st.download_button("⬇️ Download Excel", f, file_name="Filtered_Fastener_Data.xlsx", 
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ======================================================
# 🔹 Calculations Section (Single & Batch)
# ======================================================
def show_calculations():
    st.header("🧮 Engineering Calculations")
    
    # --- Single Weight Calculation ---
    product_options = sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
    selected_product = st.selectbox("Select Product", product_options)
    series = st.selectbox("Select Series", ["Inch", "Metric"])
    metric_type = st.selectbox("Select Thread Type", ["Coarse", "Fine"]) if series=="Metric" else None
    selected_standard = "ASME B1.1" if series=="Inch" else ("ISO 965-2-98 Coarse" if metric_type=="Coarse" else "ISO 965-2-98 Fine")
    if series=="Metric" and st.checkbox("Use ISO 4014 Standard"):
        selected_standard = "ISO 4014"
    st.info(f"📏 Standard: **{selected_standard}** (used only for pitch diameter)")
    
    df_thread = df_iso4014 if selected_standard=="ISO 4014" else load_thread_data(thread_files.get(selected_standard,""))
    size_options = sorted(df_thread["Thread"].dropna().unique()) if not df_thread.empty else []
    selected_size = st.selectbox("Select Size", size_options)
    
    length_unit = st.selectbox("Select Length Unit", ["mm","inch","meter","ft"])
    length_val = st.number_input("Enter Length", min_value=0.1, step=0.1)
    dia_type = st.selectbox("Select Diameter Type", ["Body Diameter", "Pitch Diameter"])
    diameter_mm = None

    if dia_type == "Body Diameter":
        body_dia = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1)
        diameter_mm = body_dia*25.4 if length_unit=="inch" else body_dia
    else:
        if not df_thread.empty:
            row = df_thread[df_thread["Thread"]==selected_size]
            if not row.empty and "Pitch Diameter (Min)" in row.columns:
                pitch_val = row["Pitch Diameter (Min)"].values[0]
                diameter_mm = pitch_val if series=="Metric" else pitch_val*25.4
            else:
                st.warning("⚠️ Pitch Diameter not found.")

    grade_options_single = ["A","B"] if selected_standard=="ISO 4014" else ["All"]
    selected_grade = st.selectbox("Select Grade", grade_options_single)

    class_options_manual = ["1A", "2A", "3A"] if series=="Inch" else ["6g", "6H"]
    selected_class_manual = st.selectbox("Select Class (Manual Calculation)", class_options_manual)

    if st.button("Calculate Weight"):
        length_mm = convert_length_to_mm(length_val, length_unit)
        if diameter_mm is None:
            st.error("❌ Provide diameter.")
        else:
            weight_kg = calculate_weight(selected_product, diameter_mm, length_mm)
            st.success(f"✅ Estimated Weight: **{weight_kg} Kg** (Class: {selected_class_manual}, Grade: {selected_grade})")

    # --- Batch Weight Calculator ---
    st.subheader("Batch Weight Calculator")
    batch_selected_product = st.selectbox("Select Product for Batch", product_options, key="batch_product")
    batch_series = st.selectbox("Select Series", ["Inch", "Metric"], key="batch_series")
    batch_metric_type = st.selectbox("Select Thread Type", ["Coarse", "Fine"], key="batch_metric_type") if batch_series=="Metric" else None
    batch_standard = "ASME B1.1" if batch_series=="Inch" else ("ISO 965-2-98 Coarse" if batch_metric_type=="Coarse" else "ISO 965-2-98 Fine")
    if batch_series=="Metric" and st.checkbox("Use ISO 4014 Standard for Batch"):
        batch_standard = "ISO 4014"
    st.info(f"📏 Standard: **{batch_standard}** (used only for pitch diameter)")

    batch_length_unit = st.selectbox("Select Length Unit", ["mm","inch","meter","ft"], key="batch_length_unit")
    uploaded_file_batch = st.file_uploader("Upload Excel/CSV for Batch", type=["xlsx","csv"], key="batch_file")

    batch_class = None
    batch_grade = None
    if batch_series=="Metric" and batch_standard=="ISO 4014":
        batch_grade = st.selectbox("Select Grade for Batch", ["A","B"], key="batch_grade")
    
    if batch_series=="Inch":
        df_thread_batch = df_iso4014 if batch_standard=="ISO 4014" else load_thread_data(thread_files.get(batch_standard,""))
        class_options = ["All"]
        if not df_thread_batch.empty and "Class" in df_thread_batch.columns:
            class_options += sorted(df_thread_batch["Class"].dropna().unique())
        batch_class = st.selectbox("Select Class", class_options, key="batch_class")

    if uploaded_file_batch:
        batch_df = pd.read_excel(uploaded_file_batch) if uploaded_file_batch.name.endswith(".xlsx") else pd.read_csv(uploaded_file_batch)
        st.write("Uploaded File Preview:")
        st.dataframe(batch_df.head())
        required_cols = ["Product","Size","Length"]
        if all(col in batch_df.columns for col in required_cols):
            if st.button("Calculate Batch Weights", key="calc_batch_weights"):
                df_thread_batch = df_iso4014 if batch_standard=="ISO 4014" else load_thread_data(thread_files.get(batch_standard,""))
                df_dim_batch = df[df['Product']==batch_selected_product]
                weight_col_name = "Weight/pc (Kg)"
                if weight_col_name not in batch_df.columns:
                    batch_df[weight_col_name] = 0

                for idx, row in batch_df.iterrows():
                    prod = row["Product"]
                    size_val = row["Size"]
                    length_val = float(row["Length"])
                    length_mm = convert_length_to_mm(length_val, batch_length_unit)

                    diameter_mm = None
                    dim_row = df_dim_batch[df_dim_batch["Size"]==size_val] if not df_dim_batch.empty else pd.DataFrame()
                    if not dim_row.empty and "Body Diameter" in dim_row.columns:
                        diameter_mm = dim_row["Body Diameter"].values[0]

                    thread_row = pd.DataFrame()
                    if batch_series=="Inch":
                        if batch_class != "All" and not df_thread_batch.empty:
                            thread_row = df_thread_batch[(df_thread_batch["Thread"]==size_val) & (df_thread_batch["Class"]==batch_class)]
                        else:
                            thread_row = df_thread_batch[df_thread_batch["Thread"]==size_val]
                    else:
                        thread_row = df_thread_batch[df_thread_batch["Thread"]==size_val]

                    if not thread_row.empty and "Pitch Diameter (Min)" in thread_row.columns:
                        diameter_mm = thread_row["Pitch Diameter (Min)"].values[0]
                        if batch_series=="Inch":
                            diameter_mm *= 25.4

                    if diameter_mm is None:
                        try:
                            diameter_mm = float(size_val)
                        except:
                            diameter_mm = 0

                    weight = calculate_weight(prod, diameter_mm, length_mm)
                    batch_df.at[idx, weight_col_name] = weight
                    # Add Grade column if ISO 4014
                    if batch_standard=="ISO 4014":
                        batch_df.at[idx, "Grade"] = batch_grade

                st.session_state.batch_result_df = batch_df
                st.dataframe(batch_df)

    # Batch Download
    if st.session_state.batch_result_df is not None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        st.session_state.batch_result_df.to_excel(temp_file.name, index=False)
        temp_file.close()
        with open(temp_file.name,"rb") as f:
            st.download_button("⬇️ Download Batch Weights Excel", f, file_name="Batch_Weights.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ======================================================
# 🔹 AI Assistant Section
# ======================================================
def show_ai_assistant():
    st.header("🤖 PiU – AI Assistant")
    query = st.text_area("Enter your question for PiU")
    if st.button("Ask PiU"):
        st.info(f"Processing your query: **{query}**")
        st.success("PiU Response: [Simulated Response Here]")

# ======================================================
# 🔹 Placeholder Sections
# ======================================================
def show_inspection():
    st.header("🕵️ Inspection Section")
    st.info("Inspection module coming soon.")

def show_rnd():
    st.header("🔬 Research & Development Section")
    st.info("R&D module coming soon.")

def show_team_chat():
    st.header("💬 Team Chat Section")
    st.info("Team Chat module coming soon.")

# ======================================================
# 🔹 Section Dispatcher / Main Loop
# ======================================================
def show_section():
    section = st.session_state.selected_section
    if section is None:
        show_home()
    elif section=="📦 Product Database":
        show_product_database()
    elif section=="🧮 Calculations":
        show_calculations()
    elif section=="🤖 PiU (AI Assistant)":
        show_ai_assistant()
    elif section=="🕵️ Inspection":
        show_inspection()
    elif section=="🔬 Research & Development":
        show_rnd()
    elif section=="💬 Team Chat":
        show_team_chat()
    else:
        st.warning(f"{section} is not yet implemented.")

# ======================================================
# 🔹 Footer
# ======================================================
def show_footer():
    st.markdown("---")
    st.markdown("<p style='text-align:center;color:gray;'>© 2025 JSC Industries. All Rights Reserved.</p>", unsafe_allow_html=True)

# ======================================================
# 🔹 Run App
# ======================================================
show_section()
show_footer()
