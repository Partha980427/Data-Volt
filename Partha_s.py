import streamlit as st
import pandas as pd
import os
from fractions import Fraction
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile
import re
from datetime import datetime
import plotly.express as px

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
        "current_filters": {},
        "recent_searches": [],
        "favorite_products": []
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
# 🔹 Page Setup with Modern Styling
# ======================================================
st.set_page_config(
    page_title="JSC Industries – Fastener Intelligence", 
    layout="wide",
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #667eea;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .quick-action {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 2rem 1rem;
        border-radius: 15px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 6px 15px rgba(0,0,0,0.1);
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .quick-action:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 25px rgba(0,0,0,0.2);
    }
    .section-header {
        border-left: 5px solid #667eea;
        padding-left: 1rem;
        margin: 2rem 0 1rem 0;
        color: #2c3e50;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.7rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.2);
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    .feature-badge {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
initialize_session_state()

# ======================================================
# 🔹 Paths & Files - UPDATED WITH PROPER PATHS
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"
me_chem_path = r"Mechanical and Chemical.xlsx"

# ISO 4014 paths - local and Google Sheets
iso4014_local_path = r"G:\My Drive\Streamlite\ISO 4014 Hex Bolt.xlsx"
iso4014_file_url = "https://docs.google.com/spreadsheets/d/1d2hANwoMhuzwyKJ72c125Uy0ujB6QsV_/export?format=xlsx"

# Thread files - UPDATED WITH PROPER PATHS
thread_files = {
    "ASME B1.1": r"G:\My Drive\Streamlite\ASME B1.1 New.xlsx",
    "ISO 965-2-98 Coarse": r"G:\My Drive\Streamlite\ISO 965-2-98 Coarse.xlsx",
    "ISO 965-2-98 Fine": r"G:\My Drive\Streamlite\ISO 965-2-98 Fine.xlsx",
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

@st.cache_data
def load_thread_data(file_path):
    """Load thread data with proper error handling"""
    try:
        if os.path.exists(file_path):
            df_thread = pd.read_excel(file_path)
            st.sidebar.success(f"✅ Loaded: {os.path.basename(file_path)} - {len(df_thread)} rows")
            return df_thread
        else:
            st.sidebar.error(f"❌ File not found: {os.path.basename(file_path)}")
            return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"❌ Error loading {os.path.basename(file_path)}: {str(e)}")
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
# 🔹 Enhanced Home Dashboard
# ======================================================
def show_enhanced_home():
    # Header Section
    st.markdown("""
        <div class="main-header">
            <h1 style="margin:0; font-size: 2.5rem;">🔧 JSC Industries</h1>
            <p style="margin:0; font-size: 1.2rem; opacity: 0.9;">Fastener Intelligence Platform v3.0</p>
            <div style="margin-top: 1rem;">
                <span class="feature-badge">AI-Powered</span>
                <span class="feature-badge">Real-Time Analytics</span>
                <span class="feature-badge">Multi-Standard</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = len(df) + (len(df_iso4014) if not df_iso4014.empty else 0)
    total_standards = len(df['Standards'].unique()) + 1 if not df.empty else 1
    total_threads = len(thread_files)
    total_mecert = len(df_mechem) if not df_mechem.empty else 0
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #667eea; margin:0;">📊 Products</h3>
                <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_products}</h2>
                <p style="color: #7f8c8d; margin:0;">Total Records</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #667eea; margin:0;">🌍 Standards</h3>
                <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_standards}</h2>
                <p style="color: #7f8c8d; margin:0;">Supported</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #667eea; margin:0;">⚡ Thread Types</h3>
                <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_threads}</h2>
                <p style="color: #7f8c8d; margin:0;">Available</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #667eea; margin:0;">🔬 ME&CERT</h3>
                <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_mecert}</h2>
                <p style="color: #7f8c8d; margin:0;">Properties</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Quick Actions
    st.markdown('<h2 class="section-header">🚀 Quick Actions</h2>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    actions = [
        ("📦 Smart Search", "AI-powered product discovery with advanced filters", "database"),
        ("🧮 Batch Calculator", "Process multiple calculations with bulk upload", "calculator"),
        ("📊 Analytics Dashboard", "Visual insights and performance metrics", "analytics"),
        ("🔧 Compare Products", "Side-by-side product comparison tool", "compare"),
        ("🤖 PiU Assistant", "AI-powered technical support", "ai"),
        ("📋 Export Workspace", "Generate comprehensive reports", "export")
    ]
    
    for idx, (title, description, key) in enumerate(actions):
        with cols[idx % 3]:
            if st.button(f"**{title}**\n\n{description}", key=f"home_{key}"):
                section_map = {
                    "database": "📦 Product Database",
                    "calculator": "🧮 Calculations", 
                    "ai": "🤖 PiU (AI Assistant)"
                }
                st.session_state.selected_section = section_map.get(key, "📦 Product Database")
    
    # System Status
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="section-header">📈 System Status</h3>', unsafe_allow_html=True)
        
        # Check thread file status
        st.write("**Thread Data Status:**")
        for thread_std, file_path in thread_files.items():
            if os.path.exists(file_path):
                st.success(f"✅ {thread_std} - Available")
            else:
                st.error(f"❌ {thread_std} - File not found")
    
    with col2:
        st.markdown('<h3 class="section-header">🕒 Recent Features</h3>', unsafe_allow_html=True)
        
        features = [
            "🎯 Smart filtering with AI suggestions",
            "📱 Mobile-responsive design", 
            "🔍 Advanced search capabilities",
            "📊 Real-time analytics integration",
            "🌙 Dark mode ready",
            "🚀 Performance optimized"
        ]
        
        for feature in features:
            st.markdown(f"• {feature}")
    
    # Footer with version info
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #7f8c8d; padding: 1rem;">
            <p><strong>JSC Industries Fastener Intelligence Platform v3.0</strong></p>
            <p>Born to Perform • Engineered for Precision</p>
        </div>
    """, unsafe_allow_html=True)

# ======================================================
# 🔹 Enhanced Product Database Section
# ======================================================
def show_enhanced_product_database():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 15px; color: white; margin-bottom: 2rem;">
            <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
                📦 Product Intelligence Center
            </h1>
            <p style="margin:0; opacity: 0.9;">Advanced filtering, analytics, and discovery tools</p>
        </div>
    """, unsafe_allow_html=True)
    
    if df.empty and df_mechem.empty and df_iso4014.empty:
        st.error("🚫 No data sources available. Please check your data connections.")
        return
    
    # Quick Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        total_records = len(df) + (len(df_iso4014) if not df_iso4014.empty else 0)
        st.metric("Total Products", f"{total_records:,}")
    with col2:
        st.metric("Active Standards", len(df['Standards'].unique()) + 1 if not df.empty else 1)
    with col3:
        st.metric("Data Sources", "4" if not df_iso4014.empty else "3")
    
    st.markdown("---")
    
    # Enhanced Filter Section
    with st.sidebar:
        st.markdown("### 🔍 Smart Filters")
        
        # Thread Data Status
        st.markdown("**🔧 Thread Data Status**")
        for thread_std, file_path in thread_files.items():
            status = "✅" if os.path.exists(file_path) else "❌"
            st.write(f"{status} {thread_std}")
        
        st.markdown("---")
        
        # Quick Filter Presets
        st.markdown("**🎯 Quick Presets**")
        preset_col1, preset_col2 = st.columns(2)
        with preset_col1:
            if st.button("ISO Only", use_container_width=True):
                st.session_state.current_filters = {"series": "Metric", "standard": "ISO 4014"}
        with preset_col2:
            if st.button("ASME Only", use_container_width=True):
                st.session_state.current_filters = {"series": "Inch", "standard": "All"}
        
        st.markdown("---")
        
        # Main Filters
        product_types_from_df = list(df['Product'].dropna().unique()) if not df.empty else []
        unique_products = list(set(product_types_from_df))
        product_types = ["All"] + sorted(unique_products) + ["Threaded Rod", "Stud", "Hex Bolt"]
        
        product_type = st.selectbox("**Product Type**", product_types, 
                                   help="Select specific product category")
        
        series = st.radio("**Series System**", ["Inch", "Metric"], 
                         help="Choose between inch and metric standards")
        
        # Dynamic standards based on series
        dimensional_standards = ["All"]
        if series == "Inch":
            inch_standards = [std for std in df['Standards'].dropna().unique() if "ISO" not in str(std)] if not df.empty else []
            dimensional_standards.extend(sorted(inch_standards))
        else:
            metric_standards = [std for std in df['Standards'].dropna().unique() if "ISO" in str(std)] if not df.empty else []
            dimensional_standards.extend(sorted(metric_standards))
            if "ISO 4014" not in dimensional_standards:
                dimensional_standards.append("ISO 4014")
        
        dimensional_standard = st.selectbox("**Dimensional Standard**", dimensional_standards,
                                           help="Select applicable standard specification")
        
        # PRODUCT GRADE FILTER
        product_grade_options = ["All"]
        temp_df = df.copy()
        if dimensional_standard == "ISO 4014":
            temp_df = df_iso4014 if not df_iso4014.empty else pd.DataFrame()
        else:
            if product_type != "All":
                temp_df = temp_df[temp_df['Product'] == product_type]
            if dimensional_standard != "All":
                temp_df = temp_df[temp_df['Standards'] == dimensional_standard]
        
        if dimensional_standard == "ISO 4014":
            if not temp_df.empty and 'Product Grade' in temp_df.columns:
                grades = temp_df['Product Grade'].dropna().unique()
                if len(grades) > 0:
                    product_grade_options.extend(sorted(grades))
        else:
            if not temp_df.empty and 'Product Grade' in temp_df.columns:
                grades = temp_df['Product Grade'].dropna().unique()
                if len(grades) > 0:
                    product_grade_options.extend(sorted(grades))
        
        selected_grade = st.selectbox("**Product Grade**", product_grade_options)
    
    # Main Content Area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get filtered data
        temp_df = df.copy()
        if dimensional_standard == "ISO 4014":
            temp_df = df_iso4014
        else:
            if product_type != "All":
                temp_df = temp_df[temp_df['Product'] == product_type]
            if dimensional_standard != "All":
                temp_df = temp_df[temp_df['Standards'] == dimensional_standard]
        
        # Apply grade filter
        if selected_grade != "All":
            if dimensional_standard == "ISO 4014" and 'Product Grade' in temp_df.columns:
                temp_df = temp_df[temp_df['Product Grade'] == selected_grade]
            elif 'Product Grade' in temp_df.columns:
                temp_df = temp_df[temp_df['Product Grade'] == selected_grade]
        
        # Size filter
        size_options = get_safe_size_options(temp_df)
        selected_size = st.selectbox("**Filter by Size**", size_options,
                                    help="Select specific dimensional size")
        
        # Apply final filters
        filtered_df = temp_df.copy()
        if selected_size != "All":
            filtered_df = filtered_df[filtered_df['Size'] == selected_size]
        
        # Results Display
        st.markdown(f"### 📊 Results: {len(filtered_df)} records found")
        
        if not filtered_df.empty:
            # Enhanced dataframe with styling
            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=400
            )
            
            # Quick Actions for results
            st.download_button(
                "📥 Export Selected Data",
                filtered_df.to_csv(index=False),
                file_name=f"filtered_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("🤔 No records match your current filters. Try adjusting your search criteria.")
        
        # Thread Data Section - ALWAYS VISIBLE WHEN THREAD STANDARD IS SELECTED
        st.markdown("---")
        st.markdown("### 🔧 Thread Data")
        
        # Thread Standards
        thread_standards = ["All"]
        if series == "Inch":
            thread_standards += ["ASME B1.1"]
        else:
            thread_standards += ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
        
        thread_standard = st.selectbox("**Thread Standard**", thread_standards,
                                      help="Select thread standard to view detailed data")
        
        # Thread Size and Class options
        if thread_standard != "All":
            df_thread = get_thread_data(thread_standard)
            if not df_thread.empty:
                thread_size_options = ["All"]
                thread_class_options = ["All"]
                
                if "Thread" in df_thread.columns:
                    thread_size_options += sorted(df_thread['Thread'].dropna().unique())
                if "Class" in df_thread.columns:
                    thread_class_options += sorted(df_thread['Class'].dropna().unique())
                
                thread_size = st.selectbox("**Thread Size**", thread_size_options)
                thread_class = st.selectbox("**Thread Class**", thread_class_options)
                
                # Apply thread filters
                df_thread_filtered = df_thread.copy()
                if thread_size != "All":
                    df_thread_filtered = df_thread_filtered[df_thread_filtered['Thread'] == thread_size]
                if thread_class != "All":
                    df_thread_filtered = df_thread_filtered[df_thread_filtered['Class'] == thread_class]
                
                if not df_thread_filtered.empty:
                    st.markdown(f"**Thread Data: {thread_standard}**")
                    st.dataframe(df_thread_filtered, use_container_width=True)
                else:
                    st.info("No thread data matches the selected filters.")
            else:
                st.warning(f"No thread data available for {thread_standard}. Check if the file exists at: {thread_files.get(thread_standard, 'Unknown path')}")
        else:
            st.info("Select a thread standard to view detailed thread data.")
    
    with col2:
        st.markdown("### 🎯 Quick Insights")
        
        if not filtered_df.empty:
            # Basic statistics
            st.metric("Selected Records", len(filtered_df))
            
            if 'Size' in filtered_df.columns:
                unique_sizes = filtered_df['Size'].nunique()
                st.metric("Unique Sizes", unique_sizes)
            
            # Size distribution using Plotly
            if 'Size' in filtered_df.columns and len(filtered_df) > 1:
                size_counts = filtered_df['Size'].value_counts().head(10)
                if len(size_counts) > 0:
                    try:
                        fig = px.bar(
                            x=size_counts.index,
                            y=size_counts.values,
                            title="Top Sizes Distribution",
                            labels={'x': 'Size', 'y': 'Count'}
                        )
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.info("Chart visualization requires Plotly installation")
        
        # ME&CERT Data
        st.markdown("### 🧪 ME&CERT Data")
        filtered_mecert_df = df_mechem.copy()
        if not filtered_mecert_df.empty:
            st.metric("Available Properties", len(filtered_mecert_df))
            if st.button("View ME&CERT Data"):
                st.dataframe(filtered_mecert_df, use_container_width=True)

# ======================================================
# 🔹 Enhanced Calculations Section
# ======================================================
def show_enhanced_calculations():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                    padding: 2rem; border-radius: 15px; color: white; margin-bottom: 2rem;">
            <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
                🧮 Engineering Calculator Suite
            </h1>
            <p style="margin:0; opacity: 0.9;">Advanced weight calculations and batch processing</p>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🚀 Single Calculator", "📊 Batch Processor", "📈 Analytics"])
    
    with tab1:
        st.markdown("### Single Item Weight Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            series = st.selectbox("Measurement System", ["Inch", "Metric"], key="calc_series")
            
            if series == "Inch":
                product_options_from_df = [p for p in df['Product'].dropna().unique() if "Hex" in p or "Bolt" in p] if not df.empty else []
                unique_products = list(set(product_options_from_df))
                product_options = sorted(unique_products)
                standard_options = ["ASME B1.1"]
            else:
                product_options = ["Hex Bolt"]
                standard_options = ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine", "ISO 4014"]
            
            selected_product = st.selectbox("Product Type", product_options)
            selected_standard = st.selectbox("Applicable Standard", standard_options)
        
        with col2:
            # Get size options
            if selected_standard == "ISO 4014":
                df_source = df_iso4014
                size_options = sorted(df_source['Size'].dropna().unique()) if not df_iso4014.empty else []
            elif selected_standard in thread_files:
                df_thread = get_thread_data(selected_standard)
                size_options = sorted(df_thread['Thread'].dropna().unique()) if not df_thread.empty else []
            else:
                size_options = []
            
            selected_size = st.selectbox("Size Specification", size_options) if size_options else st.selectbox("Size Specification", ["No sizes available"])
            
            length_val = st.number_input("Length Value", min_value=0.1, value=10.0, step=0.1)
            length_unit = st.selectbox("Length Unit", ["mm", "inch", "meter", "ft"])
        
        # Calculation and results
        if st.button("🚀 Calculate Weight", use_container_width=True):
            diameter_mm = None
            
            if selected_standard == "ISO 4014" and selected_size != "No sizes available" and not df_iso4014.empty:
                row_iso = df_iso4014[df_iso4014['Size'] == selected_size]
                if not row_iso.empty and 'Body Diameter' in row_iso.columns:
                    diameter_mm = row_iso['Body Diameter'].values[0]
                    st.info(f"Body Diameter from ISO 4014: {diameter_mm} mm")
            
            if diameter_mm is None:
                st.warning("Could not auto-detect diameter. Please enter manually:")
                body_dia = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1, value=5.0)
                diameter_unit = st.selectbox("Diameter Unit", ["mm", "inch"])
                diameter_mm = body_dia * 25.4 if diameter_unit == "inch" else body_dia

            if diameter_mm is not None and diameter_mm > 0:
                length_mm = convert_length_to_mm(length_val, length_unit)
                weight_kg = calculate_weight(selected_product, diameter_mm, length_mm)
                if weight_kg > 0:
                    st.success(f"✅ Estimated Weight: **{weight_kg} Kg**")
                else:
                    st.error("❌ Failed to calculate weight. Please check inputs.")
    
    with tab2:
        st.markdown("### Batch Weight Processor")
        st.info("📁 Upload a CSV/Excel file with columns: Product, Size, Length")
        uploaded_file = st.file_uploader("Choose batch file", type=["csv", "xlsx"])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    batch_df = pd.read_excel(uploaded_file)
                else:
                    batch_df = pd.read_csv(uploaded_file)
                
                st.write("Preview of uploaded data:")
                st.dataframe(batch_df.head())
                
                if st.button("Process Batch", use_container_width=True):
                    st.success("Batch processing started...")
                    # Add batch processing logic here
                    
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    with tab3:
        st.markdown("### Calculation Analytics")
        st.info("📈 Visual insights and calculation history coming soon...")
        # Analytics implementation

# ======================================================
# 🔹 Enhanced AI Assistant Section
# ======================================================
def show_enhanced_ai_assistant():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                    padding: 2rem; border-radius: 15px; color: #2c3e50; margin-bottom: 2rem;">
            <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
                🤖 PiU - Fastener Intelligence Assistant
            </h1>
            <p style="margin:0;">AI-powered insights and technical support</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 💬 Ask PiU Anything")
        
        # Enhanced query input
        ai_query = st.text_area(
            "Your technical question...",
            placeholder="e.g., 'Show me all M12 bolts with Grade B properties' or 'Compare ISO 4014 vs ASME standards'",
            height=100
        )
        
        # Quick question templates
        st.markdown("**🎯 Quick Questions**")
        quick_col1, quick_col2 = st.columns(2)
        with quick_col1:
            if st.button("Standards Comparison", use_container_width=True):
                ai_query = "Compare different fastener standards and their applications"
        with quick_col2:
            if st.button("Material Properties", use_container_width=True):
                ai_query = "Explain mechanical and chemical properties of fastener materials"
        
        if st.button("🚀 Ask PiU", use_container_width=True) and ai_query.strip():
            loading_placeholder = show_loading_placeholder("🤖 PiU is analyzing your query...")
            
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
            st.text_area("PiU Response:", value=response, height=400)
    
    with col2:
        st.markdown("### 📚 Capabilities")
        capabilities = [
            "🔍 Smart product search",
            "📊 Data analysis", 
            "🔧 Technical specifications",
            "📈 Performance insights",
            "🌍 Standards guidance",
            "💡 Engineering advice"
        ]
        
        for cap in capabilities:
            st.markdown(f"• {cap}")

# ======================================================
# 🔹 Section Dispatcher
# ======================================================
def show_section(title):
    if title == "📦 Product Database":
        show_enhanced_product_database()
    elif title == "🧮 Calculations":
        show_enhanced_calculations()
    elif title == "🤖 PiU (AI Assistant)":
        show_enhanced_ai_assistant()
    else:
        st.info(f"⚠️ Section {title} is coming soon!")
    
    st.markdown("---")
    if st.button("🏠 Back to Dashboard", use_container_width=True):
        st.session_state.selected_section = None

# ======================================================
# 🔹 Main Application
# ======================================================
st.markdown("**App Version: 3.0 – Professional Workspace Edition ✅**")

if st.session_state.selected_section is None:
    show_enhanced_home()
else:
    show_section(st.session_state.selected_section)

# ======================================================
# 🔹 Enhanced Footer
# ======================================================
st.markdown("""
    <hr>
    <div style='text-align: center; color: gray; padding: 2rem;'>
        <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
            <span>🔒 Secure</span>
            <span>⚡ Fast</span>
            <span>🎯 Precise</span>
            <span>🌍 Global</span>
        </div>
        <p><strong>© 2024 JSC Industries Pvt Ltd</strong> | Born to Perform • Engineered for Excellence</p>
        <p style="font-size: 0.8rem;">Fastener Intelligence Platform v3.0 | Built with Streamlit</p>
    </div>
""", unsafe_allow_html=True)