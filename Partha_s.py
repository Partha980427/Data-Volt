import streamlit as st
import pandas as pd
import os
from fractions import Fraction
import math

# ======================================================
# 📂 Load Database
# ======================================================
# GitHub Excel direct download link
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"

# Local Excel backup path
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

# Standards
standards_options = ["All"] + sorted(df['Standards'].dropna().unique())
standard = st.sidebar.selectbox("Select Standard", standards_options)

# Size (supports fractions like 1/2, 1-1/2)
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

# Product
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
# ⚖️ Weight Calculator (Manual Input)
# ======================================================
st.header("⚖️ Weight Calculator")

def calculate_weight(product, size, length):
    try:
        # Convert size (fraction or metric)
        if isinstance(size, str):
            try:
                dia = float(Fraction(size)) * 25.4  # inch -> mm
            except:
                if size.startswith("M"):
                    dia = float(size.replace("M", ""))
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

calc_product = st.selectbox("Select Product for Weight", product_options[1:])
calc_size = st.selectbox("Select Size for Weight", size_options[1:])
calc_length = st.number_input("Enter Length (mm)", min_value=1, value=100)

if st.button("Calculate Weight"):
    result = calculate_weight(calc_product, calc_size, calc_length)
    if result:
        st.success(f"Estimated Weight/pc: {result} kg")
    else:
        st.error("No formula available for this combination.")

# ======================================================
# 📥 Batch Excel Weight Calculation
# ======================================================
st.header("📥 Upload Excel for Batch Weight Calculation")

uploaded_file = st.file_uploader("Upload Excel with columns: Size, Length", type=["xlsx"])

if uploaded_file:
    try:
        upload_df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        st.stop()

    required_columns = ["Size", "Length"]
    for col in required_columns:
        if col not in upload_df.columns:
            st.error(f"Uploaded file must contain column: {col}")
            st.stop()

    if "Weight/pc (Kg)" not in upload_df.columns:
        upload_df["Weight/pc (Kg)"] = None

    # Calculate weight row by row
    def get_weight(row):
        size = row["Size"]
        length = row["Length"]

        # Optional: use Product column if present
        product = row.get("Product", "Hex Bolt") if "Product" in row else "Hex Bolt"

        return calculate_weight(product, size, length)

    upload_df["Weight/pc (Kg)"] = upload_df.apply(get_weight, axis=1)

    st.write("### Processed Excel Preview", upload_df.head())

    # Save and offer download
    output_file = "processed_weights.xlsx"
    upload_df.to_excel(output_file, index=False)

    with open(output_file, "rb") as f:
        st.download_button(
            "📥 Download Processed Excel",
            f,
            file_name="processed_weights.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.success("Weights calculated successfully!")
