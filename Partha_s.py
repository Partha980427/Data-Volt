import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook

# ======================================================
# 🔹 Page Setup
# ======================================================
st.set_page_config(page_title="Bolt & Rod Calculator", layout="wide")
st.title("🔩 Bolt & Rod Search & Weight Calculator")
st.markdown("<h4 style='text-align:center; color:gray;'>JSC Industries Pvt Ltd | Born to Perform</h4>", unsafe_allow_html=True)

# ======================================================
# 🔹 Load Database
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

@st.cache_data
def load_data(url):
    try:
        return pd.read_excel(url)
    except:
        if os.path.exists(local_excel_path):
            return pd.read_excel(local_excel_path)
        return pd.DataFrame()

df = load_data(url)

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
    if df.empty:
        st.warning("No data available.")
    else:
        st.sidebar.header("Search Filters")
        standards_options = ["All"] + sorted(df['Standards'].dropna().unique())
        standard = st.sidebar.selectbox("Select Standard", standards_options)
        size_options = ["All"] + sorted(df['Size'].dropna().unique(), key=size_to_float)
        size = st.sidebar.selectbox("Select Size", size_options)
        product_options = ["All"] + sorted(df['Product'].dropna().unique())
        product = st.sidebar.selectbox("Select Product", product_options)

        filtered_df = df.copy()
        if standard != "All":
            filtered_df = filtered_df[filtered_df['Standards'] == standard]
        if size != "All":
            filtered_df = filtered_df[filtered_df['Size'] == size]
        if product != "All":
            filtered_df = filtered_df[filtered_df['Product'] == product]

        st.subheader(f"Found {len(filtered_df)} matching items")
        st.dataframe(filtered_df)

        st.download_button(
            "⬇️ Download Filtered Results as CSV",
            filtered_df.to_csv(index=False),
            file_name="filtered_bolts.csv",
            mime="text/csv"
        )

# ======================================================
# 📝 Tab 2 – Manual Weight Calculator
# ======================================================
with tab2:
    st.header("Manual Weight Calculator")

    # Let user choose Size and Length columns
    size_col_manual = st.selectbox("Select Size Column", sorted(df.columns), index=df.columns.get_loc("Size") if "Size" in df.columns else 0)
    length_col_manual = st.selectbox("Select Length Column", sorted(df.columns), index=df.columns.get_loc("Length") if "Length" in df.columns else 0)

    # Unit selection
    unit_size = st.selectbox("Select Size Unit", ["inch", "mm"])
    unit_length = st.selectbox("Select Length Unit", ["inch", "mm"])

    # Enter values manually
    size_val = st.text_input(f"Enter {size_col_manual} value")
    length_val = st.number_input(f"Enter {length_col_manual} value", min_value=0.1, step=0.1)

    product_type_manual = st.selectbox("Select Product Type", sorted(df['Product'].dropna().unique()))

    if st.button("Calculate Weight"):
        try:
            size_in = size_to_float(size_val)
            length_in = float(length_val)
            if unit_size == "mm":
                size_in /= 25.4
            if unit_length == "mm":
                length_in /= 25.4
            weight = calculate_weight(product_type_manual, size_in, length_in)
            st.success(f"Estimated Weight/pc: **{weight} Kg**")
        except Exception as e:
            st.error(f"Error in calculation: {e}")

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

        # Let user select Size and Length columns
        size_col = st.selectbox("Select Size Column", user_df.columns, index=user_df.columns.get_loc("Size") if "Size" in user_df.columns else 0)
        length_col = st.selectbox("Select Length Column", user_df.columns, index=user_df.columns.get_loc("Length") if "Length" in user_df.columns else 0)
        product_col = next((c for c in user_df.columns if "product" in c.lower()), None)

        # Units
        unit_size = st.selectbox("Select Size Unit", ["inch", "mm"])
        unit_length = st.selectbox("Select Length Unit", ["inch", "mm"])

        # Weight column
        weight_col_name = st.text_input("Enter column name for Weight/pc (Kg)", "Weight/pc (Kg)")
        weight_col_index = st.number_input(
            "Enter column index to write Weight/pc (numeric, e.g., 3 = C column)",
            min_value=1, value=len(user_df.columns)+1
        )

        selected_product_type = None
        if not product_col:
            selected_product_type = st.selectbox(
                "Select Product Type (for all rows)",
                ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw"]
            )

        if st.button("Calculate Weights for All"):
            wb = load_workbook(uploaded_file)
            ws = wb.active

            if ws.cell(row=1, column=weight_col_index).value != weight_col_name:
                ws.insert_cols(weight_col_index)
                ws.cell(row=1, column=weight_col_index, value=weight_col_name)

            for row_idx in range(2, ws.max_row+1):
                size_val_row = ws.cell(row=row_idx, column=user_df.columns.get_loc(size_col)+1).value
                length_val_row = ws.cell(row=row_idx, column=user_df.columns.get_loc(length_col)+1).value
                prod_val_row = ws.cell(row=row_idx, column=user_df.columns.get_loc(product_col)+1).value if product_col else selected_product_type

                if size_val_row and length_val_row:
                    size_in = size_to_float(size_val_row)
                    length_in = float(length_val_row)
                    if unit_size == "mm":
                        size_in /= 25.4
                    if unit_length == "mm":
                        length_in /= 25.4
                    ws.cell(row=row_idx, column=weight_col_index, value=calculate_weight(prod_val_row, size_in, length_in))

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
