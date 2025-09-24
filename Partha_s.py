import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook
import tempfile

# ======================================================
# 🔹 Page Setup
# ======================================================
st.set_page_config(page_title="Bolt & Rod Calculator", layout="wide")
st.title("🔩 Bolt & Rod Search & Weight Calculator")
st.markdown("<h4 style='text-align:center; color:gray;'>JSC Industries Pvt Ltd | Born to Perform</h4>", unsafe_allow_html=True)

# ======================================================
# 🔹 Load Bolt Database
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

# Thread databases
thread_files = {
    "ASME B1.1": "ASME B1.1 New.xlsx",
    "ISO 965-2-98 Coarse": "ISO 965-2-98 Coarse.xlsx",
    "ISO 965-2-98 Fine": "ISO 965-2-98 Fine.xlsx"
}

@st.cache_data
def load_data(path_or_url):
    try:
        return pd.read_excel(path_or_url)
    except:
        if os.path.exists(path_or_url):
            return pd.read_excel(path_or_url)
        return pd.DataFrame()

df_bolt = load_data(url)

# ======================================================
# 🔹 Helper Functions
# ======================================================
def size_to_float(size_str):
    try:
        size_str = str(size_str).strip()
        if "-" in size_str:
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
tab1, tab2, tab3 = st.tabs(["📂 Database Search", "📝 Manual Weight Calculator", "📤 Batch Excel Uploader"])

# ======================================================
# 📂 Tab 1 – Database Search
# ======================================================
with tab1:
    st.header("📊 Search Bolts in Database")
    if df_bolt.empty:
        st.warning("No bolt data available.")
    else:
        st.sidebar.header("Search Filters")

        # Specification filter
        spec_options = ["All", "Dimensional", "Mechanical", "Chemical"]
        specification = st.sidebar.selectbox("Select Specification", spec_options)

        # Bolt Standards filter
        standards_options = ["All"]
        if specification in ["All", "Dimensional"]:
            standards_options += sorted(df_bolt['Standards'].dropna().unique())
        else:
            if "Specification" in df_bolt.columns:
                standards_options += sorted(df_bolt[df_bolt['Specification'] == specification]['Standards'].dropna().unique())
        standard = st.sidebar.selectbox("Select Bolt Standard", standards_options)

        # Thread filter – only visible when Dimensional is selected
        thread_standard = "All"
        if specification == "Dimensional":
            thread_standard = st.sidebar.selectbox(
                "Select Thread Standard",
                ["All"] + list(thread_files.keys())
            )

        # Other filters
        size_options = ["All"] + sorted(df_bolt['Size'].dropna().unique(), key=size_to_float)
        size = st.sidebar.selectbox("Select Size", size_options)
        product_options = ["All"] + sorted(df_bolt['Product'].dropna().unique())
        product = st.sidebar.selectbox("Select Product", product_options)

        # Filter bolt data
        filtered_bolt = df_bolt.copy()
        if specification != "All" and "Specification" in df_bolt.columns:
            filtered_bolt = filtered_bolt[filtered_bolt['Specification'] == specification]
        if standard != "All":
            filtered_bolt = filtered_bolt[filtered_bolt['Standards'] == standard]
        if size != "All":
            filtered_bolt = filtered_bolt[filtered_bolt['Size'] == size]
        if product != "All":
            filtered_bolt = filtered_bolt[filtered_bolt['Product'] == product]

        st.subheader(f"Found {len(filtered_bolt)} matching bolt items")
        st.dataframe(filtered_bolt)

        # Filter and show thread data
        filtered_thread_list = []
        if specification == "Dimensional":
            for name, file in thread_files.items():
                if thread_standard != "All" and thread_standard != name:
                    continue
                if os.path.exists(file):
                    df_thread = pd.read_excel(file)
                    # Extract base size from thread column (e.g., 1/4-10 -> 1/4)
                    df_thread['Base_Size'] = df_thread.iloc[:,0].astype(str).str.split('-').str[0]
                    df_thread_filtered = df_thread.copy()
                    if size != "All":
                        df_thread_filtered = df_thread[df_thread['Base_Size'] == size]
                    if not df_thread_filtered.empty:
                        filtered_thread_list.append((name, df_thread_filtered))

        for thread_name, df_thread_filtered in filtered_thread_list:
            st.subheader(f"Thread Dimensions: {thread_name}")
            st.dataframe(df_thread_filtered.drop(columns=['Base_Size']))
            with open(thread_files[thread_name], "rb") as f:
                st.download_button(
                    f"⬇️ Download {thread_name} Thread Data",
                    f,
                    file_name=thread_files[thread_name],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ======================================================
# 📝 Tab 2 – Manual Weight Calculator
# ======================================================
with tab2:
    st.header("Manual Weight Calculator")
    product_type = st.selectbox("Select Product Type", sorted(df_bolt['Product'].dropna().unique()))
    size_str = st.selectbox("Select Size", sorted(df_bolt['Size'].dropna().unique(), key=size_to_float))
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
        weight_col_index = st.number_input(
            "Enter column index to write Weight/pc (numeric, e.g., 3 = C column)",
            min_value=1, value=len(user_df.columns)+1
        )

        size_unit_batch = st.selectbox("Select Size Unit (Batch)", ["inch", "mm"], key="size_batch")
        length_unit_batch = st.selectbox("Select Length Unit (Batch)", ["inch", "mm"], key="length_batch")

        if size_col and length_col:
            st.info(f"Detected columns → Size: {size_col}, Length: {length_col}")

            selected_product_type = None
            if not product_col:
                selected_product_type = st.selectbox(
                    "Select Product Type (for all rows)",
                    ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw"],
                    key="product_batch"
                )

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
                    st.download_button(
                        "⬇️ Download Updated Excel",
                        f,
                        file_name=output_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

# ======================================================
# 🔹 Footer
# ======================================================
st.markdown("""
<hr>
<div style='text-align:center; color:gray'>
    © JSC Industries Pvt Ltd | Born to Perform
</div>
""", unsafe_allow_html=True)
