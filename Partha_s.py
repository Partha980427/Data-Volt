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

# NEW: ISO 4014 dimensional file (Metric Hex Bolt)
iso4014_path = r"G:\My Drive\Streamlite\ISO 4014-2011 Coarse.xlsx"

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

# NEW loader for ISO 4014 dimensional data
@st.cache_data
def load_iso4014_data(file):
    if os.path.exists(file):
        try:
            return pd.read_excel(file)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

df_iso4014 = load_iso4014_data(iso4014_path)

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
    factor = 1.0
    if product == "Hex Cap Screw":
        factor = 1.0 * 0.95
    elif product == "Heavy Hex Bolt":
        factor = 1.0 * 1.05
    elif product == "Heavy Hex Screw":
        factor = 1.0 * 1.1
    elif product == "Threaded Rod":
        factor = 1.0
    volume = 3.1416 * (diameter_mm / 2) ** 2 * length_mm
    weight_kg = volume * density * factor / 1000
    return round(weight_kg, 4)

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
        st.header("📦 Product Database Search Panel")
        if df.empty and df_mechem.empty:
            st.warning("No data available.")
        else:
            # Sidebar filters
            st.sidebar.header("🔍 Filter Options")
            product_types = ["All"] + sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
            product_type = st.sidebar.selectbox("Select Product", product_types)
            series_options = ["Inch","Metric"]
            series = st.sidebar.selectbox("Select Series", series_options)
            
            # =======================
            # 🔹 Auto Select Standard Feature (and include ISO4014 if available)
            # =======================
            # Build dimensional standards from df but ensure ISO 4014 label included if file exists
            dimensional_standards = ["All"] + sorted(df['Standards'].dropna().unique())
            # Insert ISO 4014 label if the file exists and it's not already in the list
            iso_label = "ISO 4014-2011 Coarse"
            if not df_iso4014.empty and iso_label not in dimensional_standards:
                dimensional_standards.append(iso_label)
                dimensional_standards = ["All"] + sorted([s for s in dimensional_standards if s != "All"])
            
            # Provide a default selection for Hex Bolt + Metric (match earlier behavior)
            dimensional_standard_default = "All"
            if product_type == "Hex Bolt":
                if series == "Inch" and "ASME B18.2.1" in dimensional_standards:
                    dimensional_standard_default = "ASME B18.2.1"
                elif series == "Metric" and iso_label in dimensional_standards:
                    dimensional_standard_default = iso_label
            
            # Choose dimensional standard (with default if available)
            try:
                default_index = dimensional_standards.index(dimensional_standard_default)
            except ValueError:
                default_index = 0
            dimensional_standard = st.sidebar.selectbox("Dimensional Standard", dimensional_standards, index=default_index)
            
            # If ISO 4014 selected, show Grade dropdown (A/B); otherwise keep previous UI
            iso_grade_selected = None
            if dimensional_standard == iso_label:
                # Show grade selector in sidebar for ISO 4014
                grade_options = ["All", "A", "B"]
                iso_grade_selected = st.sidebar.selectbox("Grade (ISO 4014)", grade_options, index=0)
            
            size_options = ["All"]
            temp_df = df.copy()
            if product_type != "All":
                temp_df = temp_df[temp_df['Product']==product_type]
            # If ISO 4014 selected, source sizes from df_iso4014 (if available) instead of main df
            if dimensional_standard == iso_label and not df_iso4014.empty:
                try:
                    iso_sizes = df_iso4014['Size'].dropna().unique().tolist() if 'Size' in df_iso4014.columns else []
                    size_options += sorted(iso_sizes, key=size_to_float)
                except Exception:
                    # fallback to original temp_df sizes if iso table different
                    if dimensional_standard != "All":
                        temp_df = temp_df[temp_df['Standards']==dimensional_standard]
                        size_options += sorted(temp_df['Size'].dropna().unique(), key=size_to_float)
            else:
                if dimensional_standard != "All":
                    temp_df = temp_df[temp_df['Standards']==dimensional_standard]
                size_options += sorted(temp_df['Size'].dropna().unique(), key=size_to_float)
            dimensional_size = st.sidebar.selectbox("Dimensional Size", size_options)
            thread_standards = ["All"]
            if series=="Inch":
                thread_standards += ["ASME B1.1"]
            else:
                thread_standards += ["ISO 965-2-98 Coarse","ISO 965-2-98 Fine"]
            thread_standard = st.sidebar.selectbox("Thread Standard", thread_standards)
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

            # ME&CERT filters
            mecert_standards = ["All"]
            if not df_mechem.empty:
                mecert_standards += sorted(df_mechem['Standard'].dropna().unique())
            mecert_standard = st.sidebar.selectbox("ME&CERT Standard", mecert_standards)
            mecert_property_options = ["All"]
            if mecert_standard != "All" and not df_mechem.empty:
                temp_me = df_mechem[df_mechem['Standard']==mecert_standard]
                if "Property class" in temp_me.columns:
                    mecert_property_options += sorted(temp_me['Property class'].dropna().unique())
            mecert_property = st.sidebar.selectbox("Property Class", mecert_property_options)

            # Apply Filters
            filtered_df = df.copy()
            if product_type != "All":
                filtered_df = filtered_df[filtered_df['Product']==product_type]
            if dimensional_standard != "All" and dimensional_standard != iso_label:
                filtered_df = filtered_df[filtered_df['Standards']==dimensional_standard]
            if dimensional_size != "All":
                filtered_df = filtered_df[filtered_df['Size']==dimensional_size]

            # If ISO 4014 is selected, optionally merge or display its data (only for Hex Bolt)
            if dimensional_standard == iso_label and not df_iso4014.empty:
                # Filter iso df by grade if grade column exists
                iso_display = df_iso4014.copy()
                if iso_grade_selected and iso_grade_selected != "All" and "Grade" in iso_display.columns:
                    iso_display = iso_display[iso_display['Grade']==iso_grade_selected]
                # If user selected product Hex Bolt, restrict to rows for hex bolt if such a column exists
                if "Product" in iso_display.columns:
                    iso_display = iso_display[iso_display['Product']==product_type] if product_type!="All" else iso_display
                # If a dimensional_size filter applied, filter iso_display
                if dimensional_size != "All" and "Size" in iso_display.columns:
                    iso_display = iso_display[iso_display['Size']==dimensional_size]
                # Append iso_display to filtered_df view so user sees both sources
                if not iso_display.empty:
                    # unify columns: ensure no errors when appending
                    try:
                        display_combined = pd.concat([filtered_df, iso_display], ignore_index=True, sort=False)
                        st.subheader(f"Found {len(display_combined)} records (including ISO 4014 if applicable)")
                        st.dataframe(display_combined)
                    except Exception:
                        st.subheader(f"Found {len(filtered_df)} standard records")
                        st.dataframe(filtered_df)
                else:
                    st.subheader(f"Found {len(filtered_df)} records")
                    st.dataframe(filtered_df)
            else:
                st.subheader(f"Found {len(filtered_df)} records")
                st.dataframe(filtered_df)

            if thread_standard != "All" and not df_thread.empty:
                df_thread_filtered = df_thread.copy()
                if thread_size != "All":
                    df_thread_filtered = df_thread_filtered[df_thread_filtered['Thread']==thread_size]
                if thread_class != "All":
                    df_thread_filtered = df_thread_filtered[df_thread_filtered['Class']==thread_class]
                st.subheader(f"Thread Data: {thread_standard}")
                st.dataframe(df_thread_filtered)

            filtered_mecert_df = df_mechem.copy()
            if mecert_standard != "All":
                filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Standard']==mecert_standard]
            if mecert_property != "All":
                filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Property class']==mecert_property]
            st.subheader(f"ME&CERT Records: {len(filtered_mecert_df)}")
            st.dataframe(filtered_mecert_df)

            if st.button("📥 Download All Filtered Data"):
                wb = Workbook()
                ws_dim = wb.active
                ws_dim.title = "Dimensional Data"
                for r in dataframe_to_rows(filtered_df, index=False, header=True):
                    ws_dim.append(r)
                if thread_standard != "All" and not df_thread.empty:
                    ws_thread = wb.create_sheet("Thread Data")
                    for r in dataframe_to_rows(df_thread_filtered, index=False, header=True):
                        ws_thread.append(r)
                if not filtered_mecert_df.empty:
                    ws_me = wb.create_sheet("ME&CERT Data")
                    for r in dataframe_to_rows(filtered_mecert_df, index=False, header=True):
                        ws_me.append(r)
                # If ISO4014 selected and available, add a sheet for it
                if dimensional_standard == iso_label and not df_iso4014.empty:
                    ws_iso = wb.create_sheet("ISO4014 Data")
                    try:
                        for r in dataframe_to_rows(df_iso4014, index=False, header=True):
                            ws_iso.append(r)
                    except Exception:
                        pass
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                wb.save(temp_file.name)
                temp_file.close()
                with open(temp_file.name, "rb") as f:
                    st.download_button("⬇️ Download Excel", f, file_name="Filtered_Fastener_Data.xlsx", 
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif title == "🧮 Calculations":
        st.header("🧮 Engineering Calculations")
        # ------------------------
        # Manual Weight Calculator
        # ------------------------
        product_options = sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud"])
        selected_product = st.selectbox("Select Product", product_options)
        series = st.selectbox("Select Series", ["Inch", "Metric"])
        metric_type = st.selectbox("Select Thread Type", ["Coarse", "Fine"]) if series=="Metric" else None
        selected_standard = "ASME B1.1" if series=="Inch" else ("ISO 965-2-98 Coarse" if metric_type=="Coarse" else "ISO 965-2-98 Fine")
        st.info(f"📏 Standard: **{selected_standard}** (used only for pitch diameter)")

        # NEW: For calculations, allow selecting dimensional standard when needed (default behavior preserved)
        calc_dimensional_standards = ["All"] + sorted(df['Standards'].dropna().unique())
        iso_label_calc = "ISO 4014-2011 Coarse"
        if not df_iso4014.empty and iso_label_calc not in calc_dimensional_standards:
            calc_dimensional_standards.append(iso_label_calc)
            calc_dimensional_standards = ["All"] + sorted([s for s in calc_dimensional_standards if s != "All"])
        # Auto-default when product Hex Bolt + Metric
        calc_dim_default = "All"
        if selected_product == "Hex Bolt":
            if series == "Inch" and "ASME B18.2.1" in calc_dimensional_standards:
                calc_dim_default = "ASME B18.2.1"
            elif series == "Metric" and iso_label_calc in calc_dimensional_standards:
                calc_dim_default = iso_label_calc
        try:
            calc_dim_index = calc_dimensional_standards.index(calc_dim_default)
        except ValueError:
            calc_dim_index = 0
        calc_dimensional_standard = st.selectbox("Dimensional Standard (for calculations)", calc_dimensional_standards, index=calc_dim_index)

        # If ISO 4014 selected here, show grade select for calculations
        calc_iso_grade = None
        if calc_dimensional_standard == iso_label_calc:
            calc_iso_grade = st.selectbox("Select Grade (ISO 4014)", ["All", "A", "B"], index=0)

        df_thread = load_thread_data(thread_files[selected_standard])
        size_options = sorted(df_thread["Thread"].dropna().unique()) if not df_thread.empty else []
        selected_size = st.selectbox("Select Size", size_options)
        length_unit = st.selectbox("Select Length Unit", ["mm","inch","meter","ft"])
        length_val = st.number_input("Enter Length", min_value=0.1, step=0.1)
        dia_type = st.selectbox("Select Diameter Type", ["Body Diameter", "Pitch Diameter"])
        diameter_mm = None
        if dia_type == "Body Diameter":
            body_dia = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1)
            diameter_mm = body_dia*25.4 if length_unit=="inch" else body_dia
        else:
            # If dimensional standard is ISO 4014 (metric hex bolt) use df_iso4014 to get pitch/body diameters if present
            if calc_dimensional_standard == iso_label_calc and not df_iso4014.empty:
                # Try to find size row in iso df
                try:
                    iso_rows = df_iso4014.copy()
                    if calc_iso_grade and calc_iso_grade != "All" and "Grade" in iso_rows.columns:
                        iso_rows = iso_rows[iso_rows["Grade"] == calc_iso_grade]
                    # match by Size column if exists, otherwise fallback to thread table
                    if "Size" in iso_rows.columns:
                        row = iso_rows[iso_rows["Size"] == selected_size]
                        if not row.empty:
                            # Prefer "Pitch Diameter (Min)" if present, else "Body Diameter" or similar columns
                            if "Pitch Diameter (Min)" in row.columns:
                                pitch_val = row["Pitch Diameter (Min)"].values[0]
                                diameter_mm = pitch_val  # ISO is metric, so assume mm
                            elif "Body Diameter" in row.columns:
                                diameter_mm = row["Body Diameter"].values[0]
                    # if still not found, fall back to thread table lookup below
                except Exception:
                    diameter_mm = None

            if diameter_mm is None:
                if not df_thread.empty:
                    row = df_thread[df_thread["Thread"]==selected_size]
                    if not row.empty:
                        pitch_val = row["Pitch Diameter (Min)"].values[0]
                        diameter_mm = pitch_val if series=="Metric" else pitch_val*25.4
                    else:
                        st.warning("⚠️ Pitch Diameter not found.")

        if st.button("Calculate Weight"):
            length_mm = length_val
            if length_unit=="inch":
                length_mm *= 25.4
            elif length_unit=="meter":
                length_mm *= 1000
            elif length_unit=="ft":
                length_mm *= 304.8
            if diameter_mm is None:
                st.error("❌ Provide diameter.")
            else:
                weight_kg = calculate_weight(selected_product, diameter_mm, length_mm)
                st.success(f"✅ Estimated Weight: **{weight_kg} Kg**")

        # ------------------------
        # Batch Weight Calculator
        # ------------------------
        st.subheader("Batch Weight Calculator")
        batch_selected_product = st.selectbox("Select Product for Batch", product_options, key="batch_product")
        batch_series = st.selectbox("Select Series", ["Inch", "Metric"], key="batch_series")
        batch_metric_type = st.selectbox("Select Thread Type", ["Coarse", "Fine"], key="batch_metric_type") if batch_series=="Metric" else None
        batch_standard = "ASME B1.1" if batch_series=="Inch" else ("ISO 965-2-98 Coarse" if batch_metric_type=="Coarse" else "ISO 965-2-98 Fine")
        st.info(f"📏 Standard: **{batch_standard}** (used only for pitch diameter)")
        # Batch dimensional standard selector (to allow ISO 4014 usage in batch)
        batch_dimensional_standards = ["All"] + sorted(df['Standards'].dropna().unique())
        if not df_iso4014.empty and iso_label_calc not in batch_dimensional_standards:
            batch_dimensional_standards.append(iso_label_calc)
            batch_dimensional_standards = ["All"] + sorted([s for s in batch_dimensional_standards if s != "All"])
        # default for batch
        batch_dim_def = "All"
        if batch_selected_product == "Hex Bolt":
            if batch_series == "Inch" and "ASME B18.2.1" in batch_dimensional_standards:
                batch_dim_def = "ASME B18.2.1"
            elif batch_series == "Metric" and iso_label_calc in batch_dimensional_standards:
                batch_dim_def = iso_label_calc
        try:
            batch_dim_index = batch_dimensional_standards.index(batch_dim_def)
        except ValueError:
            batch_dim_index = 0
        batch_dimensional_standard = st.selectbox("Dimensional Standard for Batch", batch_dimensional_standards, index=batch_dim_index)

        # If ISO 4014 selected for batch, show grade choice
        batch_iso_grade = None
        if batch_dimensional_standard == iso_label_calc:
            batch_iso_grade = st.selectbox("Batch Grade (ISO 4014)", ["All", "A", "B"], key="batch_iso_grade")

        batch_length_unit = st.selectbox("Select Length Unit", ["mm","inch","meter","FT"], key="batch_length_unit")
        uploaded_file_batch = st.file_uploader("Upload Excel/CSV for Batch", type=["xlsx","csv"], key="batch_file")

        batch_class = None
        if batch_series=="Inch" and not df_thread.empty:
            df_thread_batch = load_thread_data(thread_files[batch_standard])
            class_options = ["All"]
            if "Class" in df_thread_batch.columns:
                class_options += sorted(df_thread_batch["Class"].dropna().unique())
            batch_class = st.selectbox("Select Class", class_options, key="batch_class")

        if uploaded_file_batch:
            batch_df = pd.read_excel(uploaded_file_batch) if uploaded_file_batch.name.endswith(".xlsx") else pd.read_csv(uploaded_file_batch)
            st.write("Uploaded File Preview:")
            st.dataframe(batch_df.head())
            required_cols = ["Product","Size","Length"]
            if all(col in batch_df.columns for col in required_cols):
                if st.button("Calculate Batch Weights", key="calc_batch_weights"):
                    df_thread_batch = load_thread_data(thread_files[batch_standard])
                    df_dim_batch = df[df['Product']==batch_selected_product]
                    weight_col_name = "Weight/pc (Kg)"
                    if weight_col_name not in batch_df.columns:
                        batch_df[weight_col_name] = 0

                    for idx, row in batch_df.iterrows():
                        prod = row["Product"]
                        size_val = row["Size"]
                        length_val = float(row["Length"])
                        # Convert length
                        length_mm = length_val
                        if batch_length_unit=="inch":
                            length_mm *= 25.4
                        elif batch_length_unit=="meter":
                            length_mm *= 1000
                        elif batch_length_unit=="FT":
                            length_mm *= 304.8

                        # Determine diameter using Size + Class for Inch or dimensional standard
                        diameter_mm = None
                        dim_row = df_dim_batch[df_dim_batch["Size"]==size_val] if not df_dim_batch.empty else pd.DataFrame()
                        if not dim_row.empty and "Body Diameter" in dim_row.columns:
                            diameter_mm = dim_row["Body Diameter"].values[0]

                        thread_row = pd.DataFrame()
                        if batch_series=="Inch":
                            if batch_class != "All" and df_thread_batch is not None:
                                thread_row = df_thread_batch[(df_thread_batch["Thread"]==size_val) & (df_thread_batch["Class"]==batch_class)]
                            else:
                                thread_row = df_thread_batch[df_thread_batch["Thread"]==size_val]
                        else:
                            thread_row = df_thread_batch[df_thread_batch["Thread"]==size_val]

                        if not thread_row.empty and "Pitch Diameter (Min)" in thread_row.columns:
                            diameter_mm = thread_row["Pitch Diameter (Min)"].values[0]
                            if batch_series=="Inch":
                                diameter_mm *= 25.4

                        # NEW: If user selected ISO 4014 for batch, try to obtain diameter from df_iso4014 and consider grade filter
                        if batch_dimensional_standard == iso_label_calc and not df_iso4014.empty:
                            try:
                                iso_rows = df_iso4014.copy()
                                if batch_iso_grade and batch_iso_grade != "All" and "Grade" in iso_rows.columns:
                                    iso_rows = iso_rows[iso_rows["Grade"] == batch_iso_grade]
                                if "Size" in iso_rows.columns:
                                    iso_match = iso_rows[iso_rows["Size"] == size_val]
                                    if not iso_match.empty:
                                        if "Pitch Diameter (Min)" in iso_match.columns:
                                            diameter_mm = iso_match["Pitch Diameter (Min)"].values[0]
                                        elif "Body Diameter" in iso_match.columns:
                                            diameter_mm = iso_match["Body Diameter"].values[0]
                            except Exception:
                                pass

                        if diameter_mm is None:
                            try:
                                diameter_mm = float(size_val)
                            except:
                                diameter_mm = 0

                        # Calculate weight
                        weight = calculate_weight(prod, diameter_mm, length_mm)
                        batch_df.at[idx, weight_col_name] = weight

                    st.dataframe(batch_df)
                    # Save Excel safely
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                    batch_df.to_excel(temp_file.name, index=False)
                    temp_file.close()
                    with open(temp_file.name,"rb") as f:
                        st.download_button("⬇️ Download Batch Excel", f, file_name="Batch_Weight.xlsx",
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ======================================================
    # 🔹 PiU AI Assistant Section (UPGRADED)
    # ======================================================
    elif title == "🤖 PiU (AI Assistant)":
        st.header("🤖 PiU – AI Assistant (Optional)")
        st.info("You can ask questions about your products, threads, or ME&CERT data.")

        ai_query = st.text_area("Enter your question for the AI:")

        if st.button("Ask AI"):
            if ai_query.strip() == "":
                st.warning("Please type a question.")
            else:
                response_parts = []

                # Search in Product Database
                if df is not None and not df.empty:
                    mask_prod = df.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                    filtered_prod = df[mask_prod]
                    if not filtered_prod.empty:
                        response_parts.append(f"✅ Found {len(filtered_prod)} matching Product records:\n{filtered_prod.to_string(index=False)}")

                # Search in Thread Data
                for file in thread_files.values():
                    df_thread_temp = load_thread_data(file)
                    if not df_thread_temp.empty:
                        mask_thread = df_thread_temp.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                        filtered_thread = df_thread_temp[mask_thread]
                        if not filtered_thread.empty:
                            response_parts.append(f"🔧 Found {len(filtered_thread)} matching Thread records in {file}:\n{filtered_thread.to_string(index=False)}")

                # Search in ME&CERT
                if df_mechem is not None and not df_mechem.empty:
                    mask_me = df_mechem.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                    filtered_me = df_mechem[mask_me]
                    if not filtered_me.empty:
                        response_parts.append(f"🧪 Found {len(filtered_me)} ME&CERT records:\n{filtered_me.to_string(index=False)}")

                # Also search ISO 4014 if available
                if not df_iso4014.empty:
                    try:
                        mask_iso = df_iso4014.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                        filtered_iso = df_iso4014[mask_iso]
                        if not filtered_iso.empty:
                            response_parts.append(f"📐 Found {len(filtered_iso)} ISO 4014 records:\n{filtered_iso.to_string(index=False)}")
                    except Exception:
                        pass

                if response_parts:
                    response = "\n\n".join(response_parts)
                else:
                    response = "❌ Sorry, no matching data found."

                st.text_area("AI Response:", value=response, height=400)

    st.markdown("<hr>")
    if st.button("Back to Home"):
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
