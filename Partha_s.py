import streamlit as st
import pandas as pd
import openpyxl
from fractions import Fraction
import math
from io import BytesIO

# ======================================================
# 🔹 Fractional size parser
# ======================================================
def parse_size_in_inches(size):
    if isinstance(size, (int, float)):
        return float(size)
    s = str(size).strip()
    try:
        if "-" in s:
            whole, frac = s.split("-")
            return float(whole) + float(Fraction(frac))
        else:
            return float(Fraction(s))
    except:
        return None

# ======================================================
# 🔹 Weight calculation function
# ======================================================
def calculate_weight(product, size_str, length_mm):
    dia_mm = parse_size_in_inches(size_str) * 25.4  # inches -> mm
    density = 0.00785  # g/mm³ steel

    if product == "Hex Bolt":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm
    elif product == "Heavy Hex Bolt":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm * 1.05
    elif product == "Hex Cap Screw":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm * 0.95
    elif product == "Heavy Hex Screw":
        vol = math.pi * (dia_mm / 2) ** 2 * length_mm * 1.1
    else:
        return None

    return round(vol * density / 1000, 3)  # kg

# ======================================================
# ⚖️ Manual Weight Calculator
# ======================================================
st.title("🔩 Bolt & Rod Weight Calculator")

product_type = st.selectbox(
    "Select Product Type",
    ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screw", "Heavy Hex Screw"]
)

weight_col_name = st.text_input("Enter column name for Weight/pc (Kg):", "Weight/pc (Kg)")
weight_col_index = st.number_input(
    "Enter column index to write Weight/pc (Kg) (numeric, e.g., 3 = C column)",
    min_value=1, value=3
)

uploaded_files = st.file_uploader(
    "Upload Excel file(s) to update weights",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        wb = openpyxl.load_workbook(uploaded_file)
        ws = wb.active

        # Auto-detect Size and Length columns
        headers = {cell.value: idx for idx, cell in enumerate(ws[1], 1)}
        size_cols = [name for name in headers if "size" in str(name).lower()]
        length_cols = [name for name in headers if "length" in str(name).lower()]

        if not size_cols or not length_cols:
            st.warning(f"{uploaded_file.name} missing Size or Length column. Skipping.")
            continue

        size_col_index_detected = headers[size_cols[0]]
        length_col_index_detected = headers[length_cols[0]]

        # Add weight column if not exist at specified index
        if ws.cell(row=1, column=weight_col_index).value != weight_col_name:
            ws.insert_cols(weight_col_index)
            ws.cell(row=1, column=weight_col_index, value=weight_col_name)

        # Calculate weight row by row
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            size_val = row[size_col_index_detected - 1].value
            length_val = row[length_col_index_detected - 1].value
            if size_val is not None and length_val is not None:
                row[weight_col_index - 1].value = calculate_weight(product_type, size_val, length_val)

        # Save updated Excel to in-memory BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        st.download_button(
            label=f"Download Updated {uploaded_file.name}",
            data=output,
            file_name=f"updated_{uploaded_file.name}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
