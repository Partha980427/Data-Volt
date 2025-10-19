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
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from transformers import pipeline
import spacy
import torch
import warnings
import math
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
                'ai_assistant': True,
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
        "ai_history": [],
        "current_filters": {},
        "recent_searches": [],
        "favorite_products": [],
        "calculation_history": [],
        "export_format": "csv",
        "chat_messages": [],
        "ai_thinking": False,
        "ai_model_loaded": False,
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
        "section_b_current_standard": "All",
        "section_b_current_size": "All",
        "section_b_current_class": "All",
        "section_c_current_class": "All",
        "section_c_current_standard": "All",
        "thread_data_cache": {},
        "show_professional_card": False,
        "selected_product_details": None,
        "batch_calculation_results": pd.DataFrame(),
        # Weight calculator session states - UPDATED FOR NEW WORKFLOW
        "weight_calc_product": "Hex Bolt",
        "weight_calc_series": "Inch",
        "weight_calc_standard": "ASME B18.2.1",
        "weight_calc_diameter_type": "Blank Diameter",
        "weight_calc_blank_diameter": 10.0,
        "weight_calc_blank_dia_unit": "mm",
        "weight_calc_thread_standard": "ASME B1.1",
        "weight_calc_thread_size": "All",
        "weight_calc_thread_class": "2A",
        "weight_calc_length": 50.0,
        "weight_calc_length_unit": "mm",
        "weight_calc_material": "Carbon Steel",
        "weight_calc_result": None
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
            result_df["Class"].astype(str).str.strip().str.upper() == 
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

    .chat-container {
        background: #f0f2f5;
        border-radius: 15px;
        padding: 1rem;
        height: 600px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
    }
    .message {
        margin: 0.5rem 0;
        padding: 0.8rem 1rem;
        border-radius: 18px;
        max-width: 70%;
        word-wrap: break-word;
    }
    .user-message {
        background: #0084ff;
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 5px;
    }
    .ai-message {
        background: white;
        color: #1c1e21;
        margin-right: auto;
        border-bottom-left-radius: 5px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .message-time {
        font-size: 0.7rem;
        opacity: 0.7;
        margin-top: 0.2rem;
    }
    .typing-indicator {
        display: inline-flex;
        align-items: center;
        background: white;
        padding: 0.8rem 1rem;
        border-radius: 18px;
        border-bottom-left-radius: 5px;
        margin-right: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .typing-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #999;
        margin: 0 2px;
        animation: typing 1.4s infinite;
    }
    .typing-dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    .typing-dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    @keyframes typing {
        0%, 60%, 100% { transform: translateY(0); }
        30% { transform: translateY(-5px); }
    }
    .quick-question {
        background: #f0f2f5;
        border: 1px solid #dddfe2;
        border-radius: 18px;
        padding: 0.5rem 1rem;
        margin: 0.2rem;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.9rem;
    }
    .quick-question:hover {
        background: #e4e6eb;
    }
    .chat-input-container {
        background: white;
        border-radius: 20px;
        padding: 0.5rem;
        margin-top: 1rem;
        border: 1px solid #dddfe2;
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
        .message {
            max-width: 85%;
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

def get_thread_standards_for_series(series):
    """Get thread standards based on series"""
    if series == "Inch":
        return ["ASME B1.1"]
    elif series == "Metric":
        return ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
    return ["Select Thread Standard"]

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
    **Enhanced Workflow:** Product Type → Series → Standard → Diameter Type → (Manual Input or Thread Specs)
    """)
    
    # Main input form with enhanced workflow
    with st.form("weight_calculator_enhanced"):
        st.markdown("### Product Standards Selection")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # A. Product Type
            product_options = get_available_products()
            selected_product = st.selectbox(
                "A. Product Type",
                product_options,
                key="weight_calc_product",
                index=product_options.index(st.session_state.weight_calc_product) if st.session_state.weight_calc_product in product_options else 0
            )
            st.session_state.weight_calc_product = selected_product
            
            # Show product info
            if selected_product != "Select Product":
                st.caption(f"Selected: {selected_product}")
        
        with col2:
            # B. Series (Inch/Metric)
            series_options = get_series_for_product(selected_product)
            selected_series = st.selectbox(
                "B. Series",
                series_options,
                key="weight_calc_series",
                index=series_options.index(st.session_state.weight_calc_series) if st.session_state.weight_calc_series in series_options else 0
            )
            st.session_state.weight_calc_series = selected_series
            
            # Show series info
            if selected_series != "Select Series":
                st.caption(f"Series: {selected_series}")
        
        with col3:
            # C. Standard (based on Product + Series)
            standard_options = get_standards_for_product_series(selected_product, selected_series)
            selected_standard = st.selectbox(
                "C. Standard",
                standard_options,
                key="weight_calc_standard",
                index=standard_options.index(st.session_state.weight_calc_standard) if st.session_state.weight_calc_standard in standard_options else 0
            )
            st.session_state.weight_calc_standard = selected_standard
            
            # Show standard info
            if selected_standard != "Select Standard":
                st.caption(f"Standard: {selected_standard}")
        
        st.markdown("---")
        st.markdown("### Diameter Specification")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # D. Cylinder Diameter Type
            diameter_type_options = ["Blank Diameter", "Pitch Diameter"]
            selected_diameter_type = st.radio(
                "D. Cylinder Diameter Type",
                diameter_type_options,
                key="weight_calc_diameter_type",
                index=diameter_type_options.index(st.session_state.weight_calc_diameter_type) if st.session_state.weight_calc_diameter_type in diameter_type_options else 0
            )
            st.session_state.weight_calc_diameter_type = selected_diameter_type
        
        with col2:
            # E. Conditional Input based on Diameter Type
            if selected_diameter_type == "Blank Diameter":
                st.markdown("**Blank Diameter Input**")
                dia_col1, dia_col2 = st.columns(2)
                with dia_col1:
                    blank_diameter = st.number_input(
                        "Blank Diameter Value",
                        min_value=0.1,
                        value=float(st.session_state.weight_calc_blank_diameter),
                        step=0.1,
                        key="weight_calc_blank_diameter"
                    )
                    st.session_state.weight_calc_blank_diameter = blank_diameter
                with dia_col2:
                    blank_dia_unit = st.selectbox(
                        "Unit",
                        ["mm", "inch"],
                        key="weight_calc_blank_dia_unit",
                        index=0 if st.session_state.weight_calc_blank_dia_unit == "mm" else 1
                    )
                    st.session_state.weight_calc_blank_dia_unit = blank_dia_unit
                
                st.caption(f"Blank Diameter: {blank_diameter} {blank_dia_unit}")
            
            else:  # Pitch Diameter
                st.markdown("**Thread Specification**")
                
                # Thread Standard
                thread_std_options = get_thread_standards_for_series(selected_series)
                if selected_series == "Select Series":
                    thread_std_options = ["Select Thread Standard"]
                
                thread_standard = st.selectbox(
                    "Thread Standard",
                    thread_std_options,
                    key="weight_calc_thread_standard",
                    index=thread_std_options.index(st.session_state.weight_calc_thread_standard) if st.session_state.weight_calc_thread_standard in thread_std_options else 0
                )
                st.session_state.weight_calc_thread_standard = thread_standard
                
                if thread_standard != "Select Thread Standard":
                    # Thread Size
                    thread_size_options = get_thread_sizes_enhanced(thread_standard)
                    thread_size = st.selectbox(
                        "Thread Size",
                        thread_size_options,
                        key="weight_calc_thread_size",
                        index=thread_size_options.index(st.session_state.weight_calc_thread_size) if st.session_state.weight_calc_thread_size in thread_size_options else 0
                    )
                    st.session_state.weight_calc_thread_size = thread_size
                    
                    # Thread Class
                    if thread_standard == "ASME B1.1":
                        thread_class_options = get_thread_classes_enhanced(thread_standard)
                        if len(thread_class_options) == 1:  # Only "All"
                            thread_class_options = ["2A", "3A", "1A"]
                        thread_class = st.selectbox(
                            "Tolerance Class",
                            thread_class_options,
                            key="weight_calc_thread_class",
                            index=thread_class_options.index(st.session_state.weight_calc_thread_class) if st.session_state.weight_calc_thread_class in thread_class_options else 0
                        )
                        st.session_state.weight_calc_thread_class = thread_class
                    else:
                        thread_class_options = get_thread_classes_enhanced(thread_standard)
                        thread_class = st.selectbox(
                            "Tolerance Class",
                            thread_class_options,
                            key="weight_calc_thread_class",
                            index=thread_class_options.index(st.session_state.weight_calc_thread_class) if st.session_state.weight_calc_thread_class in thread_class_options else 0
                        )
                        st.session_state.weight_calc_thread_class = thread_class
                    
                    st.caption(f"Thread: {thread_standard}, Size: {thread_size}, Class: {thread_class}")
        
        st.markdown("---")
        st.markdown("### Additional Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Length
            length_col1, length_col2 = st.columns(2)
            with length_col1:
                length = st.number_input(
                    "Length",
                    min_value=0.1,
                    value=float(st.session_state.weight_calc_length),
                    step=0.1,
                    key="weight_calc_length"
                )
                st.session_state.weight_calc_length = length
            with length_col2:
                length_unit = st.selectbox(
                    "Unit",
                    ["mm", "inch", "meter"],
                    key="weight_calc_length_unit",
                    index=["mm", "inch", "meter"].index(st.session_state.weight_calc_length_unit) if st.session_state.weight_calc_length_unit in ["mm", "inch", "meter"] else 0
                )
                st.session_state.weight_calc_length_unit = length_unit
        
        with col2:
            # Material
            material_options = ["Carbon Steel", "Stainless Steel", "Alloy Steel", "Brass", "Aluminum"]
            material = st.selectbox(
                "Material",
                material_options,
                key="weight_calc_material",
                index=material_options.index(st.session_state.weight_calc_material) if st.session_state.weight_calc_material in material_options else 0
            )
            st.session_state.weight_calc_material = material
        
        with col3:
            # Calculate button space
            st.markdown("<br>", unsafe_allow_html=True)
            calculate_btn = st.form_submit_button("Calculate Weight", use_container_width=True, type="primary")
    
    # Display current selection summary
    if selected_product != "Select Product":
        st.markdown("### Current Selection Summary")
        
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.markdown(f"""
            **Product Standards:**
            - **Product Type:** {selected_product}
            - **Series:** {selected_series}
            - **Standard:** {selected_standard}
            """)
        
        with summary_col2:
            if selected_diameter_type == "Blank Diameter":
                st.markdown(f"""
                **Diameter Specification:**
                - **Type:** {selected_diameter_type}
                - **Value:** {st.session_state.weight_calc_blank_diameter} {st.session_state.weight_calc_blank_dia_unit}
                """)
            else:
                st.markdown(f"""
                **Diameter Specification:**
                - **Type:** {selected_diameter_type}
                - **Thread Standard:** {st.session_state.weight_calc_thread_standard}
                - **Thread Size:** {st.session_state.weight_calc_thread_size}
                - **Thread Class:** {st.session_state.weight_calc_thread_class}
                """)
        
        st.markdown(f"""
        **Additional Parameters:**
        - **Length:** {st.session_state.weight_calc_length} {st.session_state.weight_calc_length_unit}
        - **Material:** {st.session_state.weight_calc_material}
        """)
    
    if calculate_btn:
        # Validate inputs
        validation_errors = []
        
        if selected_product == "Select Product":
            validation_errors.append("Please select a Product Type")
        if selected_series == "Select Series":
            validation_errors.append("Please select a Series")
        if selected_standard == "Select Standard":
            validation_errors.append("Please select a Standard")
        if selected_diameter_type == "Pitch Diameter" and st.session_state.weight_calc_thread_standard == "Select Thread Standard":
            validation_errors.append("Please select a Thread Standard for Pitch Diameter")
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            st.success("**Ready for Weight Calculation Implementation**")
            st.info("""
            **All inputs validated successfully!**
            
            The weight calculation logic can now be implemented using:
            - Product dimensional data from selected standard
            - Diameter specification (Blank or Pitch)
            - Length and material parameters
            """)
            
            # Show debug information
            if st.session_state.debug_mode:
                st.markdown("### Debug Information")
                st.json({
                    "product": selected_product,
                    "series": selected_series,
                    "standard": selected_standard,
                    "diameter_type": selected_diameter_type,
                    "blank_diameter": st.session_state.weight_calc_blank_diameter if selected_diameter_type == "Blank Diameter" else "N/A",
                    "blank_dia_unit": st.session_state.weight_calc_blank_dia_unit if selected_diameter_type == "Blank Diameter" else "N/A",
                    "thread_standard": st.session_state.weight_calc_thread_standard if selected_diameter_type == "Pitch Diameter" else "N/A",
                    "thread_size": st.session_state.weight_calc_thread_size if selected_diameter_type == "Pitch Diameter" else "N/A",
                    "thread_class": st.session_state.weight_calc_thread_class if selected_diameter_type == "Pitch Diameter" else "N/A",
                    "length": st.session_state.weight_calc_length,
                    "length_unit": st.session_state.weight_calc_length_unit,
                    "material": st.session_state.weight_calc_material
                })

def show_batch_calculator_enhanced():
    """Enhanced batch calculator with same workflow"""
    
    st.markdown("### Batch Weight Calculator - ENHANCED WORKFLOW")
    
    st.info("""
    **Batch processing with the same product standards workflow**
    Upload a CSV/Excel file with columns matching the single calculator inputs.
    """)
    
    # Download template
    st.markdown("### Download Enhanced Batch Template")
    template_data = {
        'Product_Type': ['Hex Bolt', 'Heavy Hex Bolt', 'Hex Cap Screws'],
        'Series': ['Inch', 'Inch', 'Inch'],
        'Standard': ['ASME B18.2.1', 'ASME B18.2.1', 'ASME B18.2.1'],
        'Diameter_Type': ['Blank Diameter', 'Pitch Diameter', 'Blank Diameter'],
        'Blank_Diameter': [6.35, 0, 9.525],
        'Blank_Diameter_Unit': ['mm', 'mm', 'mm'],
        'Thread_Standard': ['N/A', 'ASME B1.1', 'N/A'],
        'Thread_Size': ['N/A', '1/4', 'N/A'],
        'Thread_Class': ['N/A', '2A', 'N/A'],
        'Length': [50, 100, 75],
        'Length_Unit': ['mm', 'mm', 'mm'],
        'Material': ['Carbon Steel', 'Carbon Steel', 'Carbon Steel']
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
            required_cols = ['Product_Type', 'Series', 'Standard', 'Diameter_Type', 'Length']
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
# ADVANCED AI ASSISTANT WITH SELF-LEARNING CAPABILITIES
# ======================================================
class AdvancedFastenerAI:
    def __init__(self, df, df_iso4014, df_mechem, thread_files, df_din7991=None, df_asme_b18_3=None):
        self.df = df
        self.df_iso4014 = df_iso4014
        self.df_mechem = df_mechem
        self.df_din7991 = df_din7991
        self.df_asme_b18_3 = df_asme_b18_3
        self.thread_files = thread_files
        
        try:
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.qa_pipeline = pipeline("question-answering", 
                                      model="distilbert-base-cased-distilled-squad")
            st.session_state.ai_model_loaded = True
        except Exception as e:
            st.warning(f"AI models loading issue: {str(e)}")
            st.session_state.ai_model_loaded = False
        
        try:
            self.chroma_client = chromadb.Client()
            self.collection = self.chroma_client.create_collection(name="fastener_knowledge")
        except:
            self.collection = None
        
        self.knowledge_base = self._build_knowledge_base()
        self.learning_memory = {}
        self.conversation_history = []
        
        self._index_database_content()
    
    def _build_knowledge_base(self):
        """Build comprehensive fastener knowledge base"""
        return {
            'technical_terms': {
                'tensile_strength': "The maximum stress a material can withstand while being stretched or pulled before breaking",
                'yield_strength': "The stress at which a material begins to deform plastically. Beyond this point, permanent deformation occurs",
                'hardness': "Resistance to permanent indentation. Common scales: Rockwell (HRC, HRB), Brinell (HB)",
                'thread_pitch': "Distance between thread peaks. In metric: distance in mm. In inch: threads per inch (TPI)",
                'proof_load': "Maximum load a fastener can withstand without permanent deformation",
                'carbon_content': "Carbon percentage in steel. Affects hardness and strength. C% typically 0.05-0.55% for fastener steels",
                'manganese': "Mn% improves hardenability and strength. Typically 0.30-1.00% in fastener steels",
                'phosphorus': "P% impurity that reduces toughness. Limited to 0.04% max in quality fasteners",
                'sulfur': "S% impurity that reduces ductility. Limited to 0.05% max in quality fasteners",
            },
            'material_science': {
                'carbon_steel': "Iron-carbon alloy with carbon content up to 2.1%. Most common fastener material. Grades: 2, 5, 8",
                'stainless_steel': "Steel alloy with minimum 10.5% chromium for corrosion resistance. Types: 304, 316, 410",
                'alloy_steel': "Steel with additional alloying elements like chromium, nickel, molybdenum for enhanced properties",
                'brass': "Copper-zinc alloy with good corrosion resistance and electrical conductivity",
            },
            'grade_properties': {
                'Grade 2': {
                    'description': 'Low carbon steel for general purpose applications',
                    'chemistry': 'C: 0.05-0.31%, Mn: 0.90% max, P: 0.04% max, S: 0.05% max',
                    'mechanical': 'Tensile: 74,000 psi min, Yield: 57,000 psi min',
                    'hardness': 'RB 70-100',
                    'applications': 'General purpose, low stress applications'
                },
                'Grade 5': {
                    'description': 'Medium carbon steel, quenched and tempered',
                    'chemistry': 'C: 0.28-0.55%, Mn: 0.60% max, P: 0.04% max, S: 0.05% max',
                    'mechanical': 'Tensile: 120,000 psi min, Yield: 92,000 psi min',
                    'hardness': 'RC 25-34',
                    'applications': 'Automotive, machinery, construction'
                },
                'Grade 8': {
                    'description': 'Medium carbon alloy steel, quenched and tempered',
                    'chemistry': 'C: 0.36-0.55%, Mn: 0.90% max, P: 0.04% max, S: 0.05% max',
                    'mechanical': 'Tensile: 150,000 psi min, Yield: 130,000 psi min',
                    'hardness': 'RC 33-39',
                    'applications': 'High-strength applications, automotive suspension'
                },
                'Stainless 304': {
                    'description': 'Austenitic stainless steel, excellent corrosion resistance',
                    'chemistry': 'C: 0.08% max, Cr: 18-20%, Ni: 8-10.5%',
                    'mechanical': 'Tensile: 75,000 psi min, Yield: 30,000 psi min',
                    'applications': 'Corrosive environments, food processing'
                }
            },
            'column_mappings': {
                'carbon': ['C%', 'Carbon', 'Carbon Content', 'C'],
                'manganese': ['Mn%', 'Manganese', 'Mn Content'],
                'phosphorus': ['P%', 'Phosphorus', 'P Content'],
                'sulfur': ['S%', 'Sulfur', 'S Content'],
                'tensile': ['Tensile Strength', 'Tensile', 'UTS'],
                'yield': ['Yield Strength', 'Yield', 'Proof Strength'],
                'hardness': ['Hardness', 'HRC', 'HRB', 'Brinell'],
                'grade': ['Grade', 'Product Grade', 'Class'],
            }
        }
    
    def _index_database_content(self):
        """Index all database content for semantic search"""
        if not st.session_state.ai_model_loaded:
            return
            
        try:
            if not self.df.empty:
                for idx, row in self.df.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "main_db", "row_index": idx}],
                        ids=[f"main_{idx}"]
                    )
            
            if not self.df_iso4014.empty:
                for idx, row in self.df_iso4014.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "iso_db", "row_index": idx}],
                        ids=[f"iso_{idx}"]
                    )
            
            if not self.df_mechem.empty:
                for idx, row in self.df_mechem.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "mecert_db", "row_index": idx}],
                        ids=[f"mecert_{idx}"]
                    )
            
            if self.df_din7991 is not None and not self.df_din7991.empty:
                for idx, row in self.df_din7991.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "din7991_db", "row_index": idx}],
                        ids=[f"din7991_{idx}"]
                    )
            
            if self.df_asme_b18_3 is not None and not self.df_asme_b18_3.empty:
                for idx, row in self.df_asme_b18_3.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "asme_b18_3_db", "row_index": idx}],
                        ids=[f"asme_b18_3_{idx}"]
                    )
        except Exception as e:
            st.warning(f"Database indexing issue: {str(e)}")
    
    def _semantic_search(self, query, n_results=5):
        """Perform semantic search on database content"""
        if not st.session_state.ai_model_loaded or self.collection is None:
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return results
        except:
            return []
    
    def _extract_entities_advanced(self, query):
        """Advanced entity extraction using multiple methods"""
        entities = {
            'property': None,
            'material': None,
            'grade': None,
            'size': None,
            'value_type': None,
        }
        
        query_lower = query.lower()
        
        property_keywords = {
            'carbon': ['c%', 'carbon', 'carbon content'],
            'tensile': ['tensile', 'ultimate strength', 'uts'],
            'yield': ['yield', 'proof strength'],
            'hardness': ['hardness', 'hrc', 'hrb', 'brinell'],
            'elongation': ['elongation', 'ductility'],
            'manganese': ['mn%', 'manganese'],
            'phosphorus': ['p%', 'phosphorus'],
            'sulfur': ['s%', 'sulfur'],
        }
        
        for prop, keywords in property_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                entities['property'] = prop
                break
        
        grade_patterns = [
            r'grade\s+([2458]|B7|L7)',
            r'([2458])\s+grade',
            r'stainless\s+(304|316|410)',
        ]
        
        for pattern in grade_patterns:
            match = re.search(pattern, query_lower)
            if match:
                entities['grade'] = f"Grade {match.group(1)}" if match.group(1).isdigit() else match.group(1)
                break
        
        if 'stainless' in query_lower:
            entities['material'] = 'stainless steel'
        elif 'carbon' in query_lower and 'steel' in query_lower:
            entities['material'] = 'carbon steel'
        elif 'alloy' in query_lower:
            entities['material'] = 'alloy steel'
        elif 'brass' in query_lower:
            entities['material'] = 'brass'
        
        if 'minimum' in query_lower or 'min' in query_lower:
            entities['value_type'] = 'min'
        elif 'maximum' in query_lower or 'max' in query_lower:
            entities['value_type'] = 'max'
        elif 'typical' in query_lower or 'average' in query_lower:
            entities['value_type'] = 'typical'
        elif 'range' in query_lower:
            entities['value_type'] = 'range'
        
        return entities
    
    def _search_database_for_property(self, entities):
        """Search database for specific properties"""
        results = []
        
        if entities.get('property') == 'carbon':
            if not self.df_mechem.empty:
                carbon_cols = [col for col in self.df_mechem.columns if any(keyword in col.lower() for keyword in ['carbon', 'c%'])]
                if carbon_cols:
                    carbon_data = self.df_mechem[carbon_cols].dropna()
                    if not carbon_data.empty:
                        results.append(f"Carbon content data found in ME&CERT database:")
                        for col in carbon_cols:
                            unique_vals = carbon_data[col].unique()[:5]
                            results.append(f"  {col}: {', '.join(map(str, unique_vals))}")
        
        return results
    
    def _get_technical_answer(self, query, entities):
        """Generate technical answer based on knowledge base"""
        response_parts = []
        
        if entities.get('property') in ['carbon', 'manganese', 'phosphorus', 'sulfur']:
            prop_name = entities['property']
            grade = entities.get('grade', 'general')
            
            if grade in self.knowledge_base['grade_properties']:
                grade_info = self.knowledge_base['grade_properties'][grade]
                chemistry = grade_info.get('chemistry', '')
                
                if prop_name == 'carbon' and 'C:' in chemistry:
                    response_parts.append(f"**{grade} Carbon Content (C%):**")
                    response_parts.append(f"Chemical composition: {chemistry}")
                    response_parts.append(f"Description: {grade_info['description']}")
                else:
                    response_parts.append(f"**{grade} Properties:**")
                    response_parts.append(f"Chemistry: {chemistry}")
                    response_parts.append(f"Mechanical: {grade_info.get('mechanical', 'N/A')}")
                    response_parts.append(f"Hardness: {grade_info.get('hardness', 'N/A')}")
                    response_parts.append(f"Applications: {grade_info.get('applications', 'N/A')}")
            else:
                if prop_name in self.knowledge_base['technical_terms']:
                    response_parts.append(f"**{prop_name.title()} Content Information:**")
                    response_parts.append(self.knowledge_base['technical_terms'][prop_name])
        
        elif entities.get('property') in ['tensile', 'yield', 'hardness']:
            prop_name = entities['property']
            grade = entities.get('grade', 'general')
            
            if grade in self.knowledge_base['grade_properties']:
                grade_info = self.knowledge_base['grade_properties'][grade]
                response_parts.append(f"**{grade} Mechanical Properties:**")
                
                if prop_name == 'tensile':
                    response_parts.append(f"Tensile Strength: {grade_info.get('mechanical', '').split(',')[0]}")
                elif prop_name == 'yield':
                    mech_parts = grade_info.get('mechanical', '').split(',')
                    if len(mech_parts) > 1:
                        response_parts.append(f"Yield Strength: {mech_parts[1]}")
                elif prop_name == 'hardness':
                    response_parts.append(f"Hardness: {grade_info.get('hardness', 'N/A')}")
                
                response_parts.append(f"Applications: {grade_info.get('applications', 'N/A')}")
        
        return response_parts
    
    def process_complex_query(self, query):
        """Process complex technical queries with advanced reasoning"""
        if not st.session_state.ai_model_loaded:
            return "AI capabilities are currently limited. Please ensure all required models are installed."
        
        entities = self._extract_entities_advanced(query)
        
        semantic_results = self._semantic_search(query)
        
        response_parts = []
        
        technical_answer = self._get_technical_answer(query, entities)
        if technical_answer:
            response_parts.extend(technical_answer)
        
        db_results = self._search_database_for_property(entities)
        if db_results:
            response_parts.extend([""] + db_results)
        
        if not response_parts:
            query_lower = query.lower()
            
            if any(word in query_lower for word in ['what is', 'what does', 'explain', 'define']):
                for term, definition in self.knowledge_base['technical_terms'].items():
                    if term in query_lower:
                        response_parts.append(f"**{term.title()}:** {definition}")
                        break
            
            if not response_parts:
                response_parts.append("I understand you're asking about fastener properties. ")
                response_parts.append("I can help with:")
                response_parts.append("• Chemical composition (C%, Mn%, P%, S%)")
                response_parts.append("• Mechanical properties (tensile, yield, hardness)")
                response_parts.append("• Material grades and their specifications")
                response_parts.append("• Database queries and calculations")
                response_parts.append("\nTry asking: 'What is the carbon content in Grade 5?' or 'Show me tensile strength data'")
        
        return "\n".join(response_parts)
    
    def learn_from_interaction(self, query, response, was_helpful=True):
        """Learn from user interactions to improve future responses"""
        interaction_key = query.lower().strip()
        
        if interaction_key not in self.learning_memory:
            self.learning_memory[interaction_key] = {
                'response': response,
                'helpful_count': 0,
                'total_uses': 0,
                'last_used': datetime.now().isoformat()
            }
        
        self.learning_memory[interaction_key]['total_uses'] += 1
        if was_helpful:
            self.learning_memory[interaction_key]['helpful_count'] += 1
        
        self.learning_memory[interaction_key]['last_used'] = datetime.now().isoformat()

# ======================================================
# Enhanced Data Quality Indicators
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
        
        if st.session_state.ai_model_loaded:
            st.markdown('<div class="data-quality-indicator quality-good">AI Assistant: Advanced Mode</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">AI Assistant: Basic Mode</div>', unsafe_allow_html=True)

# ======================================================
# MESSENGER-STYLE CHAT INTERFACE WITH ADVANCED AI
# ======================================================
def add_message(role, content):
    """Add message to chat history"""
    timestamp = datetime.now().strftime("%H:%M")
    st.session_state.chat_messages.append({
        'role': role,
        'content': content,
        'time': timestamp
    })

def show_typing_indicator():
    """Show typing indicator"""
    st.markdown("""
    <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div>
    """, unsafe_allow_html=True)

def show_chat_interface():
    """Show messenger-style chat interface with advanced AI"""
    
    ai_assistant = AdvancedFastenerAI(df, df_iso4014, df_mechem, thread_files, df_din7991, df_asme_b18_3)
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
            PiU - Advanced Fastener Intelligence
        </h1>
        <p style="margin:0;">Ask complex technical questions about materials, properties, and specifications</p>
        <div style="margin-top: 0.5rem;">
            <span class="engineering-badge">Semantic Search</span>
            <span class="technical-badge">Technical AI</span>
            <span class="material-badge">Self-Learning</span>
            <span class="grade-badge">Multi-Database</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.ai_model_loaded:
        st.success("Advanced AI Mode: Semantic search and technical reasoning enabled")
    else:
        st.warning("Basic AI Mode: Install transformers, sentence-transformers, chromadb for full capabilities")
    
    st.markdown("### Technical Questions")
    technical_questions = [
        "What is C% in Grade 5?",
        "Compare Grade 5 vs Grade 8 mechanical properties",
        "Chemical composition of stainless steel 304",
        "Tensile strength range for different grades",
        "Hardness specifications for alloy steels"
    ]
    
    cols = st.columns(5)
    for idx, question in enumerate(technical_questions):
        with cols[idx]:
            if st.button(question, use_container_width=True, key=f"tech_{idx}"):
                add_message("user", question)
                st.session_state.ai_thinking = True
                st.rerun()
    
    st.markdown("### Advanced AI Chat")
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    for msg in st.session_state.chat_messages:
        if msg['role'] == 'user':
            st.markdown(f"""
            <div class="message user-message">
                <div>{msg['content']}</div>
                <div class="message-time">{msg['time']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            formatted_content = msg['content'].replace('\n', '<br>')
            st.markdown(f"""
            <div class="message ai-message">
                <div>{formatted_content}</div>
                <div class="message-time">{msg['time']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    if st.session_state.ai_thinking:
        show_typing_indicator()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_input("Ask complex technical questions...", key="chat_input", label_visibility="collapsed")
    
    with col2:
        send_button = st.button("Send", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if send_button and user_input.strip():
        add_message("user", user_input.strip())
        st.session_state.ai_thinking = True
        st.rerun()
    
    if st.session_state.ai_thinking:
        last_user_message = st.session_state.chat_messages[-1]['content']
        
        time.sleep(1)
        
        ai_response = ai_assistant.process_complex_query(last_user_message)
        add_message("ai", ai_response)
        
        ai_assistant.learn_from_interaction(last_user_message, ai_response, was_helpful=True)
        
        st.session_state.ai_thinking = False
        st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with col2:
        if st.button("Reload AI Models", use_container_width=True):
            st.session_state.ai_model_loaded = False
            st.rerun()

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
    
    # Get current date and user info
    current_date = datetime.now().strftime('%d/%m/%Y')
    generated_by = "Partha Sharma"  # This could be dynamic based on user login
    
    # Create the professional card HTML
    card_html = f"""
    <div class="professional-card">
        <div class="card-header">
            <div>
                <h1 class="card-title">{product_name}</h1>
                <p class="card-subtitle">Size: {size} | Standard: {standard}</p>
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
# FIXED SECTION A - PROPER PRODUCT-SERIES-STANDARD-SIZE RELATIONSHIP
# ======================================================

def get_products_for_standard(standard):
    """Get available products for a specific standard"""
    if standard in st.session_state.available_products:
        return st.session_state.available_products[standard]
    return ["All"]

def get_series_for_standard(standard):
    """Get series for a specific standard"""
    if standard in st.session_state.available_series:
        return st.session_state.available_series[standard]
    return "All"

def get_filtered_dataframe(product_type, standard):
    """Get filtered dataframe based on product type and standard"""
    if standard == "ASME B18.2.1":
        temp_df = df.copy()
        if product_type != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product_type]
        return temp_df
    
    elif standard == "ISO 4014":
        temp_df = df_iso4014.copy()
        if product_type != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product_type]
        return temp_df
    
    elif standard == "DIN-7991":
        temp_df = df_din7991.copy()
        if product_type != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product_type]
        return temp_df
    
    elif standard == "ASME B18.3":
        temp_df = df_asme_b18_3.copy()
        if product_type != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product_type]
        return temp_df
    
    return pd.DataFrame()

# ======================================================
# FIXED SECTION A FILTERING LOGIC
# ======================================================
def apply_section_a_filters():
    """Apply filters for Section A only - completely independent"""
    filters = st.session_state.section_a_filters
    
    if not filters:
        return pd.DataFrame()
    
    selected_standard = filters.get('standard', 'All')
    
    if selected_standard == "All":
        return pd.DataFrame()
    
    result_df = pd.DataFrame()
    
    if selected_standard == "ASME B18.2.1" and not df.empty:
        result_df = df.copy()
    elif selected_standard == "ISO 4014" and not df_iso4014.empty:
        result_df = df_iso4014.copy()
    elif selected_standard == "DIN-7991" and st.session_state.din7991_loaded:
        result_df = df_din7991.copy()
    elif selected_standard == "ASME B18.3" and st.session_state.asme_b18_3_loaded:
        result_df = df_asme_b18_3.copy()
    else:
        return pd.DataFrame()
    
    # Apply product filter
    if filters.get('product') and filters['product'] != "All" and 'Product' in result_df.columns:
        result_df = result_df[result_df['Product'] == filters['product']]
    
    # Apply size filter - FIXED: Normalize both values to string for comparison
    if filters.get('size') and filters['size'] != "All" and 'Size' in result_df.columns:
        try:
            # Convert both to string and strip whitespace for proper comparison
            result_df = result_df[
                result_df['Size'].astype(str).str.strip() == str(filters['size']).strip()
            ]
        except Exception as e:
            st.warning(f"Size filtering issue: {str(e)}")
            pass
    
    return result_df

def show_section_a_results():
    """Display results for Section A"""
    if st.session_state.section_a_results.empty:
        return
    
    st.markdown('<div class="section-results">', unsafe_allow_html=True)
    st.markdown("### Section A Results - Dimensional Specifications")
    
    result_df = st.session_state.section_a_results
    
    st.markdown(f"**Found {len(result_df)} matching products**")
    
    # NEW: Professional Card View Toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        show_card_view = st.checkbox("Show Professional Card View", value=st.session_state.show_professional_card, key="card_view_toggle")
        st.session_state.show_professional_card = show_card_view
    
    # Show professional card if enabled and we have results
    if st.session_state.show_professional_card and not result_df.empty:
        # Use the first result for the card display
        first_product = result_df.iloc[0]
        product_details = extract_product_details(first_product)
        st.session_state.selected_product_details = product_details
        
        # Show the professional card
        show_professional_product_card(product_details)
    
    # Always show the data table
    st.dataframe(
        result_df,
        use_container_width=True,
        height=400
    )
    
    # Export options for Section A
    col1, col2 = st.columns(2)
    with col1:
        export_format_a = st.selectbox("Export Format", ["Excel", "CSV"], key="export_section_a")
    with col2:
        if st.button("Export Section A Results", use_container_width=True, key="export_btn_a"):
            enhanced_export_data(result_df, export_format_a)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ======================================================
# FIXED SECTION B - THREAD SPECIFICATIONS WITH PROPER DATA TYPES
# ======================================================
def apply_section_b_filters():
    """Apply filters for Section B only - completely independent"""
    filters = st.session_state.section_b_filters
    
    if not filters:
        return pd.DataFrame()
    
    selected_standard = filters.get('standard', 'All')
    
    if selected_standard == "All":
        return pd.DataFrame()
    
    # Get thread data using enhanced function
    result_df = get_thread_data_enhanced(
        selected_standard,
        filters.get('size'),
        filters.get('class')
    )
    
    return result_df

def show_section_b_results():
    """Display results for Section B"""
    if st.session_state.section_b_results.empty:
        return
    
    st.markdown('<div class="section-results">', unsafe_allow_html=True)
    st.markdown("### Section B Results - Thread Specifications")
    
    result_df = st.session_state.section_b_results
    
    st.markdown(f"**Found {len(result_df)} matching thread specifications**")
    
    # Show data info for debugging
    if st.session_state.debug_mode:
        st.info(f"**Debug Info:** Columns: {result_df.columns.tolist()}, Shape: {result_df.shape}")
        if not result_df.empty:
            st.info(f"Sample data types: {result_df.dtypes.to_dict()}")
    
    st.dataframe(
        result_df,
        use_container_width=True,
        height=400
    )
    
    # Export options for Section B
    col1, col2 = st.columns(2)
    with col1:
        export_format_b = st.selectbox("Export Format", ["Excel", "CSV"], key="export_section_b")
    with col2:
        if st.button("Export Section B Results", use_container_width=True, key="export_btn_b"):
            enhanced_export_data(result_df, export_format_b)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ======================================================
# SECTION C - MATERIAL PROPERTIES - COMPLETELY FIXED VERSION
# ======================================================
def apply_section_c_filters():
    """Apply filters for Section C only - completely independent - COMPLETELY FIXED"""
    filters = st.session_state.section_c_filters
    
    if not filters:
        return pd.DataFrame()
    
    property_class = filters.get('property_class', 'All')
    standard = filters.get('standard', 'All')
    
    if property_class == "All":
        return pd.DataFrame()
    
    if df_mechem.empty:
        return pd.DataFrame()
    
    result_df = df_mechem.copy()
    
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
    
    # Apply property class filter using ALL possible columns
    filtered_data = pd.DataFrame()
    
    for prop_col in property_class_cols:
        if prop_col in result_df.columns:
            # Try exact match first
            exact_match = result_df[result_df[prop_col] == property_class]
            if not exact_match.empty:
                filtered_data = exact_match
                break
            # Try string contains for more flexible matching
            str_match = result_df[result_df[prop_col].astype(str).str.contains(str(property_class), na=False, case=False)]
            if not str_match.empty:
                filtered_data = str_match
                break
    
    # If no match found with property class, return empty
    if filtered_data.empty:
        return pd.DataFrame()
    
    result_df = filtered_data
    
    # Apply standard filter if specified
    if standard != "All":
        # Find ALL possible standard columns
        standard_cols = []
        possible_standard_cols = ['Standard', 'Specification', 'Norm', 'Type', 'Designation']
        
        for col in result_df.columns:
            col_lower = str(col).lower()
            for possible in possible_standard_cols:
                if possible.lower() in col_lower:
                    standard_cols.append(col)
                    break
        
        # If no standard columns found, look for columns containing standard-like data
        if not standard_cols:
            for col in result_df.columns:
                if any(word in col.lower() for word in ['iso', 'astm', 'asme', 'din', 'bs', 'jis', 'gb']):
                    standard_cols.append(col)
                    break
        
        # Apply standard filter using ALL possible columns
        standard_filtered = pd.DataFrame()
        
        for std_col in standard_cols:
            if std_col in result_df.columns:
                # Try exact match
                exact_std_match = result_df[result_df[std_col] == standard]
                if not exact_std_match.empty:
                    standard_filtered = exact_std_match
                    break
                # Try string contains
                str_std_match = result_df[result_df[std_col].astype(str).str.contains(str(standard), na=False, case=False)]
                if not str_std_match.empty:
                    standard_filtered = str_std_match
                    break
        
        if not standard_filtered.empty:
            result_df = standard_filtered
    
    return result_df

def show_section_c_results():
    """Display results for Section C - COMPLETELY FIXED"""
    if st.session_state.section_c_results.empty:
        return
    
    st.markdown('<div class="section-results">', unsafe_allow_html=True)
    st.markdown("### Section C Results - Material Properties")
    
    result_df = st.session_state.section_c_results
    
    st.markdown(f"**Found {len(result_df)} matching material properties**")
    
    # Show debug info if enabled
    if st.session_state.debug_mode:
        st.info(f"**Debug Info Section C:** Columns: {result_df.columns.tolist()}, Shape: {result_df.shape}")
    
    st.dataframe(
        result_df,
        use_container_width=True,
        height=400
    )
    
    # Show detailed properties
    filters = st.session_state.section_c_filters
    if filters and filters.get('property_class') and filters['property_class'] != "All":
        show_mechanical_chemical_details(filters['property_class'])
    
    # Export options for Section C
    col1, col2 = st.columns(2)
    with col1:
        export_format_c = st.selectbox("Export Format", ["Excel", "CSV"], key="export_section_c")
    with col2:
        if st.button("Export Section C Results", use_container_width=True, key="export_btn_c"):
            enhanced_export_data(result_df, export_format_c)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ======================================================
# COMBINE ALL SECTIONS RESULTS
# ======================================================
def combine_all_results():
    """Combine results from all sections for final display"""
    all_results = []
    
    # Add Section A results with source identifier
    if not st.session_state.section_a_results.empty:
        section_a_df = st.session_state.section_a_results.copy()
        section_a_df['Data_Source'] = 'Section_A_Dimensional'
        all_results.append(section_a_df)
    
    # Add Section B results with source identifier
    if not st.session_state.section_b_results.empty:
        section_b_df = st.session_state.section_b_results.copy()
        section_b_df['Data_Source'] = 'Section_B_Thread'
        all_results.append(section_b_df)
    
    # Add Section C results with source identifier
    if not st.session_state.section_c_results.empty:
        section_c_df = st.session_state.section_c_results.copy()
        section_c_df['Data_Source'] = 'Section_C_Material'
        all_results.append(section_c_df)
    
    if not all_results:
        return pd.DataFrame()
    
    # Combine all dataframes
    combined_df = pd.concat(all_results, ignore_index=True)
    return combined_df

def show_combined_results():
    """Display combined results from all sections"""
    if st.session_state.combined_results.empty:
        return
    
    st.markdown('<div class="combined-results">', unsafe_allow_html=True)
    st.markdown("### Combined Results - All Sections")
    
    combined_df = st.session_state.combined_results
    
    # Summary statistics
    section_a_count = len(combined_df[combined_df['Data_Source'] == 'Section_A_Dimensional'])
    section_b_count = len(combined_df[combined_df['Data_Source'] == 'Section_B_Thread'])
    section_c_count = len(combined_df[combined_df['Data_Source'] == 'Section_C_Material'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", len(combined_df))
    with col2:
        st.metric("Section A", section_a_count)
    with col3:
        st.metric("Section B", section_b_count)
    with col4:
        st.metric("Section C", section_c_count)
    
    st.markdown(f"**Combined data from all sections: {len(combined_df)} total records**")
    
    st.dataframe(
        combined_df,
        use_container_width=True,
        height=600
    )
    
    # Export combined results
    st.markdown("### Export Combined Results")
    col1, col2 = st.columns(2)
    with col1:
        export_format_combined = st.selectbox("Export Format", ["Excel", "CSV"], key="export_combined")
    with col2:
        if st.button("Export All Results", use_container_width=True, type="primary", key="export_all_btn"):
            enhanced_export_data(combined_df, export_format_combined)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ======================================================
# FIXED SECTION A - PROPER PRODUCT-SERIES-STANDARD-SIZE RELATIONSHIP
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

def get_available_sizes_for_standard_product(standard, product):
    """Get available sizes based on selected standard and product"""
    size_options = ["All"]
    
    if standard == "All" or product == "All":
        return size_options
    
    temp_df = get_filtered_dataframe(product, standard)
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
            <span class="engineering-badge">Independent Sections</span>
            <span class="material-badge">Separate Filters</span>
            <span class="grade-badge">Individual Results</span>
            <span class="technical-badge">Combined View</span>
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
            <p><strong>Relationship:</strong> Product -> Series -> Standards -> Size</p>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
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
        
        # Debug information
        if st.session_state.debug_mode:
            st.info(f"""
            **Debug Info - Section A:**
            - Product: {dimensional_product}
            - Series: {dimensional_series} 
            - Standards Available: {len(available_standards)-1}
            - Sizes Available: {len(available_sizes)-1}
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
                    'size': dimensional_size
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
            <span class="technical-badge">Professional UI</span>
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
        ("AI Assistant", "Technical queries and material analysis", "ai"),
        ("Export Reports", "Generate professional engineering reports", "export")
    ]
    
    for idx, (title, description, key) in enumerate(actions):
        with cols[idx % 3]:
            if st.button(f"**{title}**\n\n{description}", key=f"home_{key}"):
                section_map = {
                    "database": "Product Database",
                    "calculator": "Calculations", 
                    "ai": "PiU (AI Assistant)"
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
            "Batch processing capabilities"
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
            4. **D. Cylinder Diameter Type** - Blank Diameter (Body) or Pitch Diameter (Thread)
            5. **E. Conditional Input:**
               - **Blank Diameter**: Manual value input
               - **Pitch Diameter**: Thread specification dropdown
            
            **Purpose:**
            - Get accurate dimensional data from standards for weight calculations
            - Handle both body diameter and thread pitch diameter scenarios
            - Maintain smooth filtering like Product Database section
            """)

# ======================================================
# SECTION DISPATCHER
# ======================================================
def show_section(title):
    if title == "Product Database":
        show_enhanced_product_database()
    elif title == "Calculations":
        show_enhanced_calculations()
    elif title == "PiU (AI Assistant)":
        show_chat_interface()
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
            "Calculations",
            "PiU (AI Assistant)"
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
            <p style="font-size: 0.8rem;">Professional Fastener Intelligence Platform v4.0 - ENHANCED Weight Calculator</p>
        </div>
    """, unsafe_allow_html=True)

# Run the application
if __name__ == "__main__":
    main()