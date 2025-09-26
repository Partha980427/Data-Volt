import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows  # <-- Added import
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
        # Download All Filtered Data
        # -----------------------------
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
# 📝 Tab 2 – Manual Weight Calculator (Modified)
# ======================================================
with tab2:
    st.header("Manual Weight Calculator")

    # 1. Select Product
    product_options = ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw", "Threaded Rod", "Stud"]
    selected_product = st.selectbox("Select Product", product_options)

    # 2. Select Series
    series_options = ["Inch", "Metric"]
    selected_series = st.selectbox("Select Series", series_options, key="manual_series")

    # 3. Select Size
    size_options = []
    if selected_series == "Inch":
        temp_df = df[df["Standards"] == "ASME B18.2.1"]
    elif selected_series == "Metric":
        temp_df = df[df["Standards"].str.contains("ISO", na=False)]
    else:
        temp_df = df.copy()

    if not temp_df.empty and "Size" in temp_df.columns:
        size_options = sorted(temp_df["Size"].dropna().unique(), key=size_to_float)

    selected_size = st.selectbox("Select Size", size_options)

    # 4. Select Length Unit
    length_unit = st.selectbox("Select Length Unit", ["inch", "mm"], key="manual_length_unit")

    # 5. Enter Length
    length_val = st.number_input("Enter Length", min_value=0.1, step=0.1)

    # 6. Select Diameter Type
    dia_type = st.selectbox("Select Diameter Type", ["Body Diameter", "Pitch Diameter"])

    # 7. Handle Diameter
    diameter_mm = None
    if dia_type == "Body Diameter":
        diameter_input = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1)
        diameter_mm = diameter_input * 25.4 if length_unit == "inch" else diameter_input
    elif dia_type == "Pitch Diameter":
        thread_standard = None
        if selected_series == "Inch":
            thread_standard = "ASME B1.1"
        elif selected_series == "Metric":
            # Let user choose Coarse or Fine
            thread_standard = st.selectbox("Select Thread Standard for Pitch Dia", ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"])

        if thread_standard and thread_standard in thread_files:
            df_thread = load_thread_data(thread_files[thread_standard])
            if not df_thread.empty and "Thread" in df_thread.columns:
                pitch_row = df_thread[df_thread["Thread"] == selected_size]
                if not pitch_row.empty:
                    pitch_val = pitch_row["Pitch Diameter"].values[0]
                    diameter_mm = pitch_val * 25.4 if selected_series == "Inch" else pitch_val

    # Length conversion
    length_mm = length_val * 25.4 if length_unit == "inch" else length_val

    # 8. Weight Calculation
    if st.button("Calculate Weight"):
        if diameter_mm is None or length_mm <= 0:
            st.error("❌ Please provide valid diameter and length.")
        else:
            density = 0.00785  # g/mm³
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

            st.success(f"✅ Estimated Weight/pc: **{round(weight_kg, 3)} Kg**")

# ======================================================
# 📤 Tab 3 – Batch Excel Uploader
# ======================================================
with tab3:
    st.header("Batch Weight Calculator")
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

    if uploaded_file:
        user_df = pd.read_excel(uploaded_file)
        st.write("📄 Uploaded File Preview:")
        st.dataframe(user_df.head())

        size_col = next((c for c in user_df.columns if "size" in c.lower()), None)
        length_col = next((c for c in user_df.columns if "length" in c.lower()), None)
        product_col = next((c for c in user_df.columns if "product" in c.lower()), None)

        weight_col_name = st.text_input("Enter column name for Weight/pc (Kg)", "Weight/pc (Kg)")
        weight_col_index = st.number_input("Enter column index to write Weight/pc (numeric, e.g., 3 = C column)", min_value=1, value=len(user_df.columns)+1)

        size_unit_batch = st.selectbox("Select Size Unit (Batch)", ["inch", "mm"], key="size_batch")
        length_unit_batch = st.selectbox("Select Length Unit (Batch)", ["inch", "mm"], key="length_batch")

        if size_col and length_col:
            st.info(f"Detected columns → Size: {size_col}, Length: {length_col}")

            selected_product_type = None
            if not product_col:
                selected_product_type = st.selectbox("Select Product Type (for all rows)", ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw"], key="product_batch")

            if st.button("Calculate Weights for All"):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                temp_file.write(uploaded_file.getbuffer())
                temp_file.close()

                wb = load_workbook(temp_file.name)
                ws = wb.active

                if ws.cell(row=1, column=weight_col_index).value != weight_col_name:
                    ws.insert_cols(weight_col_index)
                    ws.cell(row=1, column=weight_col_index, value=weight_col_name)

                for row_idx in range(2, ws.max_row + 1):
                    size_val = ws.cell(row=row_idx, column=user_df.columns.get_loc(size_col)+1).value
                    length_val = ws.cell(row=row_idx, column=user_df.columns.get_loc(length_col)+1).value
                    prod_val = ws.cell(row=row_idx, column=user_df.columns.get_loc(product_col)+1).value if product_col else selected_product_type

                    if size_val and length_val:
                        size_in = size_to_float(size_val)
                        length_in_float = float(length_val)
                        if size_unit_batch == "mm":
                            size_in /= 25.4
                        if length_unit_batch == "mm":
                            length_in_float /= 25.4
                        ws.cell(row=row_idx, column=weight_col_index, value=calculate_weight(prod_val, size_in, length_in_float))

                output_file = "updated_with_weights.xlsx"
                wb.save(output_file)
                st.success("✅ Weights calculated successfully!")
                with open(output_file, "rb") as f:
                    st.download_button("⬇️ Download Updated Excel", f, file_name=output_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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
