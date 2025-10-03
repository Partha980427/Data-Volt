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
    return round(weight_kg, 4)  # 4 decimal places

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
# 🔹 TDS Generation Helper
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
        # …[Existing code for Product Database Search & TDS]…
        pass  # Keeping as is for brevity

    elif title == "🧮 Calculations":
        st.header("🧮 Engineering Calculations")
        st.subheader("Manual Weight Calculator")
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
            diameter_mm = body_dia * 25.4 if length_unit=="inch" else body_dia
        else:
            if not df_thread.empty:
                if "Class" in df_thread.columns:
                    pitch_classes = sorted(df_thread["Class"].dropna().unique())
                    pitch_class = st.selectbox("🔹 Select Pitch Class", pitch_classes)
                    row = df_thread[(df_thread["Thread"]==selected_size) & (df_thread["Class"]==pitch_class)]
                else:
                    row = df_thread[df_thread["Thread"]==selected_size]
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
        # 🔹 Batch Weight Calculator (Integrated Correct Version)
        # ======================================================
        st.subheader("📊 Batch Weight Calculator")
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
                            if not dim_df.empty and "Size" in dim_df.columns and "Body Diameter" in dim_df.columns:
                                row_dim = dim_df[dim_df["Size"]==size_val]
                                if not row_dim.empty:
                                    diameter_mm = row_dim["Body Diameter"].values[0]

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
                        st.download_button("⬇️ Download Updated Excel", f, file_name=output_file_batch,
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            else:
                st.error("❌ Could not detect Size or Length columns. Please check your file.")

    # …[Other sections like Inspection, R&D, Team Chat, PiU]…

    # Back Button
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
