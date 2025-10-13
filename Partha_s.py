import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile

# ======================================================
# 🔹 Enhanced Configuration & Error Handling
# ======================================================
def safe_load_excel_file(path_or_url):
    """Enhanced loading with better error handling"""
    try:
        if path_or_url.startswith('http'):
            return pd.read_excel(path_or_url)
        else:
            if os.path.exists(path_or_url):
                return pd.read_excel(path_or_url)
            else:
                st.error(f"File not found: {path_or_url}")
                return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading {path_or_url}: {str(e)}")
        return pd.DataFrame()

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        "selected_section": None,
        "batch_result_df": None,
        "ai_history": [],
        "current_filters": {}
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_thread_data(standard, thread_size=None, thread_class=None):
    """Centralized thread data retrieval"""
    if standard not in thread_files:
        return pd.DataFrame()
    
    df_thread = load_thread_data(thread_files[standard])
    if df_thread.empty:
        return pd.DataFrame()
    
    # Apply filters
    if thread_size and "Thread" in df_thread.columns:
        df_thread = df_thread[df_thread["Thread"] == thread_size]
    if thread_class and "Class" in df_thread.columns:
        df_thread = df_thread[df_thread["Class"] == thread_class]
    
    return df_thread

# ======================================================
# 🔹 Page Setup
# ======================================================
st.set_page_config(page_title="JSC Industries – Advanced Fastener Intelligence", layout="wide")
st.markdown("**App Version: 2.6 – ISO 4014 Integrated & Batch Weight Calculator ✅**")

# Initialize session state
initialize_session_state()

# ======================================================
# 🔹 Paths & Files
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"
me_chem_path = r"Mechanical and Chemical.xlsx"

# ISO 4014 paths - local and Google Sheets
iso4014_local_path = r"G:\My Drive\Streamlite\ISO 4014 Hex Bolt.xlsx"
iso4014_file_url = "https://docs.google.com/spreadsheets/d/1d2hANwoMhuzwyKJ72c125Uy0ujB6QsV_/export?format=xlsx"

thread_files = {
    "ASME B1.1": "ASME B1.1 New.xlsx",
    "ISO 965-2-98 Coarse": "ISO 965-2-98 Coarse.xlsx",
    "ISO 965-2-98 Fine": "ISO 965-2-98 Fine.xlsx",
}

# ======================================================
# 🔹 Data Loading with Enhanced Error Handling
# ======================================================
@st.cache_data
def load_excel_file(path_or_url):
    try:
        return pd.read_excel(path_or_url)
    except Exception as e:
        st.warning(f"Failed to load {path_or_url}: {e}")
        return pd.DataFrame()

# Load main data
df = safe_load_excel_file(url) if url else safe_load_excel_file(local_excel_path)
df_mechem = safe_load_excel_file(me_chem_path)

# Load ISO 4014 data - try Google Sheets first, then fallback to local
df_iso4014 = safe_load_excel_file(iso4014_file_url)  # Try Google Sheets first
if df_iso4014.empty:
    st.info("🔄 Online ISO 4014 file not accessible, trying local version...")
    df_iso4014 = safe_load_excel_file(iso4014_local_path)  # Fallback to local file

if not df_iso4014.empty:
    df_iso4014['Product'] = "Hex Bolt"
    df_iso4014['Standards'] = "ISO-4014-2011"
    if 'Grade' not in df_iso4014.columns:
        df_iso4014['Grade'] = "A"
    st.success(f"✅ ISO 4014 data loaded successfully with {len(df_iso4014)} records")
else:
    st.warning("⚠️ Could not load ISO 4014 data from any source")

@st.cache_data
def load_thread_data(file):
    if os.path.exists(file):
        return pd.read_excel(file)
    else:
        st.warning(f"Thread file {file} not found!")
        return pd.DataFrame()

# ======================================================
# 🔹 Enhanced Helper Functions
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
    """Enhanced with validation"""
    if diameter_mm <= 0 or length_mm <= 0:
        st.error("❌ Diameter and length must be positive values")
        return 0
    
    try:
        density = 0.00785  # g/mm^3
        V_shank = 3.1416 * (diameter_mm / 2) ** 2 * length_mm
        head_volume = 0
        product_lower = product.lower()
        if "hex cap" in product_lower:
            a = 1.5 * diameter_mm
            h = 0.8 * diameter_mm
            head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
        elif "heavy hex" in product_lower:
            a = 2 * diameter_mm
            h = 1.2 * diameter_mm
            head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
        elif "socket head" in product_lower or "low head cap" in product_lower:
            h = 0.6 * diameter_mm
            r = 0.8 * diameter_mm / 2
            head_volume = 3.1416 * r ** 2 * h
        elif "button head" in product_lower:
            h = 0.4 * diameter_mm
            r = 0.9 * diameter_mm / 2
            head_volume = 3.1416 * r ** 2 * h
        else:
            head_volume = 0.5 * 3.1416 * (diameter_mm / 2) ** 2 * (0.5 * diameter_mm)
        total_volume = V_shank + head_volume
        weight_kg = total_volume * density / 1000
        return round(weight_kg, 4)
    except Exception as e:
        st.error(f"Calculation error: {str(e)}")
        return 0

def convert_length_to_mm(length_val, unit):
    """Enhanced length conversion with validation"""
    try:
        length_val = float(length_val)
        unit = unit.lower()
        if unit=="inch":
            return length_val * 25.4
        elif unit=="meter":
            return length_val * 1000
        elif unit=="ft":
            return length_val * 304.8
        return length_val
    except ValueError:
        st.error("❌ Invalid length value")
        return 0

def show_loading_placeholder(message="🔄 Processing your request..."):
    """Show loading state"""
    placeholder = st.empty()
    placeholder.info(message)
    return placeholder

def clear_loading(placeholder):
    """Clear loading placeholder"""
    placeholder.empty()

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
# 🔹 Product Database Section
# ======================================================
def show_product_database():
    st.header("📦 Product Database Search Panel")
    if df.empty and df_mechem.empty and df_iso4014.empty:
        st.warning("No data available.")
        return
    
    st.sidebar.header("🔍 Filter Options")
    product_types = ["All"] + sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud", "Hex Bolt"])
    product_type = st.sidebar.selectbox("Select Product", product_types)
    
    series_options = ["Inch", "Metric"]
    series = st.sidebar.selectbox("Select Series", series_options)
    
    dimensional_standards = ["All"] + sorted(df['Standards'].dropna().unique())
    if "Metric" in series and "ISO 4014" not in dimensional_standards:
        dimensional_standards.append("ISO 4014")
    dimensional_standard = st.sidebar.selectbox("Dimensional Standard", dimensional_standards)
    
    temp_df = df.copy()
    if dimensional_standard=="ISO 4014":
        temp_df = df_iso4014
    else:
        if product_type != "All":
            temp_df = temp_df[temp_df['Product']==product_type]
        if dimensional_standard != "All":
            temp_df = temp_df[temp_df['Standards']==dimensional_standard]
    
    size_options = ["All"] + sorted(temp_df['Size'].dropna().unique(), key=size_to_float)
    dimensional_size = st.sidebar.selectbox("Dimensional Size", size_options)
    
    # Thread
    thread_standards = ["All"]
    if series=="Inch":
        thread_standards += ["ASME B1.1"]
    else:
        thread_standards += ["ISO 965-2-98 Coarse","ISO 965-2-98 Fine"]
    thread_standard = st.sidebar.selectbox("Thread Standard", thread_standards)
    
    thread_size_options = ["All"]
    thread_class_options = ["All"]
    if thread_standard != "All":
        df_thread = get_thread_data(thread_standard)
        if not df_thread.empty:
            if "Thread" in df_thread.columns:
                thread_size_options += sorted(df_thread['Thread'].dropna().unique())
            if "Class" in df_thread.columns:
                thread_class_options += sorted(df_thread['Class'].dropna().unique())
    thread_size = st.sidebar.selectbox("Thread Size", thread_size_options)
    thread_class = st.sidebar.selectbox("Class", thread_class_options)
    
    # ME&CERT
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
    
    # Apply filters
    filtered_df = temp_df.copy()
    if dimensional_size != "All":
        filtered_df = filtered_df[filtered_df['Size']==dimensional_size]
    
    st.subheader(f"Found {len(filtered_df)} records")
    st.dataframe(filtered_df, use_container_width=True)
    
    # Thread data
    if thread_standard != "All":
        df_thread_filtered = get_thread_data(thread_standard, thread_size, thread_class)
        if not df_thread_filtered.empty:
            st.subheader(f"Thread Data: {thread_standard}")
            st.dataframe(df_thread_filtered, use_container_width=True)
    
    # ME&CERT data
    filtered_mecert_df = df_mechem.copy()
    if mecert_standard != "All":
        filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Standard']==mecert_standard]
    if mecert_property != "All":
        filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Property class']==mecert_property]
    st.subheader(f"ME&CERT Records: {len(filtered_mecert_df)}")
    st.dataframe(filtered_mecert_df, use_container_width=True)
    
    # Download all filtered data
    if st.button("📥 Download All Filtered Data"):
        loading_placeholder = show_loading_placeholder("📥 Preparing download...")
        try:
            wb = Workbook()
            ws_dim = wb.active
            ws_dim.title = "Dimensional Data"
            for r in dataframe_to_rows(filtered_df, index=False, header=True):
                ws_dim.append(r)
            
            if thread_standard != "All":
                df_thread_filtered = get_thread_data(thread_standard, thread_size, thread_class)
                if not df_thread_filtered.empty:
                    ws_thread = wb.create_sheet("Thread Data")
                    for r in dataframe_to_rows(df_thread_filtered, index=False, header=True):
                        ws_thread.append(r)
            
            if not filtered_mecert_df.empty:
                ws_me = wb.create_sheet("ME&CERT Data")
                for r in dataframe_to_rows(filtered_mecert_df, index=False, header=True):
                    ws_me.append(r)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            wb.save(temp_file.name)
            temp_file.close()
            
            with open(temp_file.name, "rb") as f:
                st.download_button("⬇️ Download Excel", f, file_name="Filtered_Fastener_Data.xlsx", 
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            clear_loading(loading_placeholder)
            st.success("✅ Download ready!")
            
        except Exception as e:
            clear_loading(loading_placeholder)
            st.error(f"❌ Error preparing download: {str(e)}")

# ======================================================
# 🔹 Calculations Section (with Batch + ISO 4014)
# ======================================================
def show_calculations():
    st.header("🧮 Engineering Calculations")
    
    # Single Item Calculation
    st.subheader("Single Item Weight Calculation")
    product_options = sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud", "Hex Bolt"])
    selected_product = st.selectbox("Select Product", product_options)
    series = st.selectbox("Select Series", ["Inch","Metric"])
    metric_type = st.selectbox("Select Thread Type", ["Coarse","Fine"]) if series=="Metric" else None
    standard_options = ["ASME B1.1","ISO 965-2-98 Coarse","ISO 965-2-98 Fine","ISO 4014"]
    selected_standard = st.selectbox("Select Standard", standard_options)
    
    # Thread data
    df_thread = get_thread_data(selected_standard)
    
    size_options = []
    if selected_standard=="ISO 4014":
        size_options = sorted(df_iso4014['Size'].dropna().unique())
    elif not df_thread.empty:
        size_options = sorted(df_thread['Thread'].dropna().unique())
    selected_size = st.selectbox("Select Size", size_options) if size_options else st.selectbox("Select Size", [])
    
    length_unit = st.selectbox("Select Length Unit", ["mm","inch","meter","ft"])
    length_val = st.number_input("Enter Length", min_value=0.1, step=0.1, value=10.0)
    dia_type = st.selectbox("Select Diameter Type", ["Body Diameter","Pitch Diameter"])
    
    diameter_mm = None
    if selected_standard=="ISO 4014" and selected_size:
        row_iso = df_iso4014[df_iso4014['Size']==selected_size]
        if not row_iso.empty and 'Body Diameter' in row_iso.columns:
            diameter_mm = row_iso['Body Diameter'].values[0]
    elif dia_type=="Pitch Diameter" and not df_thread.empty and selected_size:
        row = df_thread[df_thread["Thread"]==selected_size]
        if not row.empty and "Pitch Diameter (Min)" in row.columns:
            pitch_val = row["Pitch Diameter (Min)"].values[0]
            diameter_mm = pitch_val if series=="Metric" else pitch_val*25.4
    elif dia_type=="Body Diameter":
        body_dia = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1, value=5.0)
        diameter_mm = body_dia*25.4 if length_unit=="inch" else body_dia

    class_options_manual = ["1A","2A","3A"] if series=="Inch" else ["6g","6H"]
    selected_class_manual = st.selectbox("Select Class (Manual Calculation)", class_options_manual)

    if st.button("Calculate Weight"):
        if diameter_mm is None:
            st.error("❌ Please provide diameter information.")
        else:
            length_mm = convert_length_to_mm(length_val, length_unit)
            weight_kg = calculate_weight(selected_product, diameter_mm, length_mm)
            if weight_kg > 0:
                st.success(f"✅ Estimated Weight: **{weight_kg} Kg** (Class: {selected_class_manual})")

    # -------------------------
    # Batch Weight Calculator
    # -------------------------
    st.subheader("Batch Weight Calculator")
    batch_selected_product = st.selectbox("Select Product for Batch", product_options, key="batch_product")
    batch_series = st.selectbox("Select Series", ["Inch","Metric"], key="batch_series")
    batch_standard = st.selectbox("Select Standard for Batch", standard_options, key="batch_standard")
    batch_length_unit = st.selectbox("Select Length Unit", ["mm","inch","meter","ft"], key="batch_length_unit")
    uploaded_file_batch = st.file_uploader("Upload Excel/CSV for Batch", type=["xlsx","csv"], key="batch_file")

    batch_class = None
    df_thread_batch = get_thread_data(batch_standard)
    if not df_thread_batch.empty:
        class_options = ["All"]
        if "Class" in df_thread_batch.columns:
            class_options += sorted(df_thread_batch["Class"].dropna().unique())
        batch_class = st.selectbox("Select Class", class_options, key="batch_class")

    if uploaded_file_batch:
        try:
            batch_df = pd.read_excel(uploaded_file_batch) if uploaded_file_batch.name.endswith(".xlsx") else pd.read_csv(uploaded_file_batch)
            st.write("Uploaded File Preview:")
            st.dataframe(batch_df.head())
            required_cols = ["Product","Size","Length"]
            if all(col in batch_df.columns for col in required_cols):
                if st.button("Calculate Batch Weights", key="calc_batch_weights"):
                    loading_placeholder = show_loading_placeholder("🧮 Calculating batch weights...")
                    df_dim_batch = df.copy()
                    weight_col_name = "Weight/pc (Kg)"
                    if weight_col_name not in batch_df.columns:
                        batch_df[weight_col_name] = 0.0
                    
                    success_count = 0
                    for idx, row in batch_df.iterrows():
                        try:
                            prod = row["Product"]
                            size_val = str(row["Size"])
                            length_val = float(row["Length"])
                            length_mm = convert_length_to_mm(length_val, batch_length_unit)
                            diameter_mm = None

                            if batch_standard=="ISO 4014":
                                row_iso = df_iso4014[df_iso4014['Size']==size_val]
                                if not row_iso.empty and 'Body Diameter' in row_iso.columns:
                                    diameter_mm = row_iso['Body Diameter'].values[0]
                            elif not df_thread_batch.empty:
                                thread_row = df_thread_batch[df_thread_batch["Thread"]==size_val]
                                if not thread_row.empty and "Pitch Diameter (Min)" in thread_row.columns:
                                    diameter_mm = thread_row["Pitch Diameter (Min)"].values[0]
                                    if batch_series=="Inch":
                                        diameter_mm *= 25.4
                            
                            if diameter_mm is None:
                                try:
                                    diameter_mm = float(size_val)
                                except:
                                    diameter_mm = 0
                            
                            weight = calculate_weight(prod, diameter_mm, length_mm)
                            batch_df.at[idx, weight_col_name] = weight
                            if weight > 0:
                                success_count += 1
                                
                        except Exception as e:
                            st.warning(f"Error processing row {idx}: {str(e)}")
                            batch_df.at[idx, weight_col_name] = 0

                    st.session_state.batch_result_df = batch_df
                    clear_loading(loading_placeholder)
                    st.success(f"✅ Successfully calculated weights for {success_count}/{len(batch_df)} items")
                    st.dataframe(batch_df)
                    
            else:
                st.error(f"❌ Required columns missing. Need: {required_cols}")
        except Exception as e:
            st.error(f"❌ Error reading uploaded file: {str(e)}")

    if st.session_state.batch_result_df is not None:
        try:
            temp_file_batch = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            st.session_state.batch_result_df.to_excel(temp_file_batch.name, index=False)
            temp_file_batch.close()
            with open(temp_file_batch.name,"rb") as f:
                st.download_button("⬇️ Download Batch Excel", f, file_name="Batch_Weight.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"❌ Error creating download file: {str(e)}")

# ======================================================
# 🔹 AI Assistant Section
# ======================================================
def show_ai_assistant():
    st.header("🤖 PiU – AI Assistant")
    st.info("You can ask questions about your products, threads, or ME&CERT data.")
    ai_query = st.text_area("Enter your question for the AI:")
    
    if st.button("Ask AI"):
        if not ai_query.strip():
            st.warning("Please type a question.")
        else:
            loading_placeholder = show_loading_placeholder("🤖 Searching through data...")
            response_parts = []
            
            # Search in main product data
            if not df.empty:
                try:
                    mask_prod = df.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                    filtered_prod = df[mask_prod]
                    if not filtered_prod.empty:
                        response_parts.append(f"✅ Found {len(filtered_prod)} Product records:\n{filtered_prod.to_string(index=False)}")
                except Exception as e:
                    st.warning(f"Error searching product data: {str(e)}")
            
            # Search in thread data
            for standard_name in thread_files.keys():
                try:
                    df_thread_temp = get_thread_data(standard_name)
                    if not df_thread_temp.empty:
                        mask_thread = df_thread_temp.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                        filtered_thread = df_thread_temp[mask_thread]
                        if not filtered_thread.empty:
                            response_parts.append(f"🔧 Found {len(filtered_thread)} Thread records in {standard_name}:\n{filtered_thread.to_string(index=False)}")
                except Exception as e:
                    st.warning(f"Error searching thread data for {standard_name}: {str(e)}")
            
            # Search in ME&CERT data
            if not df_mechem.empty:
                try:
                    mask_me = df_mechem.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                    filtered_me = df_mechem[mask_me]
                    if not filtered_me.empty:
                        response_parts.append(f"🧪 Found {len(filtered_me)} ME&CERT records:\n{filtered_me.to_string(index=False)}")
                except Exception as e:
                    st.warning(f"Error searching ME&CERT data: {str(e)}")
            
            clear_loading(loading_placeholder)
            response = "\n\n".join(response_parts) if response_parts else "❌ Sorry, no matching data found for your query."
            st.text_area("AI Response:", value=response, height=400)

# ======================================================
# 🔹 Section Dispatcher
# ======================================================
def show_section(title):
    if title == "📦 Product Database":
        show_product_database()
    elif title == "🧮 Calculations":
        show_calculations()
    elif title == "🤖 PiU (AI Assistant)":
        show_ai_assistant()
    else:
        st.info(f"⚠️ Section {title} not implemented yet.")
    st.markdown("<hr>")
    if st.button("Back to Home"):
        st.session_state.selected_section = None

# ======================================================
# 🔹 Main
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