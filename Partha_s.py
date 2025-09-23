import streamlit as st
import pandas as pd
import os
from fractions import Fraction

# ======================================================
# 🔻 Load Database
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"

@st.cache_data
def load_data(url):
    return pd.read_excel(url)

df = load_data(url)

st.set_page_config(page_title="Bolt & Rod Calculator", layout="wide")

st.title("🔩 Bolt & Rod Search & Weight Calculator")

# ======================================================
# 🔻 Helper Functions
# ======================================================

def size_to_float(size_str):
    """Convert fractional size like '1-1/2' or '3/4' to float (in inches)."""
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
    """Dummy calculation – replace with actual formulas."""
    size_mm = size_in * 25.4  # convert inches → mm
    length_mm = length_in * 25.4
    density = 0.00785  # g/mm³ for steel
    # Simplified formula: cylindrical rod
    volume = 3.1416 * (size_mm/2)**2 * length_mm
    weight_kg = volume * density / 1e6
    return round(weight_kg, 3)

# ======================================================
# 🔻 Tabs
# ======================================================
tab1, tab2, tab3 = st.tabs(["📂 Database Search", "📝 Manual Weight Calculator", "📤 Batch Excel Uploader"])

# ======================================================
# 📂 TAB 1 – Database Search
# ======================================================
with tab1:
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
# 📝 TAB 2 – Manual Weight Calculator
# ======================================================
with tab2:
    st.subheader("Manual Weight Calculator")

    product_type = st.selectbox("Select Product Type", sorted(df['Product'].dropna().unique()))
    size_str = st.selectbox("Select Size", sorted(df['Size'].dropna().unique(), key=size_to_float))
    length_in = st.number_input("Enter Length (in inches)", min_value=0.1, step=0.1)

    if st.button("Calculate Weight"):
        size_in = size_to_float(size_str)
        if size_in:
            weight = calculate_weight(product_type, size_in, length_in)
            st.success(f"Estimated Weight/pc: **{weight} Kg**")
        else:
            st.error("Invalid size format")

# ======================================================
# 📤 TAB 3 – Batch Excel Uploader
# ======================================================
with tab3:
    st.subheader("Upload Excel for Batch Weight Calculation")

    uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

    if uploaded_file:
        user_df = pd.read_excel(uploaded_file)
        st.write("📄 Uploaded File Preview:")
        st.dataframe(user_df.head())

        # Detect size/length columns automatically
        size_col = next((col for col in user_df.columns if "size" in col.lower()), None)
        length_col = next((col for col in user_df.columns if "length" in col.lower()), None)

        weight_col = st.text_input("Enter column name for Weight/pc (Kg)", "Weight/pc (Kg)")

        if size_col and length_col:
            st.info(f"Detected columns → Size: **{size_col}**, Length: **{length_col}**")

            if st.button("Calculate Weights for All"):
                results = []
                for i, row in user_df.iterrows():
                    size_in = size_to_float(row[size_col])
                    length_in = row[length_col]
                    if size_in and pd.notna(length_in):
                        results.append(calculate_weight("Bolt", size_in, length_in))
                    else:
                        results.append(None)

                user_df[weight_col] = results
                st.success("✅ Weights calculated successfully!")

                st.write("📊 Updated Preview:")
                st.dataframe(user_df.head())

                # Download updated file
                out_file = "updated_with_weights.xlsx"
                user_df.to_excel(out_file, index=False)

                with open(out_file, "rb") as f:
                    st.download_button(
                        "⬇️ Download Updated Excel",
                        f,
                        file_name=out_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.error("❌ Could not detect Size or Length columns. Please check your file.")

# ======================================================
# 🔻 Footer
# ======================================================
st.markdown("""
    <hr>
    <div style='text-align:center; color:gray'>
        © JSC Industries Pvt Ltd | Born to Perform
    </div>
""", unsafe_allow_html=True)
