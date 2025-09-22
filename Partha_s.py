import streamlit as st
import pandas as pd
import os

# --- Path to Excel on Google Drive (local sync) ---
excel_file = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

# --- Load Excel ---
@st.cache_data
def load_data(file_path):
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    else:
        st.error("Excel file not found!")
        return pd.DataFrame()

df = load_data(excel_file)

st.title("Bolt & Rod Search App")
st.write("Search ASME B18.2.1 Hex Bolts and Heavy Hex Bolts by Standard, Size, and Product")

if df.empty:
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Search Filters")

# 1. Standard Filter
standards_options = ["All"] + list(df['Standards'].dropna().unique())
standard = st.sidebar.selectbox("Select Standard", standards_options)

# 2. Size Filter
size_options = ["All"] + list(df['Size'].dropna().unique())
size = st.sidebar.selectbox("Select Size", size_options)

# 3. Product Filter
product_options = ["All"] + list(df['Product'].dropna().unique())
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

# --- Optional: Download Original Excel ---
st.download_button(
    "Download Original Excel",
    open(excel_file, "rb").read(),
    file_name="ASME_B18.2.1_Hex_Bolt_and_Heavy_Hex_Bolt.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
