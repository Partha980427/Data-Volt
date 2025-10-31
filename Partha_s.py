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
import time
import json
import numpy as np
import math
import warnings
warnings.filterwarnings('ignore')

# ======================================================
# PATHS & FILES - UPDATED WITH GOOGLE SHEETS LINKS
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

# Mechanical and Chemical Properties paths
me_chem_google_url = "https://docs.google.com/spreadsheets/d/12lBzI67Wb0yZyJKYxpDCLzHF9zvS2Fha/export?format=xlsx"
me_chem_path = r"G:\My Drive\Streamlite\Mechanical and Chemical.xlsx"

# ISO 4014 paths - local and Google Sheets
iso4014_local_path = r"G:\My Drive\Streamlite\ISO 4014 Hex Bolt.xlsx"
iso4014_file_url = "https://docs.google.com/spreadsheets/d/1d2hANwoMhuzwyKJ72c125Uy0ujB6QsV_/export?format=xlsx"

# DIN-7991 paths - local and Google Sheets
din7991_local_path = r"G:\My Drive\Streamlite\DIN-7991.xlsx"
din7991_file_url = "https://docs.google.com/spreadsheets/d/1PjptIbFfebdF1h_Aj124fNgw5jNBWlvn/export?format=xlsx"

# ASME B18.3 paths - local and Google Sheets
asme_b18_3_local_path = r"G:\My Drive\Streamlite\ASME B18.3.xlsx"
asme_b18_3_file_url = "https://docs.google.com/spreadsheets/d/1dPNGwf7bv5A77rMSPpl11dhcJTXQfob1/export?format=xlsx"

# Thread files - UPDATED WITH GOOGLE SHEETS LINKS
thread_files = {
    "ASME B1.1": "https://docs.google.com/spreadsheets/d/1YHgUloNsFudxxqhWQV66D2DtSSKWFP_w/export?format=xlsx",
    "ISO 965-2-98 Coarse": "https://docs.google.com/spreadsheets/d/1be5eEy9hbVfMg2sl1-Cz1NNCGGF8EB-L/export?format=xlsx",
    "ISO 965-2-98 Fine": "https://docs.google.com/spreadsheets/d/1QGQ6SMWBSTsah-vq3zYnhOC3NXaBdKPe/export?format=xlsx",
}

# ======================================================
# ENHANCED CONFIGURATION & ERROR HANDLING
# ======================================================
@st.cache_data(ttl=3600, show_spinner=False)
def safe_load_excel_file_enhanced(path_or_url, max_retries=3, timeout=30):
    """Enhanced loading with better caching, validation and retry mechanism"""
    for attempt in range(max_retries):
        try:
            if path_or_url.startswith('http'):
                import requests
                from io import BytesIO
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(path_or_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                if len(response.content) < 100:
                    st.warning(f"File seems too small: {path_or_url}")
                    continue
                    
                df = pd.read_excel(BytesIO(response.content))
            else:
                if os.path.exists(path_or_url):
                    file_size = os.path.getsize(path_or_url)
                    if file_size < 100:
                        st.warning(f"File seems too small: {path_or_url}")
                        continue
                    df = pd.read_excel(path_or_url)
                else:
                    st.error(f"File not found: {path_or_url}")
                    return pd.DataFrame()
            
            if df.empty:
                st.warning(f"Empty dataframe loaded from: {path_or_url}")
                return pd.DataFrame()
                
            if len(df.columns) < 2:
                st.warning(f"Dataframe has too few columns: {path_or_url}")
                return pd.DataFrame()
                
            return df
            
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"Error loading {path_or_url}: {str(e)}")
                return pd.DataFrame()
            time.sleep(1)

def validate_dataframe(df, required_columns=[]):
    """Validate dataframe structure"""
    if df.empty:
        return False, "DataFrame is empty"
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return False, f"Missing columns: {missing_cols}"
    
    return True, "Valid"

def load_config():
    """Load configuration from session state with defaults"""
    if 'app_config' not in st.session_state:
        st.session_state.app_config = {
            'data_sources': {
                'main_data': url,
                'me_chem_data': me_chem_google_url,
                'iso4014': iso4014_file_url,
                'din7991': din7991_file_url,
                'asme_b18_3': asme_b18_3_file_url,
                'thread_files': thread_files
            },
            'ui': {
                'theme': 'light',
                'page_title': 'JSC Industries - Fastener Intelligence'
            },
            'features': {
                'batch_processing': True,
                'analytics': True
            }
        }
    return st.session_state.app_config

def save_user_preferences():
    """Save user preferences to session state"""
    if 'user_prefs' not in st.session_state:
        st.session_state.user_prefs = {
            'default_standard': 'ASME B1.1',
            'preferred_units': 'metric',
            'recent_searches': [],
            'favorite_filters': {},
            'theme_preference': 'light'
        }

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        "selected_section": None,
        "batch_result_df": None,
        "current_filters": {},
        "recent_searches": [],
        "favorite_products": [],
        "calculation_history": [],
        "export_format": "csv",
        "multi_search_products": [],
        "current_filters_dimensional": {},
        "current_filters_thread": {},
        "current_filters_material": {},
        "product_intelligence_filters": {},
        "me_chem_columns": [],
        "property_classes": [],
        "din7991_loaded": False,
        "asme_b18_3_loaded": False,
        "dimensional_standards_count": 0,
        "available_products": {},
        "available_series": {},
        "debug_mode": False,
        "section_a_view": True,
        "section_b_view": True,
        "section_c_view": True,
        "thread_independent_mode": True,
        "section_a_results": pd.DataFrame(),
        "section_b_results": pd.DataFrame(),
        "section_c_results": pd.DataFrame(),
        "combined_results": pd.DataFrame(),
        "section_a_filters": {},
        "section_b_filters": {},
        "section_c_filters": {},
        "section_a_current_product": "All",
        "section_a_current_series": "All",
        "section_a_current_standard": "All",
        "section_a_current_size": "All",
        "section_a_current_grade": "All",  # NEW: Added for ISO 4014 grades
        "section_b_current_standard": "All",
        "section_b_current_size": "All",
        "section_b_current_class": "All",
        "section_c_current_class": "All",
        "section_c_current_standard": "All",
        "thread_data_cache": {},
        "show_professional_card": False,
        "selected_product_details": None,
        "batch_calculation_results": pd.DataFrame(),
        # Weight calculator session states - FIXED INITIALIZATION
        "weight_calc_product": "Select Product",
        "weight_calc_series": "Select Series",
        "weight_calc_standard": "Select Standard",
        "weight_calc_size": "Select Size",
        "weight_calc_grade": "Select Grade",  # NEW: Added for ISO 4014 grades
        "weight_calc_diameter_type": "Blank Diameter",
        "weight_calc_blank_diameter": 10.0,
        "weight_calc_blank_dia_unit": "mm",
        "weight_calc_thread_standard": "Select Thread Standard",
        "weight_calc_thread_size": "All",
        "weight_calc_thread_class": "2A",
        "weight_calc_length": 50.0,
        "weight_calc_length_unit": "mm",
        "weight_calc_material": "Carbon Steel",
        "weight_calc_result": None,
        "weight_calculation_performed": False,
        "pitch_diameter_value": None,
        "weight_form_submitted": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    load_config()
    save_user_preferences()

# ======================================================
# FIXED THREAD DATA LOADING - PROPER DATA TYPES
# ======================================================
@st.cache_data(ttl=3600)
def load_thread_data_enhanced(standard_name):
    """Enhanced thread data loading with proper data type handling"""
    if standard_name not in thread_files:
        return pd.DataFrame()
    
    file_path = thread_files[standard_name]
    try:
        df_thread = safe_load_excel_file_enhanced(file_path)
        if df_thread.empty:
            st.warning(f"Thread data for {standard_name} is empty")
            return pd.DataFrame()
        
        # Clean column names
        df_thread.columns = [str(col).strip() for col in df_thread.columns]
        
        # Debug: Show column info
        if st.session_state.debug_mode:
            st.sidebar.write(f"Columns {standard_name}:", df_thread.columns.tolist())
            st.sidebar.write(f"Shape {standard_name}:", df_thread.shape)
        
        # Handle different column naming patterns
        thread_col = None
        class_col = None
        
        # Find thread size column
        possible_thread_cols = ['Thread', 'Size', 'Thread Size', 'Nominal Size', 'Basic Major Diameter']
        for col in df_thread.columns:
            col_lower = str(col).lower()
            for possible in possible_thread_cols:
                if possible.lower() in col_lower:
                    thread_col = col
                    break
            if thread_col:
                break
        
        # Find class/tolerance column
        possible_class_cols = ['Class', 'Tolerance', 'Tolerance Class', 'Thread Class']
        for col in df_thread.columns:
            col_lower = str(col).lower()
            for possible in possible_class_cols:
                if possible.lower() in col_lower:
                    class_col = col
                    break
            if class_col:
                break
        
        # If no specific class column found, check for columns containing tolerance info
        if not class_col:
            for col in df_thread.columns:
                if 'tolerance' in str(col).lower() or 'class' in str(col).lower():
                    class_col = col
                    break
        
        # Standardize column names for consistent processing
        if thread_col:
            df_thread = df_thread.rename(columns={thread_col: 'Thread'})
        
        if class_col:
            df_thread = df_thread.rename(columns={class_col: 'Class'})
        
        # Clean data - convert all to string and handle NaN
        if 'Thread' in df_thread.columns:
            df_thread['Thread'] = df_thread['Thread'].astype(str).str.strip()
            df_thread = df_thread[df_thread['Thread'] != 'nan']
            df_thread = df_thread[df_thread['Thread'] != '']
        
        if 'Class' in df_thread.columns:
            df_thread['Class'] = df_thread['Class'].astype(str).str.strip()
            df_thread = df_thread[df_thread['Class'] != 'nan']
            df_thread = df_thread[df_thread['Class'] != '']
        
        # Add standard identifier
        df_thread['Standard'] = standard_name
        
        return df_thread
        
    except Exception as e:
        st.error(f"Error loading thread data for {standard_name}: {str(e)}")
        return pd.DataFrame()

def get_thread_data_enhanced(standard, thread_size=None, thread_class=None):
    """Enhanced thread data retrieval with proper filtering"""
    df_thread = load_thread_data_enhanced(standard)
    
    if df_thread.empty:
        return pd.DataFrame()
    
    # Apply filters if provided
    result_df = df_thread.copy()
    
    if thread_size and thread_size != "All" and "Thread" in result_df.columns:
        result_df = result_df[result_df["Thread"].astype(str).str.strip() == str(thread_size).strip()]
    
    if thread_class and thread_class != "All" and "Class" in result_df.columns:
        result_df = result_df[
            result_df["Class"].ast(str).str.strip().str.upper() == 
            str(thread_class).strip().upper()
        ]
    
    return result_df

def get_thread_sizes_enhanced(standard):
    """Get available thread sizes with proper data handling"""
    df_thread = load_thread_data_enhanced(standard)
    
    if df_thread.empty or "Thread" not in df_thread.columns:
        return ["All"]
    
    try:
        # Get unique sizes and handle NaN values properly
        unique_sizes = df_thread['Thread'].dropna().unique()
        
        # Convert all sizes to string and filter out empty strings
        unique_sizes = [str(size).strip() for size in unique_sizes if str(size).strip() != '']
        
        if len(unique_sizes) > 0:
            sorted_sizes = safe_sort_sizes(unique_sizes)
            return ["All"] + sorted_sizes
        else:
            return ["All"]
    except Exception as e:
        st.warning(f"Thread size processing warning for {standard}: {str(e)}")
        return ["All"]

def get_thread_classes_enhanced(standard):
    """Get available thread classes with proper data handling"""
    df_thread = load_thread_data_enhanced(standard)
    
    if df_thread.empty or "Class" not in df_thread.columns:
        return ["All"]
    
    try:
        # Get unique classes and handle NaN values properly
        unique_classes = df_thread['Class'].dropna().unique()
        
        # Convert all classes to string and filter out empty strings
        unique_classes = [str(cls).strip() for cls in unique_classes if str(cls).strip() != '']
        
        if len(unique_classes) > 0:
            sorted_classes = sorted(unique_classes)
            return ["All"] + sorted_classes
        else:
            return ["All"]
    except Exception as e:
        st.warning(f"Thread class processing warning for {standard}: {str(e)}")
        return ["All"]

# ======================================================
# PAGE SETUP WITH PROFESSIONAL ENGINEERING STYLING
# ======================================================
st.set_page_config(
    page_title="JSC Industries - Fastener Intelligence", 
    layout="wide",
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

# Professional Engineering CSS with Enhanced Card Design
st.markdown("""
<style>
    :root {
        --engineering-blue: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        --material-red: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        --grade-purple: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%);
        --technical-teal: linear-gradient(135deg, #1abc9c 0%, #16a085 100%);
        --neutral-light: #f8f9fa;
        --neutral-dark: #343a40;
    }
    
    .engineering-header {
        background: var(--engineering-blue);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .spec-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #3498db;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    
    .spec-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    
    .material-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #e74c3c;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    
    .grade-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #8e44ad;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    
    .technical-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #1abc9c;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    
    .engineering-badge {
        background: var(--engineering-blue);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .material-badge {
        background: var(--material-red);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .grade-badge {
        background: var(--grade-purple);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .technical-badge {
        background: var(--technical-teal);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .spec-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .spec-item {
        background: var(--neutral-light);
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #3498db;
    }
    
    .spec-label {
        font-size: 0.8rem;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    
    .spec-value {
        font-size: 1.1rem;
        color: var(--neutral-dark);
        font-weight: 700;
    }
    
    .section-header {
        border-left: 5px solid #3498db;
        padding-left: 1rem;
        margin: 2rem 0 1rem 0;
        color: #2c3e50;
        font-weight: 600;
    }
    
    .material-header {
        border-left: 5px solid #e74c3c;
        padding-left: 1rem;
        margin: 2rem 0 1rem 0;
        color: #2c3e50;
        font-weight: 600;
    }
    
    .grade-header {
        border-left: 5px solid #8e44ad;
        padding-left: 1rem;
        margin: 2rem 0 1rem 0;
        color: #2c3e50;
        font-weight: 600;
    }
    
    .stButton>button {
        background: var(--engineering-blue);
        color: white;
        border: none;
        padding: 0.7rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.2);
    }
    
    .data-quality-indicator {
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        font-size: 0.85rem;
        border-left: 4px solid;
    }
    
    .quality-good {
        background: #d4edda;
        color: #155724;
        border-left-color: #28a745;
    }
    
    .quality-warning {
        background: #fff3cd;
        color: #856404;
        border-left-color: #ffc107;
    }
    
    .quality-error {
        background: #f8d7da;
        color: #721c24;
        border-left-color: #dc3545;
    }
    
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .quick-action {
        background: white;
        padding: 1.5rem 1rem;
        border-radius: 12px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border: 1px solid #e9ecef;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .quick-action:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #3498db;
        transition: transform 0.3s ease;
        border: 1px solid #e9ecef;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
    }
    
    .property-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.8rem;
        margin: 1rem 0;
    }
    
    .property-item {
        background: var(--neutral-light);
        padding: 0.8rem;
        border-radius: 6px;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    
    .property-value {
        font-size: 1.2rem;
        font-weight: 700;
        color: #2c3e50;
    }
    
    .property-label {
        font-size: 0.75rem;
        color: #6c757d;
        text-transform: uppercase;
        margin-top: 0.3rem;
    }

    .calculation-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
    }
    .data-table {
        font-size: 0.8rem;
        margin: 0.5rem 0;
    }
    
    .filter-section {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
        border: 1px solid #e9ecef;
    }
    
    .filter-header {
        border-left: 4px solid #3498db;
        padding-left: 1rem;
        margin-bottom: 1rem;
        color: #2c3e50;
        font-weight: 600;
    }
    
    .multi-search-item {
        background: var(--neutral-light);
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        border-left: 3px solid #3498db;
    }
    
    .section-toggle {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .section-toggle:hover {
        background: #e9ecef;
    }
    
    .section-toggle.active {
        background: #3498db;
        color: white;
        border-color: #3498db;
    }
    
    .independent-section {
        border: 2px solid #3498db;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
    }
    
    .section-results {
        border: 2px solid #28a745;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #f0f8f0 0%, #ffffff 100%);
    }
    
    .combined-results {
        border: 2px solid #8e44ad;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #f8f0f8 0%, #ffffff 100%);
    }
    
    .professional-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 2px solid #3498db;
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(52, 152, 219, 0.2);
        position: relative;
        overflow: hidden;
    }
    
    .professional-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--engineering-blue);
    }
    
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #e9ecef;
    }
    
    .card-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2c3e50;
        margin: 0;
    }
    
    .card-subtitle {
        font-size: 1.2rem;
        color: #7f8c8d;
        margin: 0.5rem 0 0 0;
    }
    
    .card-company {
        background: var(--engineering-blue);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .specification-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 1.5rem 0;
    }
    
    .spec-group {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .spec-group-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3498db;
    }
    
    .spec-row {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        gap: 1rem;
        align-items: center;
        padding: 0.8rem 0;
        border-bottom: 1px solid #f8f9fa;
    }
    
    .spec-row:last-child {
        border-bottom: none;
    }
    
    .spec-label-min {
        text-align: right;
        font-weight: 600;
        color: #e74c3c;
        font-size: 0.9rem;
    }
    
    .spec-label-max {
        text-align: left;
        font-weight: 600;
        color: #27ae60;
        font-size: 0.9rem;
    }
    
    .spec-dimension {
        text-align: center;
        font-weight: 600;
        color: #2c3e50;
        font-size: 0.95rem;
        padding: 0.5rem;
        background: #f8f9fa;
        border-radius: 6px;
    }
    
    .spec-value {
        padding: 0.5rem;
        text-align: center;
        font-weight: 500;
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        min-height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 2px solid #e9ecef;
        font-size: 0.9rem;
        color: #7f8c8d;
    }
    
    .card-badge {
        background: var(--technical-teal);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 15px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    
    .card-actions {
        display: flex;
        gap: 1rem;
        margin-top: 1.5rem;
    }
    
    .action-button {
        background: var(--engineering-blue);
        color: white;
        border: none;
        padding: 0.7rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
    }
    
    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
    }
    
    .action-button.secondary {
        background: #6c757d;
    }
    
    .action-button.secondary:hover {
        background: #5a6268;
    }
    
    @media (max-width: 768px) {
        .engineering-header {
            padding: 1.5rem !important;
        }
        .spec-grid {
            grid-template-columns: 1fr;
        }
        .property-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .specification-grid {
            grid-template-columns: 1fr;
        }
        .card-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
        }
        .card-footer {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
        }
        .card-actions {
            justify-content: center;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
initialize_session_state()

# ======================================================
# ENHANCED DATA LOADING WITH PRODUCT MAPPING
# ======================================================

# Load main data
df = safe_load_excel_file_enhanced(url) if url else safe_load_excel_file_enhanced(local_excel_path)

# Load Mechanical and Chemical data
df_mechem = safe_load_excel_file_enhanced(me_chem_google_url)
if df_mechem.empty:
    st.info("Online Mechanical & Chemical file not accessible, trying local version...")
    df_mechem = safe_load_excel_file_enhanced(me_chem_path)

# Load ISO 4014 data
df_iso4014 = safe_load_excel_file_enhanced(iso4014_file_url)
if df_iso4014.empty:
    st.info("Online ISO 4014 file not accessible, trying local version...")
    df_iso4014 = safe_load_excel_file_enhanced(iso4014_local_path)

# Load DIN-7991 data
df_din7991 = safe_load_excel_file_enhanced(din7991_file_url)
if df_din7991.empty:
    st.info("Online DIN-7991 file not accessible, trying local version...")
    df_din7991 = safe_load_excel_file_enhanced(din7991_local_path)

# Load ASME B18.3 data
df_asme_b18_3 = safe_load_excel_file_enhanced(asme_b18_3_file_url)
if df_asme_b18_3.empty:
    st.info("Online ASME B18.3 file not accessible, trying local version...")
    df_asme_b18_3 = safe_load_excel_file_enhanced(asme_b18_3_local_path)

# ======================================================
# FIXED DATA PROCESSING - CORRECT PRODUCT NAMES
# ======================================================

def process_standard_data():
    """FIXED VERSION: Get ACTUAL product names from Excel files"""
    
    standard_products = {}
    standard_series = {}
    
    # Process ASME B18.2.1 - Get ACTUAL products from Excel
    if not df.empty:
        if 'Product' in df.columns:
            # Get ACTUAL unique products from the Excel data
            asme_products = df['Product'].dropna().unique().tolist()
            # Clean and sort the actual product names
            cleaned_products = [str(p).strip() for p in asme_products if p and str(p).strip() != '']
            standard_products['ASME B18.2.1'] = ["All"] + sorted(cleaned_products)
        else:
            # Fallback if no Product column
            standard_products['ASME B18.2.1'] = ["All", "Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screws", "Heavy Hex Screws"]
        standard_series['ASME B18.2.1'] = "Inch"
    
    # Process ASME B18.3 Data - Get ACTUAL products
    if not df_asme_b18_3.empty:
        if 'Product' in df_asme_b18_3.columns:
            asme_b18_3_products = df_asme_b18_3['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in asme_b18_3_products if p and str(p).strip() != '']
            standard_products['ASME B18.3'] = ["All"] + sorted(cleaned_products)
        else:
            standard_products['ASME B18.3'] = ["All", "Hexagon Socket Head Cap Screws"]
        standard_series['ASME B18.3'] = "Inch"
    
    # Process DIN-7991 Data - Get ACTUAL products
    if not df_din7991.empty:
        if 'Product' in df_din7991.columns:
            din_products = df_din7991['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in din_products if p and str(p).strip() != '']
            standard_products['DIN-7991'] = ["All"] + sorted(cleaned_products)
        else:
            standard_products['DIN-7991'] = ["All", "Hexagon Socket Countersunk Head Cap Screw"]
        standard_series['DIN-7991'] = "Metric"
    
    # Process ISO 4014 Data - Get ACTUAL products
    if not df_iso4014.empty:
        product_col = None
        for col in df_iso4014.columns:
            if 'product' in col.lower():
                product_col = col
                break
        
        if product_col:
            iso_products = df_iso4014[product_col].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in iso_products if p and str(p).strip() != '']
            standard_products['ISO 4014'] = ["All"] + sorted(cleaned_products)
        else:
            standard_products['ISO 4014'] = ["All", "Hex Bolt"]
        standard_series['ISO 4014'] = "Metric"
    
    # ADD THREADED ROD TO ALL STANDARDS
    for standard in standard_products:
        if "Threaded Rod" not in standard_products[standard]:
            standard_products[standard] = ["All", "Threaded Rod"] + [p for p in standard_products[standard] if p != "All" and p != "Threaded Rod"]
    
    # Store in session state
    st.session_state.available_products = standard_products
    st.session_state.available_series = standard_series
    
    # Count dimensional standards
    dimensional_standards_count = 0
    if not df.empty:
        dimensional_standards_count += 1
    if not df_iso4014.empty:
        dimensional_standards_count += 1
    if not df_din7991.empty:
        dimensional_standards_count += 1
    if not df_asme_b18_3.empty:
        dimensional_standards_count += 1
    
    st.session_state.dimensional_standards_count = dimensional_standards_count
    
    return standard_products, standard_series

# Process all standards data
standard_products, standard_series = process_standard_data()

# Process DIN-7991 data if loaded
if not df_din7991.empty:
    if 'Product' not in df_din7991.columns:
        df_din7991['Product'] = "Hexagon Socket Countersunk Head Cap Screw"
    if 'Standards' not in df_din7991.columns:
        df_din7991['Standards'] = "DIN-7991"
    st.session_state.din7991_loaded = True
else:
    st.session_state.din7991_loaded = False

# Process ASME B18.3 data if loaded
if not df_asme_b18_3.empty:
    if 'Product' not in df_asme_b18_3.columns:
        df_asme_b18_3['Product'] = "Hexagon Socket Head Cap Screws"
    if 'Standards' not in df_asme_b18_3.columns:
        df_asme_b18_3['Standards'] = "ASME B18.3"
    st.session_state.asme_b18_3_loaded = True
else:
    st.session_state.asme_b18_3_loaded = False

# Process ISO 4014 data
if not df_iso4014.empty:
    product_col = None
    for col in df_iso4014.columns:
        if 'product' in col.lower():
            product_col = col
            break
    
    if product_col:
        df_iso4014['Product'] = df_iso4014[product_col]
    else:
        df_iso4014['Product'] = "Hex Bolt"
    
    df_iso4014['Standards'] = "ISO-4014-2011"
    
    grade_col = None
    for col in df_iso4014.columns:
        if 'grade' in col.lower():
            grade_col = col
            break
    
    if grade_col and grade_col != 'Product Grade':
        df_iso4014['Product Grade'] = df_iso4014[grade_col]

# ======================================================
# ENHANCED MECHANICAL & CHEMICAL DATA PROCESSING - COMPLETELY FIXED
# ======================================================
def process_mechanical_chemical_data():
    """Process and extract ALL property classes from Mechanical & Chemical data - COMPLETELY FIXED"""
    if df_mechem.empty:
        return [], []
    
    try:
        me_chem_columns = df_mechem.columns.tolist()
        
        # Find ALL possible property class columns
        property_class_cols = []
        possible_class_cols = ['Grade', 'Class', 'Property Class', 'Material Grade', 'Type', 'Designation', 'Material']
        
        for col in me_chem_columns:
            col_lower = str(col).lower()
            for possible in possible_class_cols:
                if possible.lower() in col_lower:
                    property_class_cols.append(col)
                    break
        
        # If no specific class columns found, use first few columns that have string data
        if not property_class_cols:
            for col in me_chem_columns[:3]:  # Check first 3 columns
                if df_mechem[col].dtype == 'object':  # String/object type
                    property_class_cols.append(col)
                    break
        
        # Collect ALL unique property classes from ALL identified columns
        all_property_classes = set()
        
        for prop_col in property_class_cols:
            if prop_col in df_mechem.columns:
                unique_classes = df_mechem[prop_col].dropna().unique()
                # Clean and add all classes
                for cls in unique_classes:
                    if pd.notna(cls) and str(cls).strip() != '':
                        all_property_classes.add(str(cls).strip())
        
        # Convert to sorted list
        property_classes = sorted(list(all_property_classes))
        
        st.session_state.me_chem_columns = me_chem_columns
        st.session_state.property_classes = property_classes
        
        # Debug info
        if st.session_state.debug_mode:
            st.sidebar.write(f"Found {len(property_classes)} property classes")
            st.sidebar.write(f"Property class columns: {property_class_cols}")
        
        return me_chem_columns, property_classes
        
    except Exception as e:
        st.error(f"Error processing Mechanical & Chemical data: {str(e)}")
        return [], []

def get_standards_for_property_class(property_class):
    """Get available standards for a specific property class - COMPLETELY FIXED"""
    if df_mechem.empty or not property_class or property_class == "All":
        return []
    
    try:
        # Find ALL possible standard columns
        standard_cols = []
        possible_standard_cols = ['Standard', 'Specification', 'Norm', 'Type', 'Designation']
        
        for col in df_mechem.columns:
            col_lower = str(col).lower()
            for possible in possible_standard_cols:
                if possible.lower() in col_lower:
                    standard_cols.append(col)
                    break
        
        # If no standard columns found, look for any column that might contain standard info
        if not standard_cols:
            for col in df_mechem.columns:
                if any(word in col.lower() for word in ['iso', 'astm', 'asme', 'din', 'bs', 'jis', 'gb']):
                    standard_cols.append(col)
                    break
        
        # Find ALL possible property class columns
        property_class_cols = []
        possible_class_cols = ['Grade', 'Class', 'Property Class', 'Material Grade', 'Type', 'Designation', 'Material']
        
        for col in df_mechem.columns:
            col_lower = str(col).lower()
            for possible in possible_class_cols:
                if possible.lower() in col_lower:
                    property_class_cols.append(col)
                    break
        
        # If no specific class columns found, use first few columns
        if not property_class_cols:
            for col in df_mechem.columns[:3]:
                if df_mechem[col].dtype == 'object':
                    property_class_cols.append(col)
                    break
        
        # Try to find matching data using ALL property class columns
        matching_standards = set()
        
        for prop_col in property_class_cols:
            if prop_col in df_mechem.columns:
                # Try exact match first
                exact_match = df_mechem[df_mechem[prop_col] == property_class]
                if not exact_match.empty:
                    for std_col in standard_cols:
                        if std_col in exact_match.columns:
                            standards = exact_match[std_col].dropna().unique()
                            for std in standards:
                                if pd.notna(std) and str(std).strip() != '':
                                    matching_standards.add(str(std).strip())
                
                # Try string contains match for more flexible matching
                str_match = df_mechem[df_mechem[prop_col].astype(str).str.contains(str(property_class), na=False, case=False)]
                if not str_match.empty:
                    for std_col in standard_cols:
                        if std_col in str_match.columns:
                            standards = str_match[std_col].dropna().unique()
                            for std in standards:
                                if pd.notna(std) and str(std).strip() != '':
                                    matching_standards.add(str(std).strip())
        
        # If still no standards found, return some default/common standards
        if not matching_standards:
            common_standards = ['ASTM A193', 'ASTM A320', 'ASTM A194', 'ISO 898-1', 'ISO 3506', 'ASME B18.2.1']
            for std in common_standards:
                matching_standards.add(std)
        
        return sorted(list(matching_standards))
        
    except Exception as e:
        st.error(f"Error getting standards for {property_class}: {str(e)}")
        return []

def show_mechanical_chemical_details(property_class):
    """Show detailed mechanical and chemical properties for a selected property class"""
    if df_mechem.empty or not property_class:
        return
    
    try:
        # Find ALL possible property class columns
        property_class_cols = []
        possible_class_cols = ['Grade', 'Class', 'Property Class', 'Material Grade', 'Type', 'Designation', 'Material']
        
        for col in df_mechem.columns:
            col_lower = str(col).lower()
            for possible in possible_class_cols:
                if possible.lower() in col_lower:
                    property_class_cols.append(col)
                    break
        
        if not property_class_cols:
            st.info("No property class column found in the data")
            return
        
        # Try to find matching data using ALL property class columns
        filtered_data = pd.DataFrame()
        
        for prop_col in property_class_cols:
            if prop_col in df_mechem.columns:
                # Try exact match
                exact_match = df_mechem[df_mechem[prop_col] == property_class]
                if not exact_match.empty:
                    filtered_data = exact_match
                    break
                # Try string contains
                str_match = df_mechem[df_mechem[prop_col].astype(str).str.contains(str(property_class), na=False, case=False)]
                if not str_match.empty:
                    filtered_data = str_match
                    break
        
        if filtered_data.empty:
            st.info(f"No detailed data found for {property_class}")
            return
        
        st.markdown(f"### Detailed Properties for {property_class}")
        
        # Display the filtered data
        st.dataframe(
            filtered_data,
            use_container_width=True,
            height=400
        )
        
        # Show key properties in a structured way
        st.markdown("#### Key Properties")
        
        mechanical_props = []
        chemical_props = []
        other_props = []
        
        for col in filtered_data.columns:
            col_lower = str(col).lower()
            if col in property_class_cols:
                continue
            
            if any(keyword in col_lower for keyword in ['tensile', 'yield', 'hardness', 'strength', 'elongation', 'proof']):
                mechanical_props.append(col)
            elif any(keyword in col_lower for keyword in ['carbon', 'manganese', 'phosphorus', 'sulfur', 'chromium', 'nickel', 'chemical']):
                chemical_props.append(col)
            else:
                other_props.append(col)
        
        if mechanical_props:
            st.markdown("**Mechanical Properties:**")
            mech_cols = st.columns(min(3, len(mechanical_props)))
            for idx, prop in enumerate(mechanical_props):
                with mech_cols[idx % len(mech_cols)]:
                    value = filtered_data[prop].iloc[0] if not filtered_data[prop].isna().all() else "N/A"
                    st.metric(prop, value)
        
        if chemical_props:
            st.markdown("**Chemical Composition (%):**")
            chem_cols = st.columns(min(4, len(chemical_props)))
            for idx, prop in enumerate(chemical_props):
                with chem_cols[idx % len(chem_cols)]:
                    value = filtered_data[prop].iloc[0] if not filtered_data[prop].isna().all() else "N/A"
                    st.metric(prop, value)
                    
    except Exception as e:
        st.error(f"Error displaying mechanical/chemical details: {str(e)}")

# Initialize Mechanical & Chemical data processing
me_chem_columns, property_classes = process_mechanical_chemical_data()

# ======================================================
# COMPLETELY BULLETPROOF SIZE HANDLING - FIXED VERSION
# ======================================================
def size_to_float(size_str):
    """Convert size string to float for sorting - ULTRA ROBUST VERSION"""
    try:
        if pd.isna(size_str) or not isinstance(size_str, (str, int, float)):
            return 0.0
        
        size_str = str(size_str).strip()
        if not size_str or size_str == "":
            return 0.0
        
        # Handle numeric sizes (0,1,2,3 etc)
        if size_str.isdigit():
            return float(size_str)
        
        if size_str.startswith('M'):
            match = re.match(r'M\s*([\d.]+)', size_str)
            if match:
                return float(match.group(1))
            return 0.0
        
        if "/" in size_str:
            try:
                if "-" in size_str:
                    parts = size_str.split("-")
                    whole = float(parts[0]) if parts[0] else 0
                    fraction = float(Fraction(parts[1]))
                    return whole + fraction
                else:
                    return float(Fraction(size_str))
            except:
                return 0.0
        
        try:
            return float(size_str)
        except:
            return 0.0
        
    except Exception as e:
        return 0.0

def safe_sort_sizes(size_list):
    """Safely sort size list with multiple fallbacks"""
    if not size_list or len(size_list) == 0:
        return []
    
    try:
        return sorted(size_list, key=lambda x: (size_to_float(x), str(x)))
    except:
        try:
            return sorted(size_list, key=str)
        except:
            return list(size_list)

def get_safe_size_options(temp_df):
    """Completely safe way to get size options - FIXED VERSION"""
    size_options = ["All"]
    
    if temp_df is None or temp_df.empty:
        return size_options
    
    if 'Size' not in temp_df.columns:
        return size_options
    
    try:
        # Get unique sizes and handle NaN values properly
        unique_sizes = temp_df['Size'].dropna().unique()
        
        # Convert all sizes to string and filter out empty strings
        unique_sizes = [str(size) for size in unique_sizes if str(size).strip() != '']
        
        if len(unique_sizes) > 0:
            sorted_sizes = safe_sort_sizes(unique_sizes)
            size_options.extend(sorted_sizes)
        else:
            return ["All"]
    except Exception as e:
        st.warning(f"Size processing warning: {str(e)}")
        try:
            unique_sizes = temp_df['Size'].dropna().unique()
            unique_sizes = [str(size) for size in unique_sizes if str(size).strip() != '']
            size_options.extend(list(unique_sizes))
        except:
            pass
    
    return size_options

# ======================================================
# NEW: GRADE HANDLING FUNCTIONS FOR ISO 4014
# ======================================================
def get_available_grades_for_standard_product(standard, product):
    """Get available grades for specific standard and product"""
    grade_options = ["All"]
    
    if standard == "Select Standard" or product == "Select Product":
        return grade_options
    
    # Only ISO 4014 has product grades A and B
    if standard == "ISO 4014" and product == "Hex Bolt":
        # Get the appropriate dataframe
        temp_df = df_iso4014.copy()
        
        # Filter by product if specified
        if product != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product]
        
        # Get grade options from the data
        if 'Product Grade' in temp_df.columns:
            unique_grades = temp_df['Product Grade'].dropna().unique()
            unique_grades = [str(grade).strip() for grade in unique_grades if str(grade).strip() != '']
            if len(unique_grades) > 0:
                grade_options.extend(sorted(unique_grades))
        else:
            # Default grades for ISO 4014 Hex Bolt
            grade_options.extend(["A", "B"])
    
    return grade_options

def get_sizes_for_standard_product_grade(standard, product, grade):
    """Get available sizes for specific standard, product and grade"""
    size_options = ["Select Size"]
    
    if standard == "Select Standard" or product == "Select Product":
        return size_options
    
    # Get the appropriate dataframe based on standard
    if standard == "ASME B18.2.1":
        temp_df = df.copy()
    elif standard == "ISO 4014":
        temp_df = df_iso4014.copy()
    elif standard == "DIN-7991":
        temp_df = df_din7991.copy()
    elif standard == "ASME B18.3":
        temp_df = df_asme_b18_3.copy()
    else:
        return size_options
    
    # Filter by product if specified
    if product != "All" and 'Product' in temp_df.columns:
        temp_df = temp_df[temp_df['Product'] == product]
    
    # Filter by grade if specified (only for ISO 4014)
    if standard == "ISO 4014" and grade != "All" and 'Product Grade' in temp_df.columns:
        temp_df = temp_df[temp_df['Product Grade'] == grade]
    
    # Get size options
    size_options = get_safe_size_options(temp_df)
    
    return ["Select Size"] + [size for size in size_options if size != "All"]

# ======================================================
# UNIT CONVERSION FUNCTIONS - ENHANCED FOR INCH SERIES
# ======================================================
def convert_to_mm(value, from_unit, series=None):
    """Convert any unit to millimeters - ENHANCED with series detection"""
    try:
        if pd.isna(value):
            return 0.0
        
        value = float(value)
        
        # If series is specified as "Inch", assume the value is in inches and convert to mm
        if series == "Inch":
            return value * 25.4
        
        # Standard unit conversion
        if from_unit == 'mm':
            return value
        elif from_unit == 'inch':
            return value * 25.4
        elif from_unit == 'ft':
            return value * 304.8
        elif from_unit == 'meter':
            return value * 1000
        else:
            return value  # Assume mm if unknown unit
    except Exception as e:
        st.warning(f"Unit conversion error: {str(e)}")
        return value

def convert_to_meters(value, from_unit, series=None):
    """Convert any unit to meters - ENHANCED with series detection"""
    try:
        if pd.isna(value):
            return 0.0
        
        value = float(value)
        
        # If series is specified as "Inch", assume the value is in inches and convert to meters
        if series == "Inch":
            return value * 0.0254
        
        # Standard unit conversion
        if from_unit == 'mm':
            return value / 1000
        elif from_unit == 'inch':
            return value * 0.0254
        elif from_unit == 'ft':
            return value * 0.3048
        elif from_unit == 'meter':
            return value
        else:
            return value / 1000  # Assume mm if unknown unit
    except Exception as e:
        st.warning(f"Unit conversion error: {str(e)}")
        return value / 1000

# ======================================================
# ENHANCED WEIGHT CALCULATION FUNCTIONS FOR HEX PRODUCTS
# ======================================================

def get_hex_head_dimensions(standard, product, size, grade="All"):
    """Get width across flats and head height for hex products from database"""
    try:
        # Get the appropriate dataframe based on standard
        if standard == "ASME B18.2.1":
            temp_df = df.copy()
        elif standard == "ISO 4014":
            temp_df = df_iso4014.copy()
        elif standard == "DIN-7991":
            temp_df = df_din7991.copy()
        elif standard == "ASME B18.3":
            temp_df = df_asme_b18_3.copy()
        else:
            return None, None
        
        # Filter by product and size
        if 'Product' in temp_df.columns and product != "All":
            temp_df = temp_df[temp_df['Product'] == product]
        
        if 'Size' in temp_df.columns and size != "All":
            # Normalize size comparison
            temp_df = temp_df[temp_df['Size'].astype(str).str.strip() == str(size).strip()]
        
        # Filter by grade if specified (only for ISO 4014)
        if standard == "ISO 4014" and grade != "All" and 'Product Grade' in temp_df.columns:
            temp_df = temp_df[temp_df['Product Grade'] == grade]
        
        if temp_df.empty:
            return None, None
        
        # Look for width across flats column
        width_cols = [col for col in temp_df.columns if any(keyword in col.lower() for keyword in ['width', 'across', 'flats', 'w_'])]
        width_col = None
        for col in width_cols:
            if 'min' in col.lower():
                width_col = col
                break
        if not width_col and width_cols:
            width_col = width_cols[0]
        
        # Look for head height column
        height_cols = [col for col in temp_df.columns if any(keyword in col.lower() for keyword in ['head', 'height', 'head_height'])]
        height_col = None
        for col in height_cols:
            if 'min' in col.lower():
                height_col = col
                break
        if not height_col and height_cols:
            height_col = height_cols[0]
        
        width_across_flats = None
        head_height = None
        
        if width_col and width_col in temp_df.columns:
            width_across_flats = temp_df[width_col].iloc[0]
            if pd.notna(width_across_flats):
                width_across_flats = float(width_across_flats)
        
        if height_col and height_col in temp_df.columns:
            head_height = temp_df[height_col].iloc[0]
            if pd.notna(head_height):
                head_height = float(head_height)
        
        return width_across_flats, head_height
        
    except Exception as e:
        st.warning(f"Error getting hex head dimensions: {str(e)}")
        return None, None

def calculate_hex_product_weight_enhanced(parameters, width_across_flats, head_height):
    """ENHANCED: Calculate weight for hex products using the specific formula provided"""
    try:
        # Extract parameters
        product_type = parameters.get('product_type', 'Hex Bolt')
        diameter_type = parameters.get('diameter_type', 'Blank Diameter')
        diameter_value = parameters.get('diameter_value', 0.0)
        diameter_unit = parameters.get('diameter_unit', 'mm')
        length = parameters.get('length', 0.0)
        length_unit = parameters.get('length_unit', 'mm')
        material = parameters.get('material', 'Carbon Steel')
        series = parameters.get('series', 'Metric')
        
        # Convert all dimensions to meters for calculation
        if diameter_unit == 'mm':
            diameter_m = convert_to_meters(diameter_value, 'mm', series)
        elif diameter_unit == 'inch':
            diameter_m = convert_to_meters(diameter_value, 'inch', series)
        elif diameter_unit == 'ft':
            diameter_m = convert_to_meters(diameter_value, 'ft', series)
        else:  # meters
            diameter_m = convert_to_meters(diameter_value, 'meter', series)
        
        if length_unit == 'mm':
            length_m = convert_to_meters(length, 'mm', series)
        elif length_unit == 'inch':
            length_m = convert_to_meters(length, 'inch', series)
        elif length_unit == 'ft':
            length_m = convert_to_meters(length, 'ft', series)
        else:  # meters
            length_m = convert_to_meters(length, 'meter', series)
        
        # Convert head dimensions to meters
        if width_across_flats is not None:
            width_across_flats_m = convert_to_meters(width_across_flats, 'mm', series)
        else:
            width_across_flats_m = diameter_m * 1.5  # Default ratio if not available
        
        if head_height is not None:
            head_height_m = convert_to_meters(head_height, 'mm', series)
        else:
            head_height_m = diameter_m * 0.65  # Default ratio if not available
        
        # Get material density
        density = get_material_density(material)  # kg/m³
        
        # 1. Calculate Shank Volume (Cylinder Volume)
        # Formula: Pi x (Body Diameter or Pitch Diameter/2)² x Length
        shank_radius = diameter_m / 2
        shank_volume = math.pi * shank_radius**2 * length_m  # m³
        
        # 2. Calculate Head Volume using the specific formula
        # RECTIFIED: Side Length = Width Across Flats × 1.1547
        side_length = width_across_flats_m * 1.1547
        
        # Head Volume = 0.65 x (Side Length²) x Head height (Min)
        head_volume = 0.65 * (side_length**2) * head_height_m
        
        # 3. Total Volume = Cylinder Volume or Shank Volume + Head Volume
        total_volume = shank_volume + head_volume
        
        # 4. Calculate Weight = Total volume x Density
        weight_kg = total_volume * density
        
        return {
            'weight_kg': weight_kg,
            'weight_g': weight_kg * 1000,
            'weight_lb': weight_kg * 2.20462,
            'shank_volume_m3': shank_volume,
            'head_volume_m3': head_volume,
            'total_volume_m3': total_volume,
            'diameter_m': diameter_m,
            'length_m': length_m,
            'width_across_flats_m': width_across_flats_m,
            'head_height_m': head_height_m,
            'side_length_m': side_length,
            'density': density,
            'series': series,
            'original_diameter': f"{diameter_value} {diameter_unit}",
            'original_length': f"{length} {length_unit}",
            'calculation_method': 'Enhanced Hex Product Formula',
            'formula_details': {
                'shank_volume_formula': 'π × (diameter/2)² × length',
                'head_volume_formula': '0.65 × side_length² × head_height',
                'side_length_formula': 'width_across_flats × 1.1547',
                'total_volume_formula': 'shank_volume + head_volume',
                'weight_formula': 'total_volume × density'
            }
        }
        
    except Exception as e:
        st.error(f"Enhanced hex product calculation error: {str(e)}")
        return None

# ======================================================
# WEIGHT CALCULATION SECTION - COMPLETE WORKFLOW IMPLEMENTATION
# ======================================================

def get_available_products():
    """Get all available products from standards database"""
    all_products = set()
    for standard_products_list in st.session_state.available_products.values():
        all_products.update(standard_products_list)
    return ["Select Product"] + sorted([p for p in all_products if p != "All"])

def get_series_for_product(product):
    """Get available series for a specific product"""
    if product == "Select Product":
        return ["Select Series"]
    
    available_series = set()
    for standard, products in st.session_state.available_products.items():
        if product in products:
            series = st.session_state.available_series.get(standard, "")
            if series:
                available_series.add(series)
    
    return ["Select Series"] + sorted(list(available_series))

def get_standards_for_product_series(product, series):
    """Get available standards for specific product and series"""
    if product == "Select Product" or series == "Select Series":
        return ["Select Standard"]
    
    available_standards = []
    for standard, products in st.session_state.available_products.items():
        if product in products:
            std_series = st.session_state.available_series.get(standard, "")
            if std_series == series:
                available_standards.append(standard)
    
    return ["Select Standard"] + sorted(available_standards)

def get_sizes_for_standard_product(standard, product):
    """Get available sizes for specific standard and product in weight calculator"""
    if standard == "Select Standard" or product == "Select Product":
        return ["Select Size"]
    
    # Get the appropriate dataframe based on standard
    if standard == "ASME B18.2.1":
        temp_df = df.copy()
    elif standard == "ISO 4014":
        temp_df = df_iso4014.copy()
    elif standard == "DIN-7991":
        temp_df = df_din7991.copy()
    elif standard == "ASME B18.3":
        temp_df = df_asme_b18_3.copy()
    else:
        return ["Select Size"]
    
    # Filter by product if specified
    if product != "All" and 'Product' in temp_df.columns:
        temp_df = temp_df[temp_df['Product'] == product]
    
    # Get size options
    size_options = get_safe_size_options(temp_df)
    
    return ["Select Size"] + [size for size in size_options if size != "All"]

def get_thread_standards_for_series(series):
    """Get thread standards based on series"""
    if series == "Inch":
        return ["ASME B1.1"]
    elif series == "Metric":
        return ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
    return ["Select Thread Standard"]

def get_material_density(material):
    """Get density for different materials in kg/m³"""
    density_map = {
        "Carbon Steel": 7850,
        "Stainless Steel": 8000,
        "Alloy Steel": 7850,
        "Brass": 8500,
        "Aluminum": 2700,
        "Copper": 8960,
        "Titanium": 4500,
        "Bronze": 8800,
        "Inconel": 8200,
        "Monel": 8800,
        "Nickel": 8900
    }
    return density_map.get(material, 7850)  # Default to carbon steel

def get_pitch_diameter_from_thread_data(thread_standard, thread_size, thread_class):
    """Get pitch diameter from thread data for threaded rod calculation - ENHANCED FOR THREADED ROD"""
    try:
        df_thread = get_thread_data_enhanced(thread_standard, thread_size, thread_class)
        
        if df_thread.empty:
            return None
        
        # Look for pitch diameter columns - prioritize minimum pitch diameter for threaded rod
        pitch_dia_cols = []
        
        # First priority: Pitch diameter minimum columns
        min_pitch_cols = [col for col in df_thread.columns if 'pitch' in col.lower() and 'diameter' in col.lower() and 'min' in col.lower()]
        if min_pitch_cols:
            pitch_dia_cols.extend(min_pitch_cols)
        
        # Second priority: Any pitch diameter columns
        general_pitch_cols = [col for col in df_thread.columns if 'pitch' in col.lower() and 'diameter' in col.lower()]
        if general_pitch_cols:
            pitch_dia_cols.extend([col for col in general_pitch_cols if col not in pitch_dia_cols])
        
        # Third priority: Any diameter column that might contain pitch diameter
        if not pitch_dia_cols:
            dia_cols = [col for col in df_thread.columns if 'diameter' in col.lower()]
            for col in dia_cols:
                if 'pitch' not in col.lower() and 'major' not in col.lower() and 'minor' not in col.lower():
                    pitch_dia_cols.append(col)
        
        if pitch_dia_cols:
            # Get the first pitch diameter value
            pitch_diameter = df_thread[pitch_dia_cols[0]].iloc[0]
            if pd.notna(pitch_diameter):
                return float(pitch_diameter)
        
        return None
        
    except Exception as e:
        st.warning(f"Could not retrieve pitch diameter: {str(e)}")
        return None

def calculate_weight_enhanced(parameters):
    """Enhanced weight calculation with proper material densities and geometry - FIXED DIAMETER CONVERSION"""
    try:
        # Extract parameters
        product_type = parameters.get('product_type', 'Hex Bolt')
        diameter_type = parameters.get('diameter_type', 'Blank Diameter')
        diameter_value = parameters.get('diameter_value', 0.0)
        diameter_unit = parameters.get('diameter_unit', 'mm')
        length = parameters.get('length', 0.0)
        length_unit = parameters.get('length_unit', 'mm')
        material = parameters.get('material', 'Carbon Steel')
        series = parameters.get('series', 'Metric')
        standard = parameters.get('standard', 'ASME B18.2.1')
        size = parameters.get('size', 'All')
        grade = parameters.get('grade', 'All')  # NEW: Added grade parameter
        
        # Get hex head dimensions from database
        width_across_flats, head_height = get_hex_head_dimensions(standard, product_type, size, grade)
        
        # If dimensions not found in database, use default ratios
        if width_across_flats is None:
            # Estimate width across flats based on diameter
            if diameter_unit == 'inch':
                diameter_mm = diameter_value * 25.4
            else:
                diameter_mm = diameter_value
            width_across_flats = diameter_mm * 1.5  # Default ratio
        
        if head_height is None:
            # Estimate head height based on diameter
            if diameter_unit == 'inch':
                diameter_mm = diameter_value * 25.4
            else:
                diameter_mm = diameter_value
            head_height = diameter_mm * 0.65  # Default ratio
        
        hex_products = ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screws", "Heavy Hex Screws"]
        
        # Convert length to meters based on unit and series
        if length_unit == 'ft':
            length_m = length * 0.3048  # 1 ft = 0.3048 meters
        elif length_unit == 'inch':
            length_m = length * 0.0254  # 1 inch = 0.0254 meters
        elif length_unit == 'mm':
            length_m = length / 1000  # 1 mm = 0.001 meters
        else:  # meters
            length_m = length

        # --- CORRECTED DIAMETER CONVERSION LOGIC ---
        # ALWAYS convert diameter to meters based on the input unit
        if diameter_unit == 'ft':
            diameter_m = diameter_value * 0.3048  # feet to meters
        elif diameter_unit == 'inch':
            diameter_m = diameter_value * 0.0254  # inches to meters
        elif diameter_unit == 'mm':
            diameter_m = diameter_value / 1000    # mm to meters
        else:  # meters or unknown
            diameter_m = diameter_value

        # SPECIAL CASE: For Pitch Diameter from thread data in Inch series
        # Thread data from ASME B1.1 is in inches, so if we have pitch diameter value from thread data
        # and the series is Inch, we need to ensure it's converted from inches to meters
        if (diameter_type == "Pitch Diameter" and 
            series == "Inch" and 
            'pitch_diameter_value' in st.session_state):
            
            # Use the pitch diameter from thread data and convert from inches to meters
            pitch_diameter_inches = st.session_state.pitch_diameter_value
            diameter_m = pitch_diameter_inches * 0.0254  # Convert inches to meters

        # Convert head dimensions to meters
        if width_across_flats is not None:
            width_across_flats_m = width_across_flats / 1000  # Convert mm to meters
        else:
            width_across_flats_m = diameter_m * 1.5  # Default ratio if not available
        
        if head_height is not None:
            head_height_m = head_height / 1000  # Convert mm to meters
        else:
            head_height_m = diameter_m * 0.65  # Default ratio if not available
        
        # Get material density
        density = get_material_density(material)  # kg/m³
        
        # For Threaded Rod, use simple cylinder volume calculation
        if product_type == "Threaded Rod":
            # Simple cylinder volume for threaded rod
            radius = diameter_m / 2
            volume = math.pi * radius**2 * length_m
            weight_kg = volume * density
            
            return {
                'weight_kg': weight_kg,
                'weight_g': weight_kg * 1000,
                'weight_lb': weight_kg * 2.20462,
                'volume_m3': volume,
                'density': density,
                'diameter_m': diameter_m,
                'length_m': length_m,
                'series': series,
                'original_diameter': f"{diameter_value} {diameter_unit}",
                'original_length': f"{length} {length_unit}",
                'calculation_method': 'Threaded Rod Cylinder Formula',
                'dimensions_used': {
                    'diameter_input': f"{diameter_value} {diameter_unit}",
                    'diameter_calculation_m': diameter_m,
                    'diameter_calculation_mm': diameter_m * 1000,
                    'length_input': f"{length} {length_unit}",
                    'length_calculation_m': length_m,
                    'length_calculation_mm': length_m * 1000,
                    'radius_m': radius,
                    'volume_m3': volume,
                    'density_kg_m3': density
                }
            }
        
        # For hex products, use enhanced hex product formula
        elif product_type in hex_products:
            # 1. Calculate Shank Volume (Cylinder Volume)
            # Formula: Pi x (Body Diameter or Pitch Diameter/2)² x Length
            shank_radius = diameter_m / 2
            shank_volume = math.pi * shank_radius**2 * length_m  # m³
            
            # 2. Calculate Head Volume using the specific formula
            # RECTIFIED: Side Length = Width Across Flats × 1.1547
            side_length = width_across_flats_m * 1.1547
            
            # Head Volume = 0.65 x (Side Length²) x Head height (Min)
            head_volume = 0.65 * (side_length**2) * head_height_m
            
            # 3. Total Volume = Cylinder Volume or Shank Volume + Head Volume
            total_volume = shank_volume + head_volume
            
            # 4. Calculate Weight = Total volume x Density
            weight_kg = total_volume * density
            
            return {
                'weight_kg': weight_kg,
                'weight_g': weight_kg * 1000,
                'weight_lb': weight_kg * 2.20462,
                'shank_volume_m3': shank_volume,
                'head_volume_m3': head_volume,
                'total_volume_m3': total_volume,
                'diameter_m': diameter_m,
                'length_m': length_m,
                'width_across_flats_m': width_across_flats_m,
                'head_height_m': head_height_m,
                'side_length_m': side_length,
                'density': density,
                'series': series,
                'original_diameter': f"{diameter_value} {diameter_unit}",
                'original_length': f"{length} {length_unit}",
                'calculation_method': 'Enhanced Hex Product Formula',
                'formula_details': {
                    'shank_volume_formula': 'π × (diameter/2)² × length',
                    'head_volume_formula': '0.65 × side_length² × head_height',
                    'side_length_formula': 'width_across_flats × 1.1547',
                    'total_volume_formula': 'shank_volume + head_volume',
                    'weight_formula': 'total_volume × density'
                },
                'dimensions_used': {
                    'diameter_input': f"{diameter_value} {diameter_unit}",
                    'diameter_calculation_m': diameter_m,
                    'diameter_calculation_mm': diameter_m * 1000,
                    'length_input': f"{length} {length_unit}",
                    'length_calculation_m': length_m,
                    'length_calculation_mm': length_m * 1000,
                    'width_across_flats_input': f"{width_across_flats} mm",
                    'width_across_flats_calculation_m': width_across_flats_m,
                    'width_across_flats_calculation_mm': width_across_flats_m * 1000,
                    'head_height_input': f"{head_height} mm",
                    'head_height_calculation_m': head_height_m,
                    'head_height_calculation_mm': head_height_m * 1000,
                    'side_length_calculation_m': side_length,
                    'side_length_calculation_mm': side_length * 1000,
                    'shank_radius_m': shank_radius,
                    'shank_volume_m3': shank_volume,
                    'head_volume_m3': head_volume,
                    'total_volume_m3': total_volume,
                    'density_kg_m3': density,
                    'unit_conversion_applied': series == "Inch"
                }
            }
        
        # For other products, use simple cylinder calculation
        else:
            radius = diameter_m / 2
            volume = math.pi * radius**2 * length_m
            weight_kg = volume * density
            
            return {
                'weight_kg': weight_kg,
                'weight_g': weight_kg * 1000,
                'weight_lb': weight_kg * 2.20462,
                'volume_m3': volume,
                'density': density,
                'diameter_m': diameter_m,
                'length_m': length_m,
                'series': series,
                'original_diameter': f"{diameter_value} {diameter_unit}",
                'original_length': f"{length} {length_unit}",
                'calculation_method': 'Standard Cylinder Formula',
                'dimensions_used': {
                    'diameter_input': f"{diameter_value} {diameter_unit}",
                    'diameter_calculation_m': diameter_m,
                    'diameter_calculation_mm': diameter_m * 1000,
                    'length_input': f"{length} {length_unit}",
                    'length_calculation_m': length_m,
                    'length_calculation_mm': length_m * 1000,
                    'radius_m': radius,
                    'volume_m3': volume,
                    'density_kg_m3': density
                }
            }
            
    except Exception as e:
        st.error(f"Calculation error: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        return None

# ======================================================
# MISSING FUNCTIONS - ADD THESE TO FIX THE ERRORS
# ======================================================

def get_filtered_dataframe(product, standard, grade="All"):
    """Get filtered dataframe based on product and standard selection"""
    if standard == "ASME B18.2.1":
        temp_df = df.copy()
    elif standard == "ISO 4014":
        temp_df = df_iso4014.copy()
    elif standard == "DIN-7991":
        temp_df = df_din7991.copy()
    elif standard == "ASME B18.3":
        temp_df = df_asme_b18_3.copy()
    else:
        return pd.DataFrame()
    
    # Apply product filter if specified
    if product != "All" and 'Product' in temp_df.columns:
        temp_df = temp_df[temp_df['Product'] == product]
    
    # Apply grade filter if specified (only for ISO 4014)
    if standard == "ISO 4014" and grade != "All" and 'Product Grade' in temp_df.columns:
        temp_df = temp_df[temp_df['Product Grade'] == grade]
    
    return temp_df

def apply_section_a_filters():
    """Apply filters for Section A - Dimensional Specifications"""
    filters = st.session_state.section_a_filters
    
    if not filters:
        return pd.DataFrame()
    
    product = filters.get('product', 'All')
    series = filters.get('series', 'All')
    standard = filters.get('standard', 'All')
    size = filters.get('size', 'All')
    grade = filters.get('grade', 'All')  # NEW: Added grade filter
    
    # Get appropriate dataframe
    if standard == "ASME B18.2.1":
        temp_df = df.copy()
    elif standard == "ISO 4014":
        temp_df = df_iso4014.copy()
    elif standard == "DIN-7991":
        temp_df = df_din7991.copy()
    elif standard == "ASME B18.3":
        temp_df = df_asme_b18_3.copy()
    else:
        return pd.DataFrame()
    
    # Apply filters
    if product != "All" and 'Product' in temp_df.columns:
        temp_df = temp_df[temp_df['Product'] == product]
    
    if size != "All" and 'Size' in temp_df.columns:
        temp_df = temp_df[temp_df['Size'].astype(str).str.strip() == str(size).strip()]
    
    # Apply grade filter if specified (only for ISO 4014)
    if standard == "ISO 4014" and grade != "All" and 'Product Grade' in temp_df.columns:
        temp_df = temp_df[temp_df['Product Grade'] == grade]
    
    return temp_df

def apply_section_b_filters():
    """Apply filters for Section B - Thread Specifications"""
    filters = st.session_state.section_b_filters
    
    if not filters:
        return pd.DataFrame()
    
    standard = filters.get('standard', 'All')
    size = filters.get('size', 'All')
    thread_class = filters.get('class', 'All')
    
    if standard == "All":
        return pd.DataFrame()
    
    return get_thread_data_enhanced(standard, size, thread_class)

def apply_section_c_filters():
    """Apply filters for Section C - Material Properties"""
    filters = st.session_state.section_c_filters
    
    if not filters or df_mechem.empty:
        return pd.DataFrame()
    
    property_class = filters.get('property_class', 'All')
    standard = filters.get('standard', 'All')
    
    if property_class == "All":
        return df_mechem.copy()
    
    # Find property class columns
    property_class_cols = []
    possible_class_cols = ['Grade', 'Class', 'Property Class', 'Material Grade', 'Type', 'Designation', 'Material']
    
    for col in df_mechem.columns:
        col_lower = str(col).lower()
        for possible in possible_class_cols:
            if possible.lower() in col_lower:
                property_class_cols.append(col)
                break
    
    # Try to find matching data
    filtered_data = pd.DataFrame()
    
    for prop_col in property_class_cols:
        if prop_col in df_mechem.columns:
            # Try exact match
            exact_match = df_mechem[df_mechem[prop_col] == property_class]
            if not exact_match.empty:
                filtered_data = exact_match
                break
            # Try string contains
            str_match = df_mechem[df_mechem[prop_col].astype(str).str.contains(str(property_class), na=False, case=False)]
            if not str_match.empty:
                filtered_data = str_match
                break
    
    # Apply standard filter if specified
    if standard != "All" and not filtered_data.empty:
        standard_cols = []
        possible_standard_cols = ['Standard', 'Specification', 'Norm', 'Type', 'Designation']
        
        for col in filtered_data.columns:
            col_lower = str(col).lower()
            for possible in possible_standard_cols:
                if possible.lower() in col_lower:
                    standard_cols.append(col)
                    break
        
        if standard_cols:
            for std_col in standard_cols:
                std_filtered = filtered_data[filtered_data[std_col].astype(str).str.contains(str(standard), na=False, case=False)]
                if not std_filtered.empty:
                    filtered_data = std_filtered
                    break
    
    return filtered_data

def show_section_a_results():
    """Show results for Section A"""
    if not st.session_state.section_a_results.empty:
        st.markdown('<div class="section-results">', unsafe_allow_html=True)
        st.markdown("### Section A Results - Dimensional Specifications")
        
        # Show professional card if requested
        if st.session_state.show_professional_card and st.session_state.selected_product_details:
            show_professional_product_card(st.session_state.selected_product_details)
        
        # Show data
        st.dataframe(
            st.session_state.section_a_results,
            use_container_width=True,
            height=400
        )
        
        # Show export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export Section A Results", key="export_section_a"):
                enhanced_export_data(st.session_state.section_a_results, "Excel")
        with col2:
            if st.button("Show Professional Card", key="show_pro_card_a"):
                if not st.session_state.section_a_results.empty:
                    # Extract first row for professional card
                    first_row = st.session_state.section_a_results.iloc[0].to_dict()
                    st.session_state.selected_product_details = extract_product_details(first_row)
                    st.session_state.show_professional_card = True
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_section_b_results():
    """Show results for Section B"""
    if not st.session_state.section_b_results.empty:
        st.markdown('<div class="section-results">', unsafe_allow_html=True)
        st.markdown("### Section B Results - Thread Specifications")
        
        st.dataframe(
            st.session_state.section_b_results,
            use_container_width=True,
            height=400
        )
        
        if st.button("Export Section B Results", key="export_section_b"):
            enhanced_export_data(st.session_state.section_b_results, "Excel")
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_section_c_results():
    """Show results for Section C"""
    if not st.session_state.section_c_results.empty:
        st.markdown('<div class="section-results">', unsafe_allow_html=True)
        st.markdown("### Section C Results - Material Properties")
        
        st.dataframe(
            st.session_state.section_c_results,
            use_container_width=True,
            height=400
        )
        
        # Show detailed properties for selected property class
        if st.session_state.section_c_filters.get('property_class') and st.session_state.section_c_filters.get('property_class') != "All":
            show_mechanical_chemical_details(st.session_state.section_c_filters.get('property_class'))
        
        if st.button("Export Section C Results", key="export_section_c"):
            enhanced_export_data(st.session_state.section_c_results, "Excel")
        
        st.markdown('</div>', unsafe_allow_html=True)

def combine_all_results():
    """Combine results from all sections"""
    combined = pd.DataFrame()
    
    # Add section A results
    if not st.session_state.section_a_results.empty:
        section_a = st.session_state.section_a_results.copy()
        section_a['Section'] = 'A - Dimensional'
        combined = pd.concat([combined, section_a], ignore_index=True)
    
    # Add section B results  
    if not st.session_state.section_b_results.empty:
        section_b = st.session_state.section_b_results.copy()
        section_b['Section'] = 'B - Thread'
        combined = pd.concat([combined, section_b], ignore_index=True)
    
    # Add section C results
    if not st.session_state.section_c_results.empty:
        section_c = st.session_state.section_c_results.copy()
        section_c['Section'] = 'C - Material'
        combined = pd.concat([combined, section_c], ignore_index=True)
    
    return combined

def show_combined_results():
    """Show combined results from all sections"""
    if not st.session_state.combined_results.empty:
        st.markdown('<div class="combined-results">', unsafe_allow_html=True)
        st.markdown("### Combined Results - All Sections")
        
        st.dataframe(
            st.session_state.combined_results,
            use_container_width=True,
            height=500
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export Combined Results", key="export_combined"):
                enhanced_export_data(st.session_state.combined_results, "Excel")
        with col2:
            if st.button("Clear Combined Results", key="clear_combined"):
                st.session_state.combined_results = pd.DataFrame()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_weight_calculator_enhanced():
    """Enhanced weight calculator with complete product standards workflow"""
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
            Weight Calculator - ENHANCED WORKFLOW
        </h1>
        <p style="margin:0; opacity: 0.9;">Complete product standards integration for accurate weight calculations</p>
        <div style="margin-top: 0.5rem;">
            <span class="engineering-badge">Product Standards</span>
            <span class="technical-badge">Dynamic Filtering</span>
            <span class="material-badge">Dimensional Data</span>
            <span class="grade-badge">Thread Specifications</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("""
    **Enhanced Workflow:** Product Type → Series → Standard → Size → Grade (ISO 4014 only) → Diameter Type → (Manual Input or Thread Specs)
    **NEW:** Threaded Rod support with pitch diameter calculation
    **UNIT CONVERSION:** Inch series dimensions automatically converted to mm for calculations
    **RECTIFIED HEX PRODUCT FORMULA:** Specialized calculation for Hex Bolt, Heavy Hex Bolt, Hex Cap Screws, Heavy Hex Screws using specific volume formulas with corrected side length calculation
    **NEW:** ISO 4014 Product Grade selection (A/B) for different dimensions
    """)
    
    # Initialize session state for form inputs
    if 'weight_form_submitted' not in st.session_state:
        st.session_state.weight_form_submitted = False
    
    # Main input form with enhanced workflow
    with st.form("weight_calculator_enhanced"):
        st.markdown("### Product Standards Selection")
        
        col1, col2, col3, col4, col5 = st.columns(5)  # NEW: Added 5th column for grade
        
        with col1:
            # A. Product Type
            product_options = get_available_products()
            selected_product = st.selectbox(
                "A. Product Type",
                product_options,
                key="weight_calc_product_select"
            )
            
            # Show product info
            if selected_product != "Select Product":
                st.caption(f"Selected: {selected_product}")
        
        with col2:
            # B. Series (Inch/Metric)
            series_options = get_series_for_product(selected_product)
            selected_series = st.selectbox(
                "B. Series",
                series_options,
                key="weight_calc_series_select"
            )
            
            # Show series info with unit conversion note
            if selected_series != "Select Series":
                st.caption(f"Series: {selected_series}")
                if selected_series == "Inch":
                    st.caption("⚠️ Dimensions will be converted from inches to mm")
        
        with col3:
            # C. Standard (based on Product + Series) - DISABLED FOR THREADED ROD
            if selected_product == "Threaded Rod":
                st.info("Standard not required for Threaded Rod")
                selected_standard = "Not Required"
                st.session_state.weight_calc_standard_select = "Not Required"
            else:
                standard_options = get_standards_for_product_series(selected_product, selected_series)
                selected_standard = st.selectbox(
                    "C. Standard",
                    standard_options,
                    key="weight_calc_standard_select"
                )
            
            # Show standard info
            if selected_standard != "Select Standard" and selected_standard != "Not Required":
                st.caption(f"Standard: {selected_standard}")
        
        with col4:
            # D. Size (based on Standard + Product) - DISABLED FOR THREADED ROD
            if selected_product == "Threaded Rod":
                st.info("Size not required for Threaded Rod")
                selected_size = "Not Required"
                st.session_state.weight_calc_size_select = "Not Required"
            else:
                size_options = get_sizes_for_standard_product(selected_standard, selected_product)
                selected_size = st.selectbox(
                    "D. Size",
                    size_options,
                    key="weight_calc_size_select"
                )
            
            # Show size info
            if selected_size != "Select Size" and selected_size != "Not Required":
                st.caption(f"Size: {selected_size}")
        
        with col5:
            # NEW: E. Grade (only for ISO 4014 Hex Bolt)
            if selected_standard == "ISO 4014" and selected_product == "Hex Bolt":
                grade_options = get_available_grades_for_standard_product(selected_standard, selected_product)
                selected_grade = st.selectbox(
                    "E. Product Grade",
                    grade_options,
                    key="weight_calc_grade_select"
                )
                
                # Show grade info
                if selected_grade != "All":
                    st.caption(f"Grade: {selected_grade}")
                    st.caption("⚠️ Different dimensions for A/B grades")
            else:
                st.info("Grade not applicable")
                selected_grade = "Not Applicable"
                st.session_state.weight_calc_grade_select = "Not Applicable"
        
        st.markdown("---")
        st.markdown("### Diameter Specification")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # F. Cylinder Diameter Type
            diameter_type_options = ["Blank Diameter", "Pitch Diameter"]
            selected_diameter_type = st.radio(
                "F. Cylinder Diameter Type",
                diameter_type_options,
                key="weight_calc_diameter_type_select"
            )
        
        with col2:
            # G. Conditional Input based on Diameter Type
            if selected_diameter_type == "Blank Diameter":
                st.markdown("**Blank Diameter Input**")
                dia_col1, dia_col2 = st.columns(2)
                with dia_col1:
                    blank_diameter = st.number_input(
                        "Blank Diameter Value",
                        min_value=0.1,
                        value=10.0,
                        step=0.1,
                        key="weight_calc_blank_diameter_input"
                    )
                with dia_col2:
                    blank_dia_unit = st.selectbox(
                        "Unit",
                        ["mm", "inch", "ft"],
                        key="weight_calc_blank_dia_unit_select"
                    )
                
                st.caption(f"Blank Diameter: {blank_diameter} {blank_dia_unit}")
                if selected_series == "Inch" and blank_dia_unit == "inch":
                    st.caption(f"→ {blank_diameter * 25.4:.2f} mm (converted)")
            
            else:  # Pitch Diameter
                st.markdown("**Thread Specification**")
                
                # Thread Standard
                thread_std_options = get_thread_standards_for_series(selected_series)
                if selected_series == "Select Series":
                    thread_std_options = ["Select Thread Standard"]
                
                thread_standard = st.selectbox(
                    "Thread Standard",
                    thread_std_options,
                    key="weight_calc_thread_standard_select"
                )
                
                if thread_standard != "Select Thread Standard":
                    # Thread Size
                    thread_size_options = get_thread_sizes_enhanced(thread_standard)
                    thread_size = st.selectbox(
                        "Thread Size",
                        thread_size_options,
                        key="weight_calc_thread_size_select"
                    )
                    
                    # Thread Class - Only show for Inch series
                    if selected_series == "Inch" and thread_standard == "ASME B1.1":
                        thread_class_options = get_thread_classes_enhanced(thread_standard)
                        if len(thread_class_options) == 1:  # Only "All"
                            thread_class_options = ["2A", "3A", "1A"]
                        thread_class = st.selectbox(
                            "Tolerance Class",
                            thread_class_options,
                            key="weight_calc_thread_class_select"
                        )
                    else:
                        # For metric threads or non-ASME standards, don't show tolerance class
                        thread_class = "N/A"
                        st.caption("Tolerance Class: Not applicable for metric threads")
                    
                    st.caption(f"Thread: {thread_standard}, Size: {thread_size}, Class: {thread_class}")
                    
                    # Show pitch diameter information for ALL products using Pitch Diameter
                    if selected_diameter_type == "Pitch Diameter" and thread_size != "All":
                        pitch_diameter = get_pitch_diameter_from_thread_data(thread_standard, thread_size, thread_class)
                        if pitch_diameter:
                            # Store the pitch diameter in session state for calculation
                            st.session_state.pitch_diameter_value = pitch_diameter
                            
                            # Display information
                            if selected_series == "Inch":
                                # For Inch series, pitch diameter from ASME B1.1 is in inches
                                pitch_diameter_mm = pitch_diameter * 25.4
                                st.success(f"Pitch Diameter (Min): {pitch_diameter:.4f} in → {pitch_diameter_mm:.4f} mm")
                                st.info(f"⚠️ For calculation: {pitch_diameter:.4f} in will be converted to meters")
                            else:
                                # For Metric series, pitch diameter is already in mm
                                st.success(f"Pitch Diameter (Min): {pitch_diameter:.4f} mm")
                                st.info(f"⚠️ For calculation: {pitch_diameter:.4f} mm will be converted to meters")
                        else:
                            st.warning("Pitch diameter not found in thread data")
        
        st.markdown("---")
        st.markdown("### Additional Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Length - UPDATED WITH FT UNIT
            length_col1, length_col2 = st.columns(2)
            with length_col1:
                length = st.number_input(
                    "Length",
                    min_value=0.1,
                    value=50.0,
                    step=0.1,
                    key="weight_calc_length_input"
                )
            with length_col2:
                length_unit = st.selectbox(
                    "Unit",
                    ["mm", "inch", "ft", "meter"],
                    key="weight_calc_length_unit_select"
                )
            
            # Show length conversion for Inch series
            if selected_series == "Inch" and length_unit == "inch":
                st.caption(f"→ {length * 25.4:.2f} mm (converted)")
        
        with col2:
            # Material - UPDATED WITH MORE MATERIALS
            material_options = ["Carbon Steel", "Stainless Steel", "Alloy Steel", "Brass", "Aluminum", 
                              "Copper", "Titanium", "Bronze", "Inconel", "Monel", "Nickel"]
            material = st.selectbox(
                "Material",
                material_options,
                key="weight_calc_material_select"
            )
            
            # Show material density
            density = get_material_density(material)
            st.caption(f"Density: {density} kg/m³")
        
        with col3:
            # Calculate button space
            st.markdown("<br>", unsafe_allow_html=True)
            calculate_btn = st.form_submit_button("Calculate Weight", use_container_width=True, type="primary")
    
    # Handle form submission
    if calculate_btn:
        # Validate inputs
        validation_errors = []
        
        if selected_product == "Select Product":
            validation_errors.append("Please select a Product Type")
        if selected_series == "Select Series":
            validation_errors.append("Please select a Series")
        
        # Skip Standard and Size validation for Threaded Rod
        if selected_product != "Threaded Rod":
            if selected_standard == "Select Standard":
                validation_errors.append("Please select a Standard")
            if selected_size == "Select Size":
                validation_errors.append("Please select a Size")
        
        if selected_diameter_type == "Pitch Diameter" and thread_standard == "Select Thread Standard":
            validation_errors.append("Please select a Thread Standard for Pitch Diameter")
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            # Prepare calculation parameters
            calculation_params = {
                'product_type': selected_product,
                'diameter_type': selected_diameter_type,
                'material': material,
                'length': length,
                'length_unit': length_unit,
                'series': selected_series,  # Pass series for unit conversion
                'standard': selected_standard,
                'size': selected_size,
                'grade': selected_grade if selected_standard == "ISO 4014" and selected_product == "Hex Bolt" else "All"
            }
            
            # Add diameter parameters based on type
            if selected_diameter_type == "Blank Diameter":
                calculation_params.update({
                    'diameter_value': blank_diameter,
                    'diameter_unit': blank_dia_unit
                })
            else:
                # For pitch diameter, use the pitch diameter value stored in session state
                if 'pitch_diameter_value' in st.session_state:
                    pitch_diameter = st.session_state.pitch_diameter_value
                    
                    # For Inch series, pitch diameter from ASME B1.1 is in inches
                    if selected_series == "Inch":
                        calculation_params.update({
                            'diameter_value': pitch_diameter,
                            'diameter_unit': 'inch'  # ASME B1.1 data is in inches
                        })
                        st.success(f"Using Pitch Diameter: {pitch_diameter:.4f} inches for calculation")
                    else:
                        # For Metric series, pitch diameter is in mm
                        calculation_params.update({
                            'diameter_value': pitch_diameter,
                            'diameter_unit': 'mm'  # ISO thread data is in mm
                        })
                        st.success(f"Using Pitch Diameter: {pitch_diameter:.4f} mm for calculation")
                else:
                    st.error("Pitch diameter not available for calculation")
                    return
            
            # Perform calculation
            result = calculate_weight_enhanced(calculation_params)
            
            if result:
                st.session_state.weight_calc_result = result
                st.session_state.weight_calculation_performed = True
                
                # Save to calculation history
                calculation_data = {
                    'product': selected_product,
                    'series': selected_series,
                    'size': selected_size if selected_product != "Threaded Rod" else "Threaded Rod",
                    'grade': selected_grade if selected_standard == "ISO 4014" and selected_product == "Hex Bolt" else "N/A",
                    'diameter': f"{blank_diameter if selected_diameter_type == 'Blank Diameter' else thread_size} {blank_dia_unit if selected_diameter_type == 'Blank Diameter' else 'mm'}",
                    'length': f"{length} {length_unit}",
                    'material': material,
                    'weight_kg': result['weight_kg'],
                    'weight_lb': result['weight_lb'],
                    'timestamp': datetime.now().isoformat()
                }
                save_calculation_history(calculation_data)
                
                st.success("**Weight Calculation Completed Successfully!**")
    
    # Display current selection summary
    if selected_product != "Select Product":
        st.markdown("### Current Selection Summary")
        
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.markdown(f"""
            **Product Standards:**
            - **Product Type:** {selected_product}
            - **Series:** {selected_series}
            - **Standard:** {selected_standard if selected_product != "Threaded Rod" else "Not Required (Threaded Rod)"}
            - **Size:** {selected_size if selected_product != "Threaded Rod" else "Not Required (Threaded Rod)"}
            - **Grade:** {selected_grade if selected_standard == "ISO 4014" and selected_product == "Hex Bolt" else "Not Applicable"}
            """)
        
        with summary_col2:
            if selected_diameter_type == "Blank Diameter":
                st.markdown(f"""
                **Diameter Specification:**
                - **Type:** {selected_diameter_type}
                - **Value:** {blank_diameter} {blank_dia_unit}
                """)
            else:
                st.markdown(f"""
                **Diameter Specification:**
                - **Type:** {selected_diameter_type}
                - **Thread Standard:** {thread_standard}
                - **Thread Size:** {thread_size}
                - **Thread Class:** {thread_class}
                """)
        
        st.markdown(f"""
        **Additional Parameters:**
        - **Length:** {length} {length_unit}
        - **Material:** {material}
        - **Material Density:** {get_material_density(material)} kg/m³
        - **Series Unit Handling:** {'Inch → mm conversion' if selected_series == 'Inch' else 'Metric (mm)'}
        """)
    
    # Display calculation results - ENHANCED WITH DETAILED DIMENSIONS
    if st.session_state.weight_calculation_performed and st.session_state.weight_calc_result:
        result = st.session_state.weight_calc_result
        
        st.markdown("### Calculation Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Weight (kg)", f"{result['weight_kg']:.4f}")
        with col2:
            st.metric("Weight (grams)", f"{result['weight_g']:.2f}")
        with col3:
            st.metric("Weight (pounds)", f"{result['weight_lb']:.4f}")
        with col4:
            st.metric("Density", f"{result['density']} kg/m³")
        
        # ENHANCED: Detailed results with ALL dimensions used
        with st.expander("📐 Detailed Calculation Parameters - ALL DIMENSIONS USED"):
            calculation_method = result.get('calculation_method', 'Standard Cylinder Formula')
            
            # Show calculation method
            st.markdown(f"**Calculation Method:** `{calculation_method}`")
            
            # Show ALL dimensions used in calculation
            if 'dimensions_used' in result:
                dimensions = result['dimensions_used']
                
                st.markdown("### 📏 Dimensions Used in Calculation")
                
                # Create columns for better layout
                dim_col1, dim_col2 = st.columns(2)
                
                with dim_col1:
                    st.markdown("#### Input Values")
                    for key, value in dimensions.items():
                        if 'input' in key.lower():
                            st.markdown(f"- **{key.replace('_', ' ').title()}:** `{value}`")
                
                with dim_col2:
                    st.markdown("#### Calculated Values (Meters)")
                    for key, value in dimensions.items():
                        if 'calculation' in key.lower() and 'm' in key and 'mm' not in key:
                            st.markdown(f"- **{key.replace('_', ' ').title()}:** `{value:.6f} m`")
                
                # Show millimeter conversions
                st.markdown("#### Converted Values (Millimeters)")
                mm_col1, mm_col2 = st.columns(2)
                with mm_col1:
                    for key, value in dimensions.items():
                        if 'calculation_mm' in key:
                            st.markdown(f"- **{key.replace('_calculation_mm', '').replace('_', ' ').title()}:** `{value:.2f} mm`")
                
                with mm_col2:
                    # Show key calculation parameters
                    st.markdown("#### Key Parameters")
                    if 'radius_m' in dimensions:
                        st.markdown(f"- **Radius:** `{dimensions['radius_m']:.6f} m`")
                    if 'volume_m3' in dimensions:
                        st.markdown(f"- **Volume:** `{dimensions['volume_m3']:.8f} m³`")
                    elif 'total_volume_m3' in dimensions:
                        st.markdown(f"- **Total Volume:** `{dimensions['total_volume_m3']:.8f} m³`")
                        if 'shank_volume_m3' in dimensions:
                            st.markdown(f"- **Shank Volume:** `{dimensions['shank_volume_m3']:.8f} m³`")
                        if 'head_volume_m3' in dimensions:
                            st.markdown(f"- **Head Volume:** `{dimensions['head_volume_m3']:.8f} m³`")
                    st.markdown(f"- **Density:** `{dimensions['density_kg_m3']} kg/m³`")
                
                # Show unit conversion info if applicable
                if dimensions.get('unit_conversion_applied', False):
                    st.info("**Unit Conversion Applied:** Inch dimensions were automatically converted to millimeters for calculation")
            
            # Show formula details for hex products
            if calculation_method == 'Enhanced Hex Product Formula' and 'formula_details' in result:
                st.markdown("### 🧮 Formula Details")
                formulas = result['formula_details']
                for formula_name, formula in formulas.items():
                    st.markdown(f"- **{formula_name.replace('_', ' ').title()}:** `{formula}`")
            
            # Show RECTIFIED hex product specific details
            if calculation_method == 'Enhanced Hex Product Formula':
                st.markdown("### 🔧 RECTIFIED Hex Product Specific Details")
                st.markdown(f"""
                **Shank Volume Calculation:**
                - Formula: π × (diameter/2)² × length
                - Result: `{result['shank_volume_m3']:.8f} m³`
                
                **Head Volume Calculation:**
                - Side Length Formula: Width Across Flats × 1.1547
                - Side Length: `{result['side_length_m']:.6f} m` ({result['side_length_m'] * 1000:.2f} mm)
                - Head Volume Formula: 0.65 × side_length² × head_height
                - Result: `{result['head_volume_m3']:.8f} m³`
                
                **Total Volume:**
                - Formula: shank_volume + head_volume
                - Result: `{result['total_volume_m3']:.8f} m³`
                
                **Weight Calculation:**
                - Formula: total_volume × density
                - Result: `{result['weight_kg']:.4f} kg`
                """)
            
            # Show unit conversion details for Inch series
            if result['series'] == "Inch":
                st.markdown("### 🔄 Unit Conversion Details (Inch Series)")
                st.markdown("""
                **Automatic Unit Conversion Applied:**
                - All inch dimensions automatically converted to mm for calculation
                - Conversion factor: 1 inch = 25.4 mm
                - Weight calculations performed in metric units (kg/m³)
                - Final results converted back to desired units
                """)

def show_batch_calculator_enhanced():
    """Enhanced batch calculator with same workflow"""
    
    st.markdown("### Batch Weight Calculator - ENHANCED WORKFLOW")
    
    st.info("""
    **Batch processing with the same product standards workflow**
    Upload a CSV/Excel file with columns matching the single calculator inputs.
    **UNIT CONVERSION:** Inch series dimensions automatically converted to mm
    **RECTIFIED HEX PRODUCT FORMULA:** Specialized calculation for hex products using specific volume formulas with corrected side length calculation
    **NEW:** ISO 4014 Product Grade selection (A/B) for different dimensions
    """)
    
    # Download template
    st.markdown("### Download Enhanced Batch Template")
    template_data = {
        'Product_Type': ['Hex Bolt', 'Heavy Hex Bolt', 'Threaded Rod', 'Hex Cap Screws', 'Hex Bolt'],
        'Series': ['Inch', 'Inch', 'Inch', 'Inch', 'Metric'],
        'Standard': ['ASME B18.2.1', 'ASME B18.2.1', 'Not Required', 'ASME B18.2.1', 'ISO 4014'],
        'Size': ['1/4', '5/16', 'Not Required', '3/8', 'M10'],
        'Grade': ['N/A', 'N/A', 'N/A', 'N/A', 'A'],  # NEW: Added grade column
        'Diameter_Type': ['Blank Diameter', 'Pitch Diameter', 'Pitch Diameter', 'Blank Diameter', 'Blank Diameter'],
        'Blank_Diameter': [6.35, 0, 0, 9.525, 10.0],
        'Blank_Diameter_Unit': ['mm', 'mm', 'mm', 'mm', 'mm'],
        'Thread_Standard': ['N/A', 'ASME B1.1', 'ASME B1.1', 'N/A', 'N/A'],
        'Thread_Size': ['N/A', '1/4', '1/2', 'N/A', 'N/A'],
        'Thread_Class': ['N/A', '2A', '2A', 'N/A', 'N/A'],
        'Length': [50, 100, 200, 75, 60],
        'Length_Unit': ['mm', 'mm', 'ft', 'mm', 'mm'],
        'Material': ['Carbon Steel', 'Carbon Steel', 'Stainless Steel', 'Carbon Steel', 'Carbon Steel']
    }
    template_df = pd.DataFrame(template_data)
    csv_template = template_df.to_csv(index=False)
    st.download_button(
        label="Download Enhanced Batch Template (CSV)",
        data=csv_template,
        file_name="enhanced_batch_weight_template.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    uploaded_file = st.file_uploader("Upload CSV/Excel file for batch processing", 
                                   type=["csv", "xlsx"],
                                   key="batch_upload_enhanced")
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                batch_df = pd.read_excel(uploaded_file)
            else:
                batch_df = pd.read_csv(uploaded_file)
            
            st.success("File uploaded successfully!")
            st.write("Preview of uploaded data:")
            st.dataframe(batch_df.head())
            
            # Validate required columns
            required_cols = ['Product_Type', 'Series', 'Diameter_Type', 'Length']
            missing_cols = [col for col in required_cols if col not in batch_df.columns]
            
            if missing_cols:
                st.error(f"Missing required columns: {missing_cols}")
            else:
                if st.button("Process Batch Calculation", use_container_width=True, key="process_batch_enhanced"):
                    st.info("Batch processing with enhanced workflow ready for implementation")
                    st.write(f"Records to process: {len(batch_df)}")
                    
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# ======================================================
# ENHANCED CALCULATIONS PAGE - UPDATED WITH NEW WORKFLOW
# ======================================================
def show_enhanced_calculations():
    """Enhanced calculations page with complete product standards workflow"""
    
    tab1, tab2, tab3 = st.tabs(["Single Calculator", "Batch Processor", "Analytics"])
    
    with tab1:
        show_weight_calculator_enhanced()
    
    with tab2:
        show_batch_calculator_enhanced()
    
    with tab3:
        st.markdown("### Calculation Analytics - ENHANCED")
        st.info("Analytics dashboard will show calculation history and trends after weight calculations are implemented.")
        
        if 'calculation_history' in st.session_state and st.session_state.calculation_history:
            st.write("Calculation history will be displayed here")
        else:
            st.write("No calculation history yet. Perform calculations to see analytics here.")

# ======================================================
# ENHANCED DATA QUALITY INDICATORS
# ======================================================
def show_data_quality_indicators():
    """Show data quality and validation indicators"""
    st.sidebar.markdown("---")
    with st.sidebar.expander("Data Quality Status"):
        if not df.empty:
            total_rows = len(df)
            missing_data = df.isnull().sum().sum()
            completeness = ((total_rows * len(df.columns) - missing_data) / (total_rows * len(df.columns))) * 100
            st.markdown(f'<div class="data-quality-indicator quality-good">Main Data: {completeness:.1f}% Complete</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-error">Main Data: Not Loaded</div>', unsafe_allow_html=True)
        
        if not df_iso4014.empty:
            st.markdown(f'<div class="data-quality-indicator quality-good">ISO 4014: {len(df_iso4014)} Records</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">ISO 4014: Limited Access</div>', unsafe_allow_html=True)
        
        if st.session_state.din7991_loaded:
            st.markdown(f'<div class="data-quality-indicator quality-good">DIN-7991: {len(df_din7991)} Records</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">DIN-7991: Limited Access</div>', unsafe_allow_html=True)
        
        if st.session_state.asme_b18_3_loaded:
            st.markdown(f'<div class="data-quality-indicator quality-good">ASME B18.3: {len(df_asme_b18_3)} Records</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">ASME B18.3: Limited Access</div>', unsafe_allow_html=True)
        
        if not df_mechem.empty:
            st.markdown(f'<div class="data-quality-indicator quality-good">Mech & Chem: {len(df_mechem)} Records</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size: 0.8rem; margin: 0.1rem 0;">Property Classes: {len(st.session_state.property_classes)}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">Mech & Chem: Limited Access</div>', unsafe_allow_html=True)
        
        thread_status = []
        for standard, url in thread_files.items():
            df_thread = load_thread_data_enhanced(standard)
            if not df_thread.empty:
                thread_status.append(f"{standard}: OK")
            else:
                thread_status.append(f"{standard}: Limited")
        
        st.markdown(f'<div class="data-quality-indicator quality-good">Thread Data: Available</div>', unsafe_allow_html=True)
        for status in thread_status:
            st.markdown(f'<div style="font-size: 0.8rem; margin: 0.1rem 0;">{status}</div>', unsafe_allow_html=True)

# ======================================================
# Enhanced Export Functionality
# ======================================================
def export_to_excel(df, filename_prefix):
    """Export dataframe to Excel with formatting"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                workbook = writer.book
                worksheet = writer.sheets['Data']
                
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return tmp.name
    except Exception as e:
        st.error(f"Export error: {str(e)}")
        return None

def enhanced_export_data(filtered_df, export_format):
    """Enhanced export with multiple format options"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if export_format == "Excel":
        excel_file = export_to_excel(filtered_df, f"fastener_data_{timestamp}")
        if excel_file:
            with open(excel_file, 'rb') as f:
                st.download_button(
                    label="Download Excel File",
                    data=f,
                    file_name=f"fastener_data_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"excel_export_{timestamp}"
                )
    else:
        csv_data = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download CSV File",
            data=csv_data,
            file_name=f"fastener_data_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"csv_export_{timestamp}"
        )

# ======================================================
# Enhanced Calculation History
# ======================================================
def save_calculation_history(calculation_data):
    """Save calculation to history"""
    if 'calculation_history' not in st.session_state:
        st.session_state.calculation_history = []
    
    calculation_data['timestamp'] = datetime.now().isoformat()
    st.session_state.calculation_history.append(calculation_data)
    
    if len(st.session_state.calculation_history) > 20:
        st.session_state.calculation_history = st.session_state.calculation_history[-20:]

def show_calculation_history():
    """Display calculation history"""
    if 'calculation_history' in st.session_state and st.session_state.calculation_history:
        st.markdown("### Recent Calculations")
        for calc in reversed(st.session_state.calculation_history[-5:]):
            with st.container():
                st.markdown(f"""
                <div class="calculation-card">
                    <strong>{calc.get('product', 'N/A')}</strong> | 
                    Size: {calc.get('size', 'N/A')} | 
                    Grade: {calc.get('grade', 'N/A')} |
                    Weight: {calc.get('weight_kg', 'N/A')} kg
                    <br><small>{calc.get('timestamp', '')}</small>
                </div>
                """, unsafe_allow_html=True)

# ======================================================
# NEW: PROFESSIONAL PRODUCT CARD DISPLAY
# ======================================================
def show_professional_product_card(product_details):
    """Display a beautiful professional product specification card"""
    
    # Extract product details
    product_name = product_details.get('Product', 'Hex Bolt')
    size = product_details.get('Size', '1/4 x 10')
    standard = product_details.get('Standards', 'ASME B18.2.1')
    thread = product_details.get('Thread', '1/4-20-UNC-2A')
    grade = product_details.get('Product Grade', 'N/A')  # NEW: Added grade
    
    # Get current date and user info
    current_date = datetime.now().strftime('%d/%m/%Y')
    generated_by = "Partha Sharma"  # This could be dynamic based on user login
    
    # Create the professional card HTML
    card_html = f"""
    <div class="professional-card">
        <div class="card-header">
            <div>
                <h1 class="card-title">{product_name}</h1>
                <p class="card-subtitle">Size: {size} | Standard: {standard} | Grade: {grade}</p>
            </div>
            <div class="card-company">JSC India</div>
        </div>
        
        <div class="specification-grid">
            <!-- Dimensional Specifications Group -->
            <div class="spec-group">
                <div class="spec-group-title">Dimensional Specifications</div>
                
                <!-- Body Diameter -->
                <div class="spec-row">
                    <div class="spec-label-min">Body Dia (Min)</div>
                    <div class="spec-dimension">Body Diameter</div>
                    <div class="spec-label-max">Body Dia (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Body_Dia_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Body_Dia_Max', 'N/A')}</div>
                </div>
                
                <!-- Width Across Flats -->
                <div class="spec-row">
                    <div class="spec-label-min">Width Across Flats (Min)</div>
                    <div class="spec-dimension">Width Across Flats</div>
                    <div class="spec-label-max">Width Across Flats (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Width_Across_Flats_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Width_Across_Flats_Max', 'N/A')}</div>
                </div>
                
                <!-- Width Across Corners -->
                <div class="spec-row">
                    <div class="spec-label-min">Width Across Corners (Min)</div>
                    <div class="spec-dimension">Width Across Corners</div>
                    <div class="spec-label-max">Width Across Corners (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Width_Across_Corners_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Width_Across_Corners_Max', 'N/A')}</div>
                </div>
                
                <!-- Head Height -->
                <div class="spec-row">
                    <div class="spec-label-min">Head Height (Min)</div>
                    <div class="spec-dimension">Head Height</div>
                    <div class="spec-label-max">Head Height (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Head_Height_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Head_Height_Max', 'N/A')}</div>
                </div>
                
                <!-- Radius of Fillet -->
                <div class="spec-row">
                    <div class="spec-label-min">Radius of Fillet (Min)</div>
                    <div class="spec-dimension">Radius of Fillet</div>
                    <div class="spec-label-max">Radius of Fillet (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Radius_Fillet_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Radius_Fillet_Max', 'N/A')}</div>
                </div>
                
                <!-- Washer Face Thickness -->
                <div class="spec-row">
                    <div class="spec-label-min">Washer Face Thickness (Min)</div>
                    <div class="spec-dimension">Washer Face Thickness</div>
                    <div class="spec-label-max">Washer Face Thickness (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Washer_Face_Thickness_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Washer_Face_Thickness_Max', 'N/A')}</div>
                </div>
                
                <!-- Wrenching Height -->
                <div class="spec-row">
                    <div class="spec-label-min">Wrenching Height (Min)</div>
                    <div class="spec-dimension">Wrenching Height</div>
                    <div class="spec-label-max">Total Runout (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Wrenching_Height_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Total_Runout_Max', 'N/A')}</div>
                </div>
            </div>
            
            <!-- Head Specifications Group -->
            <div class="spec-group">
                <div class="spec-group-title">Head Specifications</div>
                
                <!-- Head Height -->
                <div class="spec-row">
                    <div class="spec-label-min">Head Height (Min)</div>
                    <div class="spec-dimension">Head Height</div>
                    <div class="spec-label-max">Head Height (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Head_Height_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Head_Height_Max', 'N/A')}</div>
                </div>
                
                <!-- Radius of Fillet -->
                <div class="spec-row">
                    <div class="spec-label-min">Radius of Fillet (Min)</div>
                    <div class="spec-dimension">Radius of Fillet</div>
                    <div class="spec-label-max">Radius of Fillet (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Radius_Fillet_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Radius_Fillet_Max', 'N/A')}</div>
                </div>
                
                <!-- Washer Face Thickness -->
                <div class="spec-row">
                    <div class="spec-label-min">Washer Face Thickness (Min)</div>
                    <div class="spec-dimension">Washer Face Thickness</div>
                    <div class="spec-label-max">Washer Face Thickness (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Washer_Face_Thickness_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Washer_Face_Thickness_Max', 'N/A')}</div>
                </div>
            </div>
            
            <!-- Additional Specifications Group -->
            <div class="spec-group">
                <div class="spec-group-title">Additional Specifications</div>
                
                <!-- Wrenching Height -->
                <div class="spec-row">
                    <div class="spec-label-min">Wrenching Height (Min)</div>
                    <div class="spec-dimension">Wrenching Height</div>
                    <div class="spec-label-max">Total Runout (Max)</div>
                </div>
                <div class="spec-row">
                    <div class="spec-value">{product_details.get('Wrenching_Height_Min', 'N/A')}</div>
                    <div class="spec-dimension"></div>
                    <div class="spec-value">{product_details.get('Total_Runout_Max', 'N/A')}</div>
                </div>
                
                <!-- Thread Information -->
                <div class="spec-row">
                    <div class="spec-dimension" style="grid-column: 1 / span 3; text-align: center; background: var(--engineering-blue); color: white; padding: 0.8rem;">
                        <strong>Thread: {thread}</strong>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card-footer">
            <div>
                <strong>Generation Date:</strong> {current_date}<br>
                <strong>Generated By:</strong> {generated_by}
            </div>
            <div class="card-badge">
                Professional Specification
            </div>
        </div>
        
        <div class="card-actions">
            <button class="action-button" onclick="window.print()">Print Specification</button>
            <button class="action-button secondary">Email Specification</button>
            <button class="action-button secondary">Save as PDF</button>
        </div>
    </div>
    """
    
    # Display the card
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Add some action buttons below the card
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("View Raw Data", use_container_width=True):
            st.dataframe(pd.DataFrame([product_details]))
    with col2:
        if st.button("Compare Products", use_container_width=True):
            st.info("Product comparison feature coming soon!")
    with col3:
        if st.button("Close Card", use_container_width=True):
            st.session_state.show_professional_card = False
            st.rerun()

def extract_product_details(row):
    """Extract product details from dataframe row and map to card format"""
    details = {
        'Product': row.get('Product', 'Hex Bolt'),
        'Size': row.get('Size', 'N/A'),
        'Standards': row.get('Standards', 'ASME B18.2.1'),
        'Thread': row.get('Thread', '1/4-20-UNC-2A'),
        'Product Grade': row.get('Product Grade', 'N/A'),  # NEW: Added grade
        
        # Map dimensional specifications - these would come from your actual data columns
        'Body_Dia_Min': row.get('Body_Diameter_Min', row.get('Basic_Major_Diameter_Min', 'N/A')),
        'Body_Dia_Max': row.get('Body_Diameter_Max', row.get('Basic_Major_Diameter_Max', 'N/A')),
        
        'Width_Across_Flats_Min': row.get('Width_Across_Flats_Min', row.get('W_Across_Flats_Min', 'N/A')),
        'Width_Across_Flats_Max': row.get('Width_Across_Flats_Max', row.get('W_Across_Flats_Max', 'N/A')),
        
        'Width_Across_Corners_Min': row.get('Width_Across_Corners_Min', row.get('W_Across_Corners_Min', 'N/A')),
        'Width_Across_Corners_Max': row.get('Width_Across_Corners_Max', row.get('W_Across_Corners_Max', 'N/A')),
        
        'Head_Height_Min': row.get('Head_Height_Min', 'N/A'),
        'Head_Height_Max': row.get('Head_Height_Max', 'N/A'),
        
        'Radius_Fillet_Min': row.get('Radius_Fillet_Min', row.get('Fillet_Radius_Min', 'N/A')),
        'Radius_Fillet_Max': row.get('Radius_Fillet_Max', row.get('Fillet_Radius_Max', 'N/A')),
        
        'Washer_Face_Thickness_Min': row.get('Washer_Face_Thickness_Min', 'N/A'),
        'Washer_Face_Thickness_Max': row.get('Washer_Face_Thickness_Max', 'N/A'),
        
        'Wrenching_Height_Min': row.get('Wrenching_Height_Min', 'N/A'),
        'Total_Runout_Max': row.get('Total_Runout_Max', 'N/A')
    }
    
    return details

# ======================================================
# FIXED SECTION A - PROPER PRODUCT-SERIES-STANDARD-SIZE-GRADE RELATIONSHIP
# ======================================================

def get_available_standards_for_product_series(product, series):
    """Get available standards based on selected product and series"""
    available_standards = ["All"]
    
    if product == "All" and series == "All":
        # Show all standards
        for standard in st.session_state.available_products.keys():
            available_standards.append(standard)
    elif product == "All" and series != "All":
        # Filter by series only
        for standard, std_series in st.session_state.available_series.items():
            if std_series == series:
                available_standards.append(standard)
    elif product != "All" and series == "All":
        # Filter by product only
        for standard, products in st.session_state.available_products.items():
            if product in products:
                available_standards.append(standard)
    else:
        # Filter by both product and series
        for standard, products in st.session_state.available_products.items():
            if product in products:
                std_series = st.session_state.available_series.get(standard, "")
                if std_series == series:
                    available_standards.append(standard)
    
    return available_standards

def get_available_sizes_for_standard_product(standard, product, grade="All"):
    """Get available sizes based on selected standard and product"""
    size_options = ["All"]
    
    if standard == "All" or product == "All":
        return size_options
    
    temp_df = get_filtered_dataframe(product, standard, grade)
    size_options = get_safe_size_options(temp_df)
    
    return size_options

# ======================================================
# FIXED SECTION B - THREAD SPECIFICATIONS WITH PROPER DATA HANDLING
# ======================================================
def show_enhanced_product_database():
    """Enhanced Product Intelligence Center with COMPLETELY FIXED Section C material properties"""
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
            Product Intelligence Center - Independent Sections
        </h1>
        <p style="margin:0; opacity: 0.9;">Each section works completely independently - No dependencies</p>
        <div style="margin-top: 1rem;">
            <span class="engineering-badge">Enhanced Calculator</span>
            <span class="material-badge">Product-Based Workflow</span>
            <span class="grade-badge">Dynamic Standards</span>
            <span class="technical-badge">Professional Grade</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if df.empty and df_mechem.empty and df_iso4014.empty and not st.session_state.din7991_loaded and not st.session_state.asme_b18_3_loaded:
        st.error("No data sources available. Please check your data connections.")
        return
    
    # Section toggles
    st.markdown("### Section Controls")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        section_a_active = st.checkbox("Section A - Dimensional Specifications", value=st.session_state.section_a_view, key="section_a_toggle")
        st.session_state.section_a_view = section_a_active
    
    with col2:
        section_b_active = st.checkbox("Section B - Thread Specifications", value=st.session_state.section_b_view, key="section_b_toggle")
        st.session_state.section_b_view = section_b_active
    
    with col3:
        section_c_active = st.checkbox("Section C - Material Properties", value=st.session_state.section_c_view, key="section_c_toggle")
        st.session_state.section_c_view = section_c_active
    
    st.markdown("---")
    
    # SECTION A - DIMENSIONAL SPECIFICATIONS (FIXED RELATIONSHIPS)
    if st.session_state.section_a_view:
        st.markdown("""
        <div class="independent-section">
            <h3 class="filter-header">Section A - Dimensional Specifications</h3>
            <p><strong>Relationship:</strong> Product -> Series -> Standards -> Size -> Grade (ISO 4014 only)</p>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)  # NEW: Added 5th column for grade
        
        with col1:
            # 1. Product List - Get all unique products from all standards
            all_products = set()
            for standard_products_list in st.session_state.available_products.values():
                all_products.update(standard_products_list)
            all_products = ["All"] + sorted([p for p in all_products if p != "All"])
            
            dimensional_product = st.selectbox(
                "Product List", 
                all_products, 
                key="section_a_product",
                index=all_products.index(st.session_state.section_a_current_product) if st.session_state.section_a_current_product in all_products else 0
            )
            st.session_state.section_a_current_product = dimensional_product
        
        with col2:
            # 2. Series System - Always show both options
            series_options = ["All", "Inch", "Metric"]
            dimensional_series = st.selectbox(
                "Series System", 
                series_options, 
                key="section_a_series",
                index=series_options.index(st.session_state.section_a_current_series) if st.session_state.section_a_current_series in series_options else 0
            )
            st.session_state.section_a_current_series = dimensional_series
        
        with col3:
            # 3. Standards - Filtered based on Product and Series
            available_standards = get_available_standards_for_product_series(dimensional_product, dimensional_series)
            
            dimensional_standard = st.selectbox(
                "Standards", 
                available_standards, 
                key="section_a_standard",
                index=available_standards.index(st.session_state.section_a_current_standard) if st.session_state.section_a_current_standard in available_standards else 0
            )
            st.session_state.section_a_current_standard = dimensional_standard
            
            # Show info about available standards
            if dimensional_standard != "All":
                std_series = st.session_state.available_series.get(dimensional_standard, "Unknown")
                st.caption(f"Series: {std_series}")
        
        with col4:
            # 4. Size - Filtered based on Standard and Product
            available_sizes = get_available_sizes_for_standard_product(dimensional_standard, dimensional_product)
            
            dimensional_size = st.selectbox(
                "Size", 
                available_sizes, 
                key="section_a_size",
                index=available_sizes.index(st.session_state.section_a_current_size) if st.session_state.section_a_current_size in available_sizes else 0
            )
            st.session_state.section_a_current_size = dimensional_size
            
            # Show info about available sizes
            if dimensional_size != "All":
                st.caption(f"Sizes available: {len(available_sizes)-1}")
        
        with col5:
            # NEW: 5. Grade - Only for ISO 4014 Hex Bolt
            if dimensional_standard == "ISO 4014" and dimensional_product == "Hex Bolt":
                grade_options = get_available_grades_for_standard_product(dimensional_standard, dimensional_product)
                dimensional_grade = st.selectbox(
                    "Product Grade", 
                    grade_options, 
                    key="section_a_grade",
                    index=grade_options.index(st.session_state.section_a_current_grade) if st.session_state.section_a_current_grade in grade_options else 0
                )
                st.session_state.section_a_current_grade = dimensional_grade
                
                # Show info about available grades
                if dimensional_grade != "All":
                    st.caption(f"Grade: {dimensional_grade}")
                    st.caption("⚠️ Different dimensions for A/B")
            else:
                st.info("Grade not applicable")
                dimensional_grade = "Not Applicable"
                st.session_state.section_a_current_grade = "All"
        
        # Debug information
        if st.session_state.debug_mode:
            st.info(f"""
            **Debug Info - Section A:**
            - Product: {dimensional_product}
            - Series: {dimensional_series} 
            - Standards Available: {len(available_standards)-1}
            - Sizes Available: {len(available_sizes)-1}
            - Grade: {dimensional_grade}
            - Selected Standard: {dimensional_standard}
            - Selected Size: {dimensional_size}
            """)
        
        # Apply Section A Filters Button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("APPLY SECTION A FILTERS", use_container_width=True, type="primary", key="apply_section_a"):
                st.session_state.section_a_filters = {
                    'product': dimensional_product,
                    'series': dimensional_series,
                    'standard': dimensional_standard,
                    'size': dimensional_size,
                    'grade': dimensional_grade if dimensional_standard == "ISO 4014" and dimensional_product == "Hex Bolt" else "All"
                }
                # Apply filters and store results
                st.session_state.section_a_results = apply_section_a_filters()
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show Section A Results
        show_section_a_results()
    
    # SECTION B - THREAD SPECIFICATIONS (FIXED DATA TYPES)
    if st.session_state.section_b_view:
        st.markdown("""
        <div class="independent-section">
            <h3 class="filter-header">Section B - Thread Specifications</h3>
            <p><strong>FIXED:</strong> Proper data loading from Excel files with correct tolerance classes</p>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Thread standards
            thread_standards = ["All", "ASME B1.1", "ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
            thread_standard = st.selectbox(
                "Thread Standard", 
                thread_standards, 
                key="section_b_standard",
                index=thread_standards.index(st.session_state.section_b_current_standard) if st.session_state.section_b_current_standard in thread_standards else 0
            )
            st.session_state.section_b_current_standard = thread_standard
            
            # Show thread data info
            if thread_standard != "All":
                df_thread = load_thread_data_enhanced(thread_standard)
                if not df_thread.empty:
                    st.caption(f"Threads available: {len(df_thread)}")
                    if st.session_state.debug_mode:
                        st.caption(f"Columns: {df_thread.columns.tolist()}")
        
        with col2:
            # Thread sizes - FIXED: Get from actual Excel data
            thread_size_options = get_thread_sizes_enhanced(thread_standard)
            
            thread_size = st.selectbox(
                "Thread Size", 
                thread_size_options, 
                key="section_b_size",
                index=thread_size_options.index(st.session_state.section_b_current_size) if st.session_state.section_b_current_size in thread_size_options else 0
            )
            st.session_state.section_b_current_size = thread_size
            
            if thread_size != "All":
                st.caption(f"Sizes available: {len(thread_size_options)-1}")
        
        with col3:
            # Tolerance classes - FIXED: Get ACTUAL classes from Excel data
            if thread_standard == "ASME B1.1":
                # Get actual tolerance classes from Excel data
                tolerance_options = get_thread_classes_enhanced(thread_standard)
                
                # If no specific classes found, use default
                if len(tolerance_options) == 1:  # Only "All"
                    tolerance_options = ["All", "1A", "2A", "3A"]
                elif len(tolerance_options) > 1 and "All" in tolerance_options:
                    # If "All" is present, prioritize it
                    tolerance_options = ["All"] + [cls for cls in tolerance_options if cls != "All"]
                
                tolerance_class = st.selectbox(
                    "Tolerance Class", 
                    tolerance_options, 
                    key="section_b_class",
                    index=tolerance_options.index(st.session_state.section_b_current_class) if st.session_state.section_b_current_class in tolerance_options else 0
                )
                st.session_state.section_b_current_class = tolerance_class
                
                if tolerance_class != "All":
                    st.caption(f"Classes available: {len(tolerance_options)-1}")
            else:
                # For metric threads, show available classes from data
                tolerance_options = get_thread_classes_enhanced(thread_standard)
                tolerance_class = st.selectbox(
                    "Tolerance Class", 
                    tolerance_options, 
                    key="section_b_class",
                    index=tolerance_options.index(st.session_state.section_b_current_class) if st.session_state.section_b_current_class in tolerance_options else 0
                )
                st.session_state.section_b_current_class = tolerance_class
                
                if tolerance_class != "All":
                    st.caption(f"Classes available: {len(tolerance_options)-1}")
        
        # Debug information for Section B
        if st.session_state.debug_mode and thread_standard != "All":
            df_thread_sample = load_thread_data_enhanced(thread_standard)
            if not df_thread_sample.empty:
                st.info(f"""
                **Debug Info - Section B ({thread_standard}):**
                - Total Records: {len(df_thread_sample)}
                - Columns: {df_thread_sample.columns.tolist()}
                - Unique Sizes: {len(get_thread_sizes_enhanced(thread_standard))-1}
                - Unique Classes: {len(get_thread_classes_enhanced(thread_standard))-1}
                - Sample Data: {df_thread_sample[['Thread', 'Class']].head(3).to_dict() if 'Thread' in df_thread_sample.columns and 'Class' in df_thread_sample.columns else 'No Thread/Class columns'}
                """)
        
        # Apply Section B Filters Button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("APPLY SECTION B FILTERS", use_container_width=True, type="primary", key="apply_section_b"):
                st.session_state.section_b_filters = {
                    'standard': thread_standard,
                    'size': thread_size,
                    'class': tolerance_class
                }
                # Apply filters and store results
                st.session_state.section_b_results = apply_section_b_filters()
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show Section B Results
        show_section_b_results()
    
    # SECTION C - MATERIAL PROPERTIES (COMPLETELY INDEPENDENT) - COMPLETELY FIXED VERSION
    if st.session_state.section_c_view:
        st.markdown("""
        <div class="independent-section">
            <h3 class="filter-header">Section C - Material Properties</h3>
            <p><strong>COMPLETELY FIXED:</strong> Works with ALL property classes including 10.9, 6.8, 8.8, 304, A, B, B7</p>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Property classes - FIXED: Get ALL property classes from Mechanical & Chemical data
            property_classes = ["All"]
            if st.session_state.property_classes:
                property_classes.extend(sorted(st.session_state.property_classes))
            else:
                # If no property classes found, show a message
                st.info("No property classes found in Mechanical & Chemical data")
                property_classes = ["All", "No data available"]
            
            property_class = st.selectbox(
                "Property Class (Grade)", 
                property_classes, 
                key="section_c_class",
                index=property_classes.index(st.session_state.section_c_current_class) if st.session_state.section_c_current_class in property_classes else 0
            )
            st.session_state.section_c_current_class = property_class
            
            # Show info about selected property class
            if property_class != "All" and property_class != "No data available":
                st.caption(f"Selected: {property_class}")
                # Show available standards for this property class
                available_standards = get_standards_for_property_class(property_class)
                if available_standards:
                    st.caption(f"Available standards: {len(available_standards)}")
        
        with col2:
            # Material standards - FIXED: Get standards based on selected property class
            material_standards = ["All"]
            if property_class != "All" and property_class != "No data available":
                mechem_standards = get_standards_for_property_class(property_class)
                if mechem_standards:
                    material_standards.extend(sorted(mechem_standards))
                else:
                    st.caption("No specific standards found for this property class")
                    # Add some common standards as fallback
                    material_standards.extend(["ASTM A193", "ASTM A320", "ISO 898-1", "ASME B18.2.1"])
            
            material_standard = st.selectbox(
                "Material Standard", 
                material_standards, 
                key="section_c_standard",
                index=material_standards.index(st.session_state.section_c_current_standard) if st.session_state.section_c_current_standard in material_standards else 0
            )
            st.session_state.section_c_current_standard = material_standard
            
            # Show info about available standards
            if material_standard != "All":
                st.caption(f"Standard: {material_standard}")
        
        # Debug information for Section C
        if st.session_state.debug_mode:
            st.info(f"""
            **Debug Info - Section C:**
            - Property Classes Available: {len(property_classes)-1}
            - Selected Property Class: {property_class}
            - Standards Available: {len(material_standards)-1}
            - Selected Standard: {material_standard}
            - Mechanical & Chemical Data: {len(df_mechem)} records
            - Sample Property Classes: {st.session_state.property_classes[:5] if st.session_state.property_classes else 'None'}
            """)
        
        # Apply Section C Filters Button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("APPLY SECTION C FILTERS", use_container_width=True, type="primary", key="apply_section_c"):
                if property_class == "All" or property_class == "No data available":
                    st.warning("Please select a valid property class")
                else:
                    st.session_state.section_c_filters = {
                        'property_class': property_class,
                        'standard': material_standard
                    }
                    # Apply filters and store results
                    st.session_state.section_c_results = apply_section_c_filters()
                    
                    # Show immediate feedback
                    if st.session_state.section_c_results.empty:
                        st.warning(f"No data found for Property Class: {property_class} and Standard: {material_standard}")
                    else:
                        st.success(f"Found {len(st.session_state.section_c_results)} records for {property_class}")
                    
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show Section C Results
        show_section_c_results()
    
    # COMBINE ALL RESULTS SECTION
    st.markdown("---")
    st.markdown("### Combine All Sections")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("COMBINE ALL SECTION RESULTS", use_container_width=True, type="secondary", key="combine_all"):
            st.session_state.combined_results = combine_all_results()
            st.rerun()
    
    # Show Combined Results
    show_combined_results()
    
    # Quick actions
    st.markdown("---")
    st.markdown("### Quick Actions")
    
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    
    with quick_col1:
        if st.button("Clear All Filters", use_container_width=True, key="clear_all"):
            st.session_state.section_a_filters = {}
            st.session_state.section_b_filters = {}
            st.session_state.section_c_filters = {}
            st.session_state.section_a_results = pd.DataFrame()
            st.session_state.section_b_results = pd.DataFrame()
            st.session_state.section_c_results = pd.DataFrame()
            st.session_state.combined_results = pd.DataFrame()
            st.session_state.show_professional_card = False
            # Reset current selections
            st.session_state.section_a_current_product = "All"
            st.session_state.section_a_current_series = "All"
            st.session_state.section_a_current_standard = "All"
            st.session_state.section_a_current_size = "All"
            st.session_state.section_a_current_grade = "All"  # NEW: Reset grade
            st.session_state.section_b_current_standard = "All"
            st.session_state.section_b_current_size = "All"
            st.session_state.section_b_current_class = "All"
            st.session_state.section_c_current_class = "All"
            st.session_state.section_c_current_standard = "All"
            st.rerun()
    
    with quick_col2:
        if st.button("View All Data", use_container_width=True, key="view_all"):
            # Show all available data
            st.session_state.section_a_results = df.copy()
            # Load thread data for ASME B1.1
            st.session_state.section_b_results = get_thread_data_enhanced("ASME B1.1")
            if not df_mechem.empty:
                st.session_state.section_c_results = df_mechem.copy()
            st.rerun()
    
    with quick_col3:
        if st.button("Export Everything", use_container_width=True, key="export_all"):
            # Combine current results and export
            combined = combine_all_results()
            if not combined.empty:
                enhanced_export_data(combined, "Excel")
            else:
                st.warning("No data to export")
    
    with quick_col4:
        if st.button("Reset Sections", use_container_width=True, key="reset_sections"):
            st.session_state.section_a_view = True
            st.session_state.section_b_view = True
            st.session_state.section_c_view = True
            st.rerun()

# ======================================================
# ENHANCED HOME DASHBOARD
# ======================================================
def show_enhanced_home():
    """Show professional engineering dashboard"""
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; font-size: 2.5rem;">JSC Industries</h1>
        <p style="margin:0; font-size: 1.2rem; opacity: 0.9;">Professional Fastener Intelligence Platform v4.0 - ENHANCED</p>
        <div style="margin-top: 1rem;">
            <span class="engineering-badge">Enhanced Calculator</span>
            <span class="material-badge">Product-Based Workflow</span>
            <span class="grade-badge">Dynamic Standards</span>
            <span class="technical-badge">Professional Grade</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = len(df) + (len(df_iso4014) if not df_iso4014.empty else 0) + (len(df_din7991) if st.session_state.din7991_loaded else 0) + (len(df_asme_b18_3) if st.session_state.asme_b18_3_loaded else 0)
    total_dimensional_standards = st.session_state.dimensional_standards_count
    total_threads = len(thread_files)
    total_mecert = len(df_mechem) if not df_mechem.empty else 0
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">Products</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_products}</h2>
            <p style="color: #7f8c8d; margin:0;">Total Records</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">Dimensional Standards</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_dimensional_standards}</h2>
            <p style="color: #7f8c8d; margin:0;">ASME B18.2.1, ASME B18.3, ISO 4014, DIN-7991</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">Thread Types</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_threads}</h2>
            <p style="color: #7f8c8d; margin:0;">Available</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">ME&CERT</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_mecert}</h2>
            <p style="color: #7f8c8d; margin:0;">Properties</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<h2 class="section-header">Engineering Tools - ENHANCED</h2>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    actions = [
        ("Product Database", "Professional product discovery with engineering filters", "database"),
        ("Engineering Calculator", "ENHANCED weight calculations with improved workflow", "calculator"),
        ("Analytics Dashboard", "Visual insights and performance metrics", "analytics"),
        ("Compare Products", "Side-by-side technical comparison", "compare"),
        ("Export Reports", "Generate professional engineering reports", "export")
    ]
    
    for idx, (title, description, key) in enumerate(actions):
        with cols[idx % 3]:
            if st.button(f"**{title}**\n\n{description}", key=f"home_{key}"):
                section_map = {
                    "database": "Product Database",
                    "calculator": "Calculations"
                }
                st.session_state.selected_section = section_map.get(key, "Product Database")
                st.rerun()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="section-header">System Status - ENHANCED</h3>', unsafe_allow_html=True)
        
        status_items = [
            ("ASME B18.2.1 Data", not df.empty, "engineering-badge"),
            ("ISO 4014 Data", not df_iso4014.empty, "technical-badge"),
            ("DIN-7991 Data", st.session_state.din7991_loaded, "material-badge"),
            ("ASME B18.3 Data", st.session_state.asme_b18_3_loaded, "grade-badge"),
            ("ME&CERT Data", not df_mechem.empty, "engineering-badge"),
            ("Thread Data", any(not load_thread_data_enhanced(url).empty for url in thread_files.values()), "technical-badge"),
            ("Weight Calculations", True, "engineering-badge"),
            ("Enhanced Calculator", True, "technical-badge"),
        ]
        
        for item_name, status, badge_class in status_items:
            if status:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0;">{item_name} - Active</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0; background: #6c757d;">{item_name} - Limited</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<h3 class="section-header">ENHANCED Features</h3>', unsafe_allow_html=True)
        
        features = [
            "Product-based calculator workflow",
            "Dynamic dimensional standards", 
            "Automatic size selection",
            "Flexible diameter input options",
            "Threaded rod and stud support",
            "Database-connected calculations",
            "Enhanced user interface",
            "Professional reporting",
            "Carbon steel density calculations",
            "Batch processing capabilities",
            "Automatic inch-to-mm conversion",
            "RECTIFIED hex product formulas with specific volume calculations",
            "NEW: ISO 4014 Product Grade selection (A/B)"
        ]
        
        for feature in features:
            st.markdown(f'<div style="padding: 0.5rem; border-left: 3px solid #3498db; margin: 0.2rem 0; background: var(--neutral-light);">• {feature}</div>', unsafe_allow_html=True)
    
    show_calculation_history()

# ======================================================
# HELP SYSTEM
# ======================================================
def show_help_system():
    """Show contextual help system"""
    with st.sidebar:
        st.markdown("---")
        with st.expander("ENHANCED Weight Calculator Guide"):
            st.markdown("""
            **ENHANCED WEIGHT CALCULATOR WORKFLOW:**
            
            **Complete Input Sequence:**
            1. **A. Product Type** - Select from standards database
            2. **B. Series** (Inch/Metric) - Filtered by product type
            3. **C. Standard** - Filtered by product + series (for dimensional data)
            4. **D. Size** - Filtered by standard + product
            5. **E. Product Grade** - Only for ISO 4014 Hex Bolt (A/B grades)
            6. **F. Cylinder Diameter Type** - Blank Diameter (Body) or Pitch Diameter (Thread)
            7. **G. Conditional Input:**
               - **Blank Diameter**: Manual value input
               - **Pitch Diameter**: Thread specification dropdown
            
            **RECTIFIED HEX PRODUCT FORMULA:**
            - **Hex Bolt, Heavy Hex Bolt, Hex Cap Screws, Heavy Hex Screws** use RECTIFIED calculation
            - **Shank Volume**: π × (diameter/2)² × length
            - **RECTIFIED: Side Length** = Width Across Flats × 1.1547
            - **Head Volume**: 0.65 × side_length² × head_height
            - **Total Volume** = Shank Volume + Head Volume
            - **Weight** = Total Volume × Density
            
            **NEW ISO 4014 GRADE SELECTION:**
            - ISO 4014 Hex Bolt has two product grades: A and B
            - Each grade has different dimensional specifications
            - Grade selection affects weight calculations for ISO 4014 Hex Bolt
            
            **NEW THREADED ROD SUPPORT:**
            - Threaded Rod added to all product lists
            - Uses pitch diameter from thread standards data
            - Automatic pitch diameter lookup from thread database
            - Support for both inch and metric threaded rods
            
            **UNIT CONVERSION FEATURE:**
            - **Inch Series**: All dimensions automatically converted from inches to mm
            - **ASME B1.1**: Pitch diameter data in inches converted to mm
            - **Weight calculations**: Always performed in metric units (kg/m³)
            - **Display**: Shows both original and converted values
            
            **Purpose:**
            - Get accurate dimensional data from standards for weight calculations
            - Handle both body diameter and thread pitch diameter scenarios
            - Maintain smooth filtering like Product Database section
            - Automatic unit conversion for accurate calculations
            - RECTIFIED formulas for hex products with specific volume calculation
            - NEW: ISO 4014 grade-specific dimension handling
            """)

# ======================================================
# SECTION DISPATCHER
# ======================================================
def show_section(title):
    if title == "Product Database":
        show_enhanced_product_database()
    elif title == "Calculations":
        show_enhanced_calculations()
    else:
        st.info(f"Section {title} is coming soon!")
    
    st.markdown("---")
    if st.button("Back to Dashboard", use_container_width=True):
        st.session_state.selected_section = None
        st.rerun()

# ======================================================
# MAIN APPLICATION
# ======================================================
def main():
    """Main application entry point"""
    
    show_help_system()
    
    show_data_quality_indicators()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## Navigation")
        
        sections = [
            "Home Dashboard",
            "Product Database", 
            "Calculations"
        ]
        
        for section in sections:
            if st.button(section, use_container_width=True, key=f"nav_{section}"):
                if section == "Home Dashboard":
                    st.session_state.selected_section = None
                else:
                    st.session_state.selected_section = section
                st.rerun()
        
        # Debug mode toggle
        st.markdown("---")
        st.session_state.debug_mode = st.checkbox("Debug Mode", value=st.session_state.debug_mode)
    
    if st.session_state.selected_section is None:
        show_enhanced_home()
    else:
        show_section(st.session_state.selected_section)
    
    st.markdown("""
        <hr>
        <div style='text-align: center; color: gray; padding: 2rem;'>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
                <span class="engineering-badge">ENHANCED Calculator</span>
                <span class="technical-badge">Improved Workflow</span>
                <span class="material-badge">Dynamic Standards</span>
                <span class="grade-badge">Professional Grade</span>
            </div>
            <p><strong>© 2024 JSC Industries Pvt Ltd</strong> | Born to Perform • Engineered for Excellence</p>
            <p style="font-size: 0.8rem;">Professional Fastener Intelligence Platform v4.0 - ENHANCED Weight Calculator with Automatic Unit Conversion, RECTIFIED Hex Product Formulas, and ISO 4014 Grade Selection</p>
        </div>
    """, unsafe_allow_html=True)

# Run the application
if __name__ == "__main__":
    main()