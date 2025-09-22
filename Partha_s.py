import streamlit as st
import pandas as pd
import os
from fractions import Fraction

# --- Google Sheets direct download link for data ---
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"

# --- Local path for original Excel download (Windows Google Drive sync) ---
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

# --- Load data from Google Sheets ---
@st.cache_data
def load_data(url):
    return pd.read_excel(url)

df = load_data(url)

st.title("Bolt & Rod Search App")
st.write("Search ASME B18.2.1 Hex Bolts and Heavy Hex Bolts by Standard, Size, and Product")

if df.empty:
    st.warning("No data available.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Search Filters")

# Standard Filter
standards_options = ["All"] + sorted(df['Standards'].dropna().unique())
standard = st.sidebar.selectbox("Select Standard", standards_options)

# Size Filter (handles fractions like '1/2', '1-1/2')
def size_to_float(size_str):
    try:
        if "-" in str(size_str):
            parts = str(size_str).split("-")
            return float(parts[0]) + float(Fraction(parts[1]))
        else:
            return float(Fraction(str(size_str)))
    except:
        return float('inf')  # Invalid formats go to the end

size_options = ["All"] + sorted(df['Size'].dropna().unique(), key=size_to_float)
size = st.sidebar.selectbox("Select Size", size_options)

# Product Filter
product_options = ["All"] + sorted(df['Product'].dropna().unique())
product = st.sidebar.selectbox("Select Product", product_options)

# --- Filter Data ---
filtered_df = df.copy()
if standard != "All":
    filtered_df = filtered_df[filtered_df['Standards'] == standard]
if size != "All":
    filtered_df = filtered_df[filtered_df['Size'] == size]
if product != "All":
    filtered_df = filtered_df[filtered_df['Product'] == product]

# --- Display Results ---
st.subheader(f"Found {len(filtered_df)} matching items")
st.dataframe(filtered_df)

# --- Download Filtered Data ---
st.download_button(
    "Download Filtered Results as CSV",
    filtered_df.to_csv(index=False),
    file_name="filtered_bolts.csv",
    mime="text/csv"
)

# --- Download Original Excel ---
if os.path.exists(local_excel_path):
    with open(local_excel_path, "rb") as f:
        st.download_button(
            "Download Original Excel",
            f,
            file_name="ASME_B18.2.1_Hex_Bolt_and_Heavy_Hex_Bolt.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.warning("Original Excel file not found at local path.")
