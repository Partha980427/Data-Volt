import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile
import re

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

# FIXED: Use correct column name "Product Grade" instead of "Grade"
if not df_iso4014.empty:
    df_iso4014['Product'] = "Hex Bolt"
    df_iso4014['Standards'] = "ISO-4014-2011"
    # Remove the old 'Grade' column if it exists and use 'Product Grade'
    if 'Grade' in df_iso4014.columns and 'Product Grade' in df_iso4014.columns:
        df_iso4014 = df_iso4014.drop('Grade', axis=1)
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
# 🔹 COMPLETELY BULLETPROOF SIZE HANDLING
# ======================================================
def size_to_float(size_str):
    """Convert size string to float for sorting - ULTRA ROBUST VERSION"""
    try:
        # Handle empty/None values
        if pd.isna(size_str) or not isinstance(size_str, (str, int, float)):
            return 0.0
        
        size_str = str(size_str).strip()
        if not size_str or size_str == "":
            return 0.0
        
        # Handle ISO metric sizes like "M1.6 X 0.35", "M30 X3.5", "M30 X 3.5"
        if size_str.startswith('M'):
            # Extract the number after M (handle various formats)
            match = re.match(r'M\s*([\d.]+)', size_str)
            if match:
                return float(match.group(1))
            return 0.0
        
        # Handle inch fractional sizes like "1/2", "1/4", "3/8"
        if "/" in size_str:
            try:
                # Handle mixed numbers like "1-1/2"
                if "-" in size_str:
                    parts = size_str.split("-")
                    whole = float(parts[0]) if parts[0] else 0
                    fraction = float(Fraction(parts[1]))
                    return whole + fraction
                else:
                    return float(Fraction(size_str))
            except:
                return 0.0
        
        # Handle decimal numbers
        try:
            return float(size_str)
        except:
            return 0.0
        
    except Exception as e:
        # Silent fail - return 0 for any error
        return 0.0

def safe_sort_sizes(size_list):
    """Safely sort size list with multiple fallbacks"""
    if not size_list or len(size_list) == 0:
        return []
    
    try:
        # First try: numeric sorting with our converter
        return sorted(size_list, key=lambda x: (size_to_float(x), str(x)))
    except:
        try:
            # Second try: string sorting
            return sorted(size_list, key=str)
        except:
            # Final fallback: return as-is
            return list(size_list)

def get_safe_size_options(temp_df):
    """Completely safe way to get size options"""
    size_options = ["All"]
    
    if temp_df is None or temp_df.empty:
        return size_options
    
    if 'Size' not in temp_df.columns:
        return size_options
    
    try:
        unique_sizes = temp_df['Size'].dropna().unique()
        if len(unique_sizes) > 0:
            sorted_sizes = safe_sort_sizes(unique_sizes)
            size_options.extend(sorted_sizes)
    except Exception as e:
        # If everything fails, just return unique values without sorting
        try:
            unique_sizes = temp_df['Size'].dropna().unique()
            size_options.extend(list(unique_sizes))
        except:
            pass
    
    return size_options

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
# 🔹 Product Database Section - FIXED GRADE COLUMN
# ======================================================
def show_product_database():
    st.header("📦 Product Database Search Panel")
    if df.empty and df_mechem.empty and df_iso4014.empty:
        st.warning("No data available.")
        return
    
    st.sidebar.header("🔍 Filter Options")
    
    # Product Type Selection
    product_types = ["All"] + sorted(list(df['Product'].dropna().unique()) + ["Threaded Rod", "Stud", "Hex Bolt"])
    product_type = st.sidebar.selectbox("Select Product", product_types)
    
    # Series Selection
    series_options = ["Inch", "Metric"]
    series = st.sidebar.selectbox("Select Series", series_options)
    
    # Dimensional Standards based on series selection
    dimensional_standards = ["All"]
    if series == "Inch":
        inch_standards = [std for std in df['Standards'].dropna().unique() if "ISO" not in str(std)]
        dimensional_standards.extend(sorted(inch_standards))
    else:
        metric_standards = [std for std in df['Standards'].dropna().unique() if "ISO" in str(std)]
        dimensional_standards.extend(sorted(metric_standards))
        if "ISO 4014" not in dimensional_standards:
            dimensional_standards.append("ISO 4014")
    
    dimensional_standard = st.sidebar.selectbox("Dimensional Standard", dimensional_standards)
    
    # Get the appropriate dataframe FIRST (without grade filter)
    temp_df = df.copy()
    if dimensional_standard == "ISO 4014":
        temp_df = df_iso4014
    else:
        if product_type != "All":
            temp_df = temp_df[temp_df['Product'] == product_type]
        if dimensional_standard != "All":
            temp_df = temp_df[temp_df['Standards'] == dimensional_standard]
    
    # PRODUCT GRADE FILTER - FIXED: Use "Product Grade" column for ISO 4014
    product_grade_options = ["All"]
    if dimensional_standard == "ISO 4014":
        # FIXED: Use 'Product Grade' column instead of 'Grade'
        if not temp_df.empty and 'Product Grade' in temp_df.columns:
            grades = temp_df['Product Grade'].dropna().unique()
            if len(grades) > 0:
                product_grade_options.extend(sorted(grades))
    else:
        # For other standards, use 'Product Grade' column
        if not temp_df.empty and 'Product Grade' in temp_df.columns:
            grades = temp_df['Product Grade'].dropna().unique()
            if len(grades) > 0:
                product_grade_options.extend(sorted(grades))
    
    selected_grade = st.sidebar.selectbox("Product Grade", product_grade_options)
    
    # USE THE COMPLETELY SAFE SIZE OPTIONS FUNCTION (before grade filter)
    size_options = get_safe_size_options(temp_df)
    dimensional_size = st.sidebar.selectbox("Dimensional Size", size_options)
    
    # Thread Standards
    thread_standards = ["All"]
    if series == "Inch":
        thread_standards += ["ASME B1.1"]
    else:
        thread_standards += ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
    
    thread_standard = st.sidebar.selectbox("Thread Standard", thread_standards)
    
    # Thread Size and Class options
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
    
    # ME&CERT Standards
    mecert_standards = ["All"]
    if not df_mechem.empty:
        mecert_standards += sorted(df_mechem['Standard'].dropna().unique())
    mecert_standard = st.sidebar.selectbox("ME&CERT Standard", mecert_standards)
    
    mecert_property_options = ["All"]
    if mecert_standard != "All" and not df_mechem.empty:
        temp_me = df_mechem[df_mechem['Standard'] == mecert_standard]
        if "Property class" in temp_me.columns:
            mecert_property_options += sorted(temp_me['Property class'].dropna().unique())
    mecert_property = st.sidebar.selectbox("Property Class", mecert_property_options)
    
    # APPLY ALL FILTERS TO FINAL DATAFRAME
    filtered_df = temp_df.copy()
    
    # Apply grade filter - FIXED: Use "Product Grade" for ISO 4014
    if selected_grade != "All":
        if dimensional_standard == "ISO 4014" and 'Product Grade' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Product Grade'] == selected_grade]
        elif 'Product Grade' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Product Grade'] == selected_grade]
    
    # Apply size filter
    if dimensional_size != "All":
        filtered_df = filtered_df[filtered_df['Size'] == dimensional_size]
    
    # Display Results
    st.subheader(f"Found {len(filtered_df)} records")
    
    if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("No records found with the selected filters.")
    
    # Thread data display
    if thread_standard != "All":
        df_thread_filtered = get_thread_data(thread_standard, thread_size, thread_class)
        if not df_thread_filtered.empty:
            st.subheader(f"Thread Data: {thread_standard}")
            st.dataframe(df_thread_filtered, use_container_width=True)
    
    # ME&CERT data display
    filtered_mecert_df = df_mechem.copy()
    if mecert_standard != "All":
        filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Standard'] == mecert_standard]
    if mecert_property != "All":
        filtered_mecert_df = filtered_mecert_df[filtered_mecert_df['Property class'] == mecert_property]
    
    if not filtered_mecert_df.empty:
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
# 🔹 Calculations Section
# ======================================================
def show_calculations():
    st.header("🧮 Engineering Calculations")
    
    # Single Item Calculation
    st.subheader("Single Item Weight Calculation")
    
    # Series selection first - determines available options
    series = st.selectbox("Select Series", ["Inch", "Metric"])
    
    # Product and standard options based on series
    if series == "Inch":
        product_options = sorted([p for p in df['Product'].dropna().unique() if "Hex" in p or "Bolt" in p])
        standard_options = ["ASME B1.1"]
    else:  # Metric
        product_options = ["Hex Bolt"]  # ISO 4014 is specifically for hex bolts
        standard_options = ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine", "ISO 4014"]
    
    selected_product = st.selectbox("Select Product", product_options)
    selected_standard = st.selectbox("Select Standard", standard_options)
    
    # Get appropriate data source
    if selected_standard == "ISO 4014":
        df_source = df_iso4014
        size_options = sorted(df_source['Size'].dropna().unique())
    elif selected_standard in thread_files:
        df_thread = get_thread_data(selected_standard)
        size_options = sorted(df_thread['Thread'].dropna().unique()) if not df_thread.empty else []
    else:
        size_options = []
    
    selected_size = st.selectbox("Select Size", size_options) if size_options else st.selectbox("Select Size", ["No sizes available"])
    
    length_unit = st.selectbox("Select Length Unit", ["mm", "inch", "meter", "ft"])
    length_val = st.number_input("Enter Length", min_value=0.1, step=0.1, value=10.0)
    
    # Diameter handling based on standard and series
    diameter_mm = None
    if selected_standard == "ISO 4014" and selected_size != "No sizes available":
        row_iso = df_iso4014[df_iso4014['Size'] == selected_size]
        if not row_iso.empty and 'Body Diameter' in row_iso.columns:
            diameter_mm = row_iso['Body Diameter'].values[0]
            st.info(f"Body Diameter from ISO 4014: {diameter_mm} mm")
    elif selected_standard in thread_files and selected_size != "No sizes available":
        df_thread = get_thread_data(selected_standard)
        if not df_thread.empty:
            thread_row = df_thread[df_thread["Thread"] == selected_size]
            if not thread_row.empty and "Pitch Diameter (Min)" in thread_row.columns:
                pitch_val = thread_row["Pitch Diameter (Min)"].values[0]
                diameter_mm = pitch_val if series == "Metric" else pitch_val * 25.4
                st.info(f"Pitch Diameter: {diameter_mm} mm")
    
    # Manual diameter input as fallback
    if diameter_mm is None:
        st.warning("Could not auto-detect diameter. Please enter manually:")
        body_dia = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1, value=5.0)
        diameter_unit = st.selectbox("Diameter Unit", ["mm", "inch"])
        diameter_mm = body_dia * 25.4 if diameter_unit == "inch" else body_dia

    # Class selection based on series
    if series == "Inch":
        class_options = ["1A", "2A", "3A"]
    else:  # Metric
        class_options = ["6g", "6H", "4g", "4H", "8g", "8H"]
    
    selected_class = st.selectbox("Select Class", class_options)

    if st.button("Calculate Weight"):
        if diameter_mm is None or diameter_mm <= 0:
            st.error("❌ Please provide valid diameter information.")
        else:
            length_mm = convert_length_to_mm(length_val, length_unit)
            weight_kg = calculate_weight(selected_product, diameter_mm, length_mm)
            if weight_kg > 0:
                st.success(f"✅ Estimated Weight: **{weight_kg} Kg** (Class: {selected_class})")
            else:
                st.error("❌ Failed to calculate weight. Please check inputs.")

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
            
            # Search in ISO 4014 data
            if not df_iso4014.empty:
                try:
                    mask_iso = df_iso4014.apply(lambda row: row.astype(str).str.contains(ai_query, case=False, na=False).any(), axis=1)
                    filtered_iso = df_iso4014[mask_iso]
                    if not filtered_iso.empty:
                        response_parts.append(f"🌍 Found {len(filtered_iso)} ISO 4014 records:\n{filtered_iso.to_string(index=False)}")
                except Exception as e:
                    st.warning(f"Error searching ISO 4014 data: {str(e)}")
            
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