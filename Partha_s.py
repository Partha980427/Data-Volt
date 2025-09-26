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

# Product-specific weight calculation
def calculate_weight(product, diameter_mm, length_mm):
    density = 0.00785  # Steel density in g/mm^3
    # Approximate multipliers or factors for different products
    if product == "Hex Cap Screw":
        factor = 0.95
    elif product == "Heavy Hex Bolt":
        factor = 1.05
    elif product == "Heavy Hex Screw":
        factor = 1.1
    elif product == "Threaded Rod":
        factor = 1.0
    else:  # Standard Hex Bolt
        factor = 1.0
    
    # Cylindrical approximation
    volume = 3.1416 * (diameter_mm / 2) ** 2 * length_mm
    weight_kg = volume * density * factor / 1000
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
        product_types = ["All"] + sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
        product_type = st.sidebar.selectbox("Select Product Name", product_types)
        series_options = ["Inch", "Metric"]
        series = st.sidebar.selectbox("Select Series", series_options)

        # Dimensional Specification
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

        # Thread Specification
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

        # ME&CERT Specification
        st.sidebar.subheader("ME&CERT Specification")
        mecert_standard_options = ["All"] + (sorted(df_mechem['Standard'].dropna().unique()) if not df_mechem.empty else [])
        mecert_standard = st.sidebar.selectbox("ME&CERT Standard", mecert_standard_options)
        mecert_property_options = ["All"]
        if mecert_standard != "All":
            temp_df_me = df_mechem[df_mechem['Standard'] == mecert_standard]
            if "Property class" in temp_df_me.columns:
                mecert_property_options += sorted(temp_df_me['Property class'].dropna().unique())
        mecert_property = st.sidebar.selectbox("Property Class", mecert_property_options)

        # Filter Main Database
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

# ======================================================
# 📝 Tab 2 – Manual Weight Calculator
# ======================================================
with tab2:
    st.header("Manual Weight Calculator")

    product_options = sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
    selected_product = st.selectbox("1️⃣ Select Product", product_options)
    series = st.selectbox("2️⃣ Select Series", ["Inch", "Metric"])
    metric_type = st.selectbox("3️⃣ Select Thread Type", ["Coarse", "Fine"]) if series=="Metric" else None
    selected_standard = "ASME B1.1" if series=="Inch" else ("ISO 965-2-98 Coarse" if metric_type=="Coarse" else "ISO 965-2-98 Fine")
    st.info(f"📏 Standard: **{selected_standard}** (used only for pitch diameter)")

    df_thread = load_thread_data(thread_files[selected_standard])
    size_options = sorted(df_thread["Thread"].dropna().unique()) if not df_thread.empty else []
    selected_size = st.selectbox("5️⃣ Select Size", size_options)
    length_unit = st.selectbox("6️⃣ Select Length Unit", ["inch", "mm"])
    length_val = st.number_input("7️⃣ Enter Length", min_value=0.1, step=0.1)
    dia_type = st.selectbox("8️⃣ Select Diameter Type", ["Body Diameter", "Pitch Diameter"])

    diameter_mm = None
    if dia_type == "Body Diameter":
        body_dia = st.number_input("🔹 Enter Body Diameter", min_value=0.1, step=0.1)
        diameter_mm = body_dia * 25.4 if length_unit == "inch" else body_dia
    else:
        if not df_thread.empty:
            if "Class" in df_thread.columns:
                pitch_classes = sorted(df_thread["Class"].dropna().unique())
                pitch_class = st.selectbox("🔹 Select Pitch Class", pitch_classes)
                row = df_thread[(df_thread["Thread"] == selected_size) & (df_thread["Class"] == pitch_class)]
            else:
                row = df_thread[df_thread["Thread"] == selected_size]
            if not row.empty:
                pitch_val = row["Pitch Diameter (Min)"].values[0]
                diameter_mm = pitch_val if series=="Metric" else pitch_val*25.4
            else:
                st.warning("⚠️ Pitch Diameter not found for this selection.")

    if st.button("⚖️ Calculate Weight"):
        length_mm = length_val*25.4 if length_unit=="inch" else length_val
        if diameter_mm is None:
            st.error("❌ Please provide diameter information.")
        else:
            weight_kg = calculate_weight(selected_product, diameter_mm, length_mm)
            st.success(f"✅ Estimated Weight/pc: **{weight_kg} Kg**")

# ======================================================
# 📤 Tab 3 – Batch Excel Uploader (Full Modified)
# ======================================================
with tab3:
    st.header("Batch Weight Calculator")
    batch_product_options = sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
    batch_selected_product = st.selectbox("1️⃣ Select Product", batch_product_options, key="batch_product")
    batch_series = st.selectbox("2️⃣ Select Series", ["Inch", "Metric"], key="batch_series")
    batch_metric_type = st.selectbox("3️⃣ Select Thread Type", ["Coarse", "Fine"], key="batch_metric_type") if batch_series=="Metric" else None
    batch_standard = "ASME B1.1" if batch_series=="Inch" else ("ISO 965-2-98 Coarse" if batch_metric_type=="Coarse" else "ISO 965-2-98 Fine")
    st.info(f"📏 Standard: **{batch_standard}** (used only for pitch diameter)")
    batch_length_unit = st.selectbox("4️⃣ Select Length Unit", ["inch","mm","meter"], key="batch_length_unit")
    batch_weight_col_name = st.text_input("5️⃣ Enter column name for Weight/pc (Kg)", "Weight/pc (Kg)", key="batch_weight_col_name")
    batch_weight_col_index = st.number_input("6️⃣ Column Index for Weight", min_value=1, value=10, key="batch_weight_col_index")
    uploaded_file_batch = st.file_uploader("7️⃣ Upload Excel file", type=["xlsx"], key="batch_file")

    if uploaded_file_batch:
        user_df_batch = pd.read_excel(uploaded_file_batch)
        st.write("📄 Uploaded File Preview:")
        st.dataframe(user_df_batch.head())
        size_col_batch = next((c for c in user_df_batch.columns if "size" in c.lower()), None)
        length_col_batch = next((c for c in user_df_batch.columns if "length" in c.lower()), None)

        if size_col_batch and length_col_batch:
            st.info(f"Detected columns → Size: {size_col_batch}, Length: {length_col_batch}")

            if st.button("8️⃣ Calculate Weights for All Rows"):
                temp_file_batch = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                temp_file_batch.write(uploaded_file_batch.getbuffer())
                temp_file_batch.close()
                wb = load_workbook(temp_file_batch.name)
                ws = wb.active

                if ws.cell(row=1, column=batch_weight_col_index).value != batch_weight_col_name:
                    ws.insert_cols(batch_weight_col_index)
                    ws.cell(row=1, column=batch_weight_col_index, value=batch_weight_col_name)

                dim_df = df[df['Product']==batch_selected_product] if not df.empty else pd.DataFrame()
                thread_df = load_thread_data(thread_files[batch_standard])

                for row_idx in range(2, ws.max_row+1):
                    size_val = ws.cell(row=row_idx, column=user_df_batch.columns.get_loc(size_col_batch)+1).value
                    length_val = ws.cell(row=row_idx, column=user_df_batch.columns.get_loc(length_col_batch)+1).value
                    if size_val and length_val:
                        size_mm = size_to_float(size_val)
                        length_mm = float(length_val)
                        if batch_length_unit=="inch":
                            length_mm *= 25.4
                        elif batch_length_unit=="meter":
                            length_mm *= 1000

                        diameter_mm = None
                        # Body diameter from Dimensional Spec
                        if not dim_df.empty and "Size" in dim_df.columns and "Body Diameter" in dim_df.columns:
                            row_dim = dim_df[dim_df["Size"]==size_val]
                            if not row_dim.empty:
                                diameter_mm = row_dim["Body Diameter"].values[0]

                        # Pitch diameter from Thread Spec
                        if not thread_df.empty and "Thread" in thread_df.columns and "Pitch Diameter (Min)" in thread_df.columns:
                            row_thread = thread_df[thread_df["Thread"]==size_val]
                            if not row_thread.empty:
                                pitch_val = row_thread["Pitch Diameter (Min)"].values[0]
                                diameter_mm = pitch_val

                        if diameter_mm is None:
                            diameter_mm = size_mm

                        weight = calculate_weight(batch_selected_product, diameter_mm, length_mm)
                        ws.cell(row=row_idx, column=batch_weight_col_index, value=weight)

                output_file_batch = "updated_with_weights.xlsx"
                wb.save(output_file_batch)
                st.success("✅ Weights calculated successfully!")

                with open(output_file_batch, "rb") as f:
                    st.download_button("⬇️ Download Updated Excel", f, file_name=output_file_batch, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        else:
            st.error("❌ Could not detect Size or Length columns. Please check your file.")

# ======================================================
# 🔹 Footer
# ======================================================
st.markdown("""
<hr>
<div style='text-align:center; color:gray'>
    © JSC Industries Pvt Ltd | Born to Perform
</div>
""", unsafe_allow_html=True)
