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
warnings.filterwarnings('ignore')

# ======================================================
# 🔹 Paths & Files - UPDATED WITH GOOGLE SHEETS LINKS
# ======================================================
url = "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx"
local_excel_path = r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"

# UPDATED: Mechanical and Chemical Properties paths
me_chem_google_url = "https://docs.google.com/spreadsheets/d/12lBzI67Wb0yZyJKYxpDCLzHF9zvS2Fha/export?format=xlsx"
me_chem_path = r"G:\My Drive\Streamlite\Mechanical and Chemical.xlsx"

# ISO 4014 paths - local and Google Sheets
iso4014_local_path = r"G:\My Drive\Streamlite\ISO 4014 Hex Bolt.xlsx"
iso4014_file_url = "https://docs.google.com/spreadsheets/d/1d2hANwoMhuzwyKJ72c125Uy0ujB6QsV_/export?format=xlsx"

# DIN-7991 paths - local and Google Sheets
din7991_local_path = r"G:\My Drive\Streamlite\DIN-7991.xlsx"
din7991_file_url = "https://docs.google.com/spreadsheets/d/1PjptIbFfebdF1h_Aj124fNgw5jNBWlvn/export?format=xlsx"

# NEW: ASME B18.3 paths - local and Google Sheets
asme_b18_3_local_path = r"G:\My Drive\Streamlite\ASME B18.3.xlsx"
asme_b18_3_file_url = "https://docs.google.com/spreadsheets/d/1dPNGwf7bv5A77rMSPpl11dhcJTXQfob1/export?format=xlsx"

# Thread files - UPDATED WITH GOOGLE SHEETS LINKS
thread_files = {
    "ASME B1.1": "https://docs.google.com/spreadsheets/d/1YHgUloNsFudxxqhWQV66D2DtSSKWFP_w/export?format=xlsx",
    "ISO 965-2-98 Coarse": "https://docs.google.com/spreadsheets/d/1be5eEy9hbVfMg2sl1-Cz1NNCGGF8EB-L/export?format=xlsx",
    "ISO 965-2-98 Fine": "https://docs.google.com/spreadsheets/d/1QGQ6SMWBSTsah-vq3zYnhOC3NXaBdKPe/export?format=xlsx",
}

# ======================================================
# 🔹 Enhanced Configuration & Error Handling
# ======================================================
@st.cache_data(ttl=3600, show_spinner=False)
def safe_load_excel_file_enhanced(path_or_url, max_retries=3, timeout=30):
    """Enhanced loading with better caching, validation and retry mechanism"""
    for attempt in range(max_retries):
        try:
            if path_or_url.startswith('http'):
                import requests
                from io import BytesIO
                
                # Add headers to mimic browser request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(path_or_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                # Validate file size
                if len(response.content) < 100:  # Too small to be valid
                    st.warning(f"File seems too small: {path_or_url}")
                    continue
                    
                df = pd.read_excel(BytesIO(response.content))
            else:
                if os.path.exists(path_or_url):
                    file_size = os.path.getsize(path_or_url)
                    if file_size < 100:  # Too small to be valid
                        st.warning(f"File seems too small: {path_or_url}")
                        continue
                    df = pd.read_excel(path_or_url)
                else:
                    st.error(f"File not found: {path_or_url}")
                    return pd.DataFrame()
            
            # Validate dataframe structure
            if df.empty:
                st.warning(f"Empty dataframe loaded from: {path_or_url}")
                return pd.DataFrame()
                
            # Basic data validation
            if len(df.columns) < 2:
                st.warning(f"Dataframe has too few columns: {path_or_url}")
                return pd.DataFrame()
                
            return df
            
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"Error loading {path_or_url}: {str(e)}")
                return pd.DataFrame()
            time.sleep(1)  # Wait before retry

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
                'page_title': 'JSC Industries – Fastener Intelligence'
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
        "debug_mode": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize config and preferences
    load_config()
    save_user_preferences()

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
# 🔹 Page Setup with Professional Engineering Styling
# ======================================================
st.set_page_config(
    page_title="JSC Industries – Fastener Intelligence", 
    layout="wide",
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

# Professional Engineering CSS with Enhanced Card Design
st.markdown("""
<style>
    /* Professional Color Scheme */
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
    
    /* Professional Card Designs */
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
    
    /* Professional Badge System */
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
    
    /* Specification Grid Layout */
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
    
    /* Section Headers */
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
    
    /* Enhanced Buttons */
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
    
    /* Data Quality Indicators */
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
    
    /* Professional Table Styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Quick Action Cards */
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
    
    /* Metric Cards */
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
    
    /* Property Grid for Material Data */
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

    /* Messenger Style Chat CSS */
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
    
    /* Filter Section Styling */
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
    
    /* Multi-search styling */
    .multi-search-item {
        background: var(--neutral-light);
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        border-left: 3px solid #3498db;
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
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
initialize_session_state()

# ======================================================
# 🔹 ENHANCED DATA LOADING WITH PRODUCT MAPPING
# ======================================================

# Load main data
df = safe_load_excel_file_enhanced(url) if url else safe_load_excel_file_enhanced(local_excel_path)

# Load Mechanical and Chemical data
df_mechem = safe_load_excel_file_enhanced(me_chem_google_url)
if df_mechem.empty:
    st.info("🔄 Online Mechanical & Chemical file not accessible, trying local version...")
    df_mechem = safe_load_excel_file_enhanced(me_chem_path)

# Load ISO 4014 data
df_iso4014 = safe_load_excel_file_enhanced(iso4014_file_url)
if df_iso4014.empty:
    st.info("🔄 Online ISO 4014 file not accessible, trying local version...")
    df_iso4014 = safe_load_excel_file_enhanced(iso4014_local_path)

# Load DIN-7991 data
df_din7991 = safe_load_excel_file_enhanced(din7991_file_url)
if df_din7991.empty:
    st.info("🔄 Online DIN-7991 file not accessible, trying local version...")
    df_din7991 = safe_load_excel_file_enhanced(din7991_local_path)

# Load ASME B18.3 data
df_asme_b18_3 = safe_load_excel_file_enhanced(asme_b18_3_file_url)
if df_asme_b18_3.empty:
    st.info("🔄 Online ASME B18.3 file not accessible, trying local version...")
    df_asme_b18_3 = safe_load_excel_file_enhanced(asme_b18_3_local_path)

# ======================================================
# 🔹 ENHANCED DATA PROCESSING WITH STANDARD MAPPING
# ======================================================

def process_standard_data():
    """Process all standards data and extract products and series"""
    
    # Initialize products and series mapping
    standard_products = {}
    standard_series = {}
    
    # Process ASME B18.2.1 Data
    if not df.empty:
        if 'Product' in df.columns:
            asme_products = df['Product'].dropna().unique().tolist()
            standard_products['ASME B18.2.1'] = ["All"] + sorted(asme_products)
        else:
            standard_products['ASME B18.2.1'] = ["All", "Hex Bolt", "Heavy Hex Bolt", "Hex Screw", "Heavy Hex Screw"]
        standard_series['ASME B18.2.1'] = "Inch"
    
    # Process ASME B18.3 Data
    if not df_asme_b18_3.empty:
        if 'Product' in df_asme_b18_3.columns:
            asme_b18_3_products = df_asme_b18_3['Product'].dropna().unique().tolist()
            standard_products['ASME B18.3'] = ["All"] + sorted(asme_b18_3_products)
        else:
            standard_products['ASME B18.3'] = ["All", "Hexagon Socket Head Cap Screws"]
        standard_series['ASME B18.3'] = "Inch"
    
    # Process DIN-7991 Data
    if not df_din7991.empty:
        if 'Product' in df_din7991.columns:
            din_products = df_din7991['Product'].dropna().unique().tolist()
            standard_products['DIN-7991'] = ["All"] + sorted(din_products)
        else:
            standard_products['DIN-7991'] = ["All", "Hexagon Socket Countersunk Head Cap Screw"]
        standard_series['DIN-7991'] = "Metric"
    
    # Process ISO 4014 Data
    if not df_iso4014.empty:
        # Handle different column names for ISO 4014
        product_col = None
        for col in df_iso4014.columns:
            if 'product' in col.lower():
                product_col = col
                break
        
        if product_col:
            iso_products = df_iso4014[product_col].dropna().unique().tolist()
            standard_products['ISO 4014'] = ["All"] + sorted(iso_products)
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
    # Handle different column names for ISO 4014
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
    
    # Handle grade column
    grade_col = None
    for col in df_iso4014.columns:
        if 'grade' in col.lower():
            grade_col = col
            break
    
    if grade_col and grade_col != 'Product Grade':
        df_iso4014['Product Grade'] = df_iso4014[grade_col]

@st.cache_data
def load_thread_data(file_path):
    """Load thread data with proper error handling"""
    try:
        df_thread = pd.read_excel(file_path)
        return df_thread
    except Exception as e:
        st.sidebar.error(f"❌ Error loading thread data: {str(e)}")
        return pd.DataFrame()

# ======================================================
# 🔹 ENHANCED MECHANICAL & CHEMICAL DATA PROCESSING
# ======================================================
def process_mechanical_chemical_data():
    """Process and extract property classes from Mechanical & Chemical data"""
    if df_mechem.empty:
        return [], []
    
    try:
        # Store column names for analysis
        me_chem_columns = df_mechem.columns.tolist()
        
        # Identify property class column
        property_class_col = None
        possible_class_cols = ['Grade', 'Class', 'Property Class', 'Material Grade', 'Type', 'Designation']
        
        for col in me_chem_columns:
            col_lower = col.lower()
            for possible in possible_class_cols:
                if possible.lower() in col_lower:
                    property_class_col = col
                    break
            if property_class_col:
                break
        
        # If no specific column found, use first column as default
        if not property_class_col and len(me_chem_columns) > 0:
            property_class_col = me_chem_columns[0]
        
        # Extract unique property classes
        property_classes = []
        if property_class_col and property_class_col in df_mechem.columns:
            property_classes = df_mechem[property_class_col].dropna().unique().tolist()
            property_classes = [str(pc) for pc in property_classes if str(pc).strip() != '']
        
        # Store in session state
        st.session_state.me_chem_columns = me_chem_columns
        st.session_state.property_classes = property_classes
        
        return me_chem_columns, property_classes
        
    except Exception as e:
        st.error(f"Error processing Mechanical & Chemical data: {str(e)}")
        return [], []

def get_standards_for_property_class(property_class):
    """Get available standards for a specific property class"""
    if df_mechem.empty or not property_class:
        return []
    
    try:
        # Identify property class column
        property_class_col = None
        for col in st.session_state.me_chem_columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['grade', 'class', 'property']):
                property_class_col = col
                break
        
        if not property_class_col:
            return []
        
        # Filter data for the selected property class
        filtered_data = df_mechem[df_mechem[property_class_col] == property_class]
        
        # Look for standards columns
        standards = []
        possible_standard_cols = ['Standard', 'Specification', 'Norm', 'Type']
        
        for col in filtered_data.columns:
            col_lower = col.lower()
            for possible in possible_standard_cols:
                if possible.lower() in col_lower:
                    # Get unique standards from this column
                    col_standards = filtered_data[col].dropna().unique()
                    standards.extend([str(std) for std in col_standards if str(std).strip() != ''])
                    break
        
        # Remove duplicates and return
        return list(set(standards))
        
    except Exception as e:
        st.error(f"Error getting standards for {property_class}: {str(e)}")
        return []

def show_mechanical_chemical_details(property_class):
    """Show detailed mechanical and chemical properties for a selected property class"""
    if df_mechem.empty or not property_class:
        return
    
    try:
        # Identify property class column
        property_class_col = None
        for col in st.session_state.me_chem_columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['grade', 'class', 'property']):
                property_class_col = col
                break
        
        if not property_class_col:
            return
        
        # Filter data for the selected property class
        filtered_data = df_mechem[df_mechem[property_class_col] == property_class]
        
        if filtered_data.empty:
            st.info(f"No detailed data found for {property_class}")
            return
        
        # Display the data
        st.markdown(f"### 🧪 Detailed Properties for {property_class}")
        
        # Show as dataframe
        st.dataframe(
            filtered_data,
            use_container_width=True,
            height=400
        )
        
        # Show key properties in a nice format
        st.markdown("#### 📊 Key Properties")
        
        # Group properties by type
        mechanical_props = []
        chemical_props = []
        other_props = []
        
        for col in filtered_data.columns:
            col_lower = col.lower()
            # Skip the property class column itself
            if col == property_class_col:
                continue
            
            # Categorize columns
            if any(keyword in col_lower for keyword in ['tensile', 'yield', 'hardness', 'strength', 'elongation', 'proof']):
                mechanical_props.append(col)
            elif any(keyword in col_lower for keyword in ['carbon', 'manganese', 'phosphorus', 'sulfur', 'chromium', 'nickel', 'chemical']):
                chemical_props.append(col)
            else:
                other_props.append(col)
        
        # Display mechanical properties
        if mechanical_props:
            st.markdown("**Mechanical Properties:**")
            mech_cols = st.columns(min(3, len(mechanical_props)))
            for idx, prop in enumerate(mechanical_props):
                with mech_cols[idx % len(mech_cols)]:
                    value = filtered_data[prop].iloc[0] if not filtered_data[prop].isna().all() else "N/A"
                    st.metric(prop, value)
        
        # Display chemical properties
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
# 🔹 COMPLETELY BULLETPROOF SIZE HANDLING - FIXED VERSION
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

# ======================================================
# 🔹 ENHANCED WEIGHT CALCULATION WITH ALL PRODUCT TYPES
# ======================================================
def calculate_weight_enhanced(product, diameter_mm, length_mm, diameter_type="body"):
    """Enhanced weight calculation for all product types with diameter type support"""
    if diameter_mm <= 0 or length_mm <= 0:
        return 0
    
    try:
        density = 0.00785  # g/mm^3 for steel
        
        # Calculate shank volume (common for all products)
        V_shank = 3.1416 * (diameter_mm / 2) ** 2 * length_mm
        
        # Calculate head/nut volume based on product type
        head_volume = 0
        product_lower = product.lower()
        
        if "hex cap" in product_lower or "hex bolt" in product_lower:
            # Hex head bolt
            a = 1.5 * diameter_mm  # across flats
            h = 0.8 * diameter_mm  # head height
            head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
            
        elif "heavy hex" in product_lower:
            # Heavy hex bolt
            a = 2 * diameter_mm  # across flats
            h = 1.2 * diameter_mm  # head height
            head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
            
        elif "socket head" in product_lower or "low head cap" in product_lower:
            # Socket head cap screw
            h = 0.6 * diameter_mm
            r = 0.8 * diameter_mm / 2
            head_volume = 3.1416 * r ** 2 * h
            
        elif "button head" in product_lower:
            # Button head screw
            h = 0.4 * diameter_mm
            r = 0.9 * diameter_mm / 2
            head_volume = 3.1416 * r ** 2 * h
            
        elif "countersunk" in product_lower or "counter sunk" in product_lower:
            # Countersunk head screw - conical head volume
            h = 0.6 * diameter_mm  # head height
            r = diameter_mm  # head radius
            head_volume = (1/3) * 3.1416 * r ** 2 * h  # Cone volume
            
        elif "threaded rod" in product_lower or "stud" in product_lower:
            # Threaded rod or stud - no head, just threaded portion
            # For threaded rods, we calculate based on nominal diameter
            # Threaded rods typically have reduced cross-sectional area due to threads
            if diameter_type == "pitch":
                # Use pitch diameter for more accurate calculation
                head_volume = 0
            else:
                # Use nominal diameter
                head_volume = 0
                
        elif "nut" in product_lower:
            # Hex nut - calculate nut volume
            a = 1.5 * diameter_mm  # across flats
            h = 0.8 * diameter_mm  # nut height
            head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
            
        elif "washer" in product_lower:
            # Washer - annular volume
            outer_dia = 2 * diameter_mm
            inner_dia = diameter_mm
            thickness = 0.1 * diameter_mm
            head_volume = 3.1416 * ((outer_dia/2)**2 - (inner_dia/2)**2) * thickness
            
        else:
            # Default for unknown products - assume standard hex head
            a = 1.5 * diameter_mm
            h = 0.8 * diameter_mm
            head_volume = (3 * (3 ** 0.5) / 2) * a ** 2 * h
        
        # For threaded rods and studs, apply thread reduction factor
        if "threaded rod" in product_lower or "stud" in product_lower:
            # Thread reduction factor (approximate)
            thread_reduction = 0.85  # 15% reduction due to threads
            V_shank = V_shank * thread_reduction
        
        total_volume = V_shank + head_volume
        weight_kg = total_volume * density / 1000
        return round(weight_kg, 4)
        
    except Exception as e:
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
        return 0

# ======================================================
# 🔹 ADVANCED AI ASSISTANT WITH SELF-LEARNING CAPABILITIES
# ======================================================
class AdvancedFastenerAI:
    def __init__(self, df, df_iso4014, df_mechem, thread_files, df_din7991=None, df_asme_b18_3=None):
        self.df = df
        self.df_iso4014 = df_iso4014
        self.df_mechem = df_mechem
        self.df_din7991 = df_din7991
        self.df_asme_b18_3 = df_asme_b18_3
        self.thread_files = thread_files
        
        # Initialize AI components with error handling
        try:
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.qa_pipeline = pipeline("question-answering", 
                                      model="distilbert-base-cased-distilled-squad")
            st.session_state.ai_model_loaded = True
        except Exception as e:
            st.warning(f"AI models loading issue: {str(e)}")
            st.session_state.ai_model_loaded = False
        
        # Initialize vector database
        try:
            self.chroma_client = chromadb.Client()
            self.collection = self.chroma_client.create_collection(name="fastener_knowledge")
        except:
            self.collection = None
        
        # Knowledge base and learning memory
        self.knowledge_base = self._build_knowledge_base()
        self.learning_memory = {}
        self.conversation_history = []
        
        # Index all database content for semantic search
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
            # Index main database
            if not self.df.empty:
                for idx, row in self.df.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "main_db", "row_index": idx}],
                        ids=[f"main_{idx}"]
                    )
            
            # Index ISO 4014 database
            if not self.df_iso4014.empty:
                for idx, row in self.df_iso4014.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "iso_db", "row_index": idx}],
                        ids=[f"iso_{idx}"]
                    )
            
            # Index ME&CERT database
            if not self.df_mechem.empty:
                for idx, row in self.df_mechem.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "mecert_db", "row_index": idx}],
                        ids=[f"mecert_{idx}"]
                    )
            
            # Index DIN-7991 database
            if self.df_din7991 is not None and not self.df_din7991.empty:
                for idx, row in self.df_din7991.iterrows():
                    text_content = " ".join([str(val) for val in row.values if pd.notna(val)])
                    self.collection.add(
                        documents=[text_content],
                        metadatas=[{"source": "din7991_db", "row_index": idx}],
                        ids=[f"din7991_{idx}"]
                    )
            
            # Index ASME B18.3 database
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
            'value_type': None,  # min, max, typical, range
        }
        
        query_lower = query.lower()
        
        # Property extraction
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
        
        # Grade extraction
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
        
        # Material extraction
        if 'stainless' in query_lower:
            entities['material'] = 'stainless steel'
        elif 'carbon' in query_lower and 'steel' in query_lower:
            entities['material'] = 'carbon steel'
        elif 'alloy' in query_lower:
            entities['material'] = 'alloy steel'
        elif 'brass' in query_lower:
            entities['material'] = 'brass'
        
        # Value type extraction
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
            # Search in ME&CERT database for carbon content
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
        
        # Handle chemical composition queries
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
                # General property information
                if prop_name in self.knowledge_base['technical_terms']:
                    response_parts.append(f"**{prop_name.title()} Content Information:**")
                    response_parts.append(self.knowledge_base['technical_terms'][prop_name])
        
        # Handle mechanical properties queries
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
        
        # Extract entities using advanced method
        entities = self._extract_entities_advanced(query)
        
        # Perform semantic search
        semantic_results = self._semantic_search(query)
        
        response_parts = []
        
        # Generate technical answer
        technical_answer = self._get_technical_answer(query, entities)
        if technical_answer:
            response_parts.extend(technical_answer)
        
        # Add database search results
        db_results = self._search_database_for_property(entities)
        if db_results:
            response_parts.extend([""] + db_results)
        
        # If no specific answer found, provide general information
        if not response_parts:
            # Try to answer using knowledge base
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
# 🔹 Enhanced Data Quality Indicators
# ======================================================
def show_data_quality_indicators():
    """Show data quality and validation indicators"""
    st.sidebar.markdown("---")
    with st.sidebar.expander("📊 Data Quality Status"):
        # Main data quality
        if not df.empty:
            total_rows = len(df)
            missing_data = df.isnull().sum().sum()
            completeness = ((total_rows * len(df.columns) - missing_data) / (total_rows * len(df.columns))) * 100
            st.markdown(f'<div class="data-quality-indicator quality-good">Main Data: {completeness:.1f}% Complete</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-error">Main Data: Not Loaded</div>', unsafe_allow_html=True)
        
        # ISO 4014 data quality
        if not df_iso4014.empty:
            st.markdown(f'<div class="data-quality-indicator quality-good">ISO 4014: {len(df_iso4014)} Records</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">ISO 4014: Limited Access</div>', unsafe_allow_html=True)
        
        # DIN-7991 data quality
        if st.session_state.din7991_loaded:
            st.markdown(f'<div class="data-quality-indicator quality-good">DIN-7991: {len(df_din7991)} Records</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">DIN-7991: Limited Access</div>', unsafe_allow_html=True)
        
        # ASME B18.3 data quality
        if st.session_state.asme_b18_3_loaded:
            st.markdown(f'<div class="data-quality-indicator quality-good">ASME B18.3: {len(df_asme_b18_3)} Records</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">ASME B18.3: Limited Access</div>', unsafe_allow_html=True)
        
        # Mechanical & Chemical data quality
        if not df_mechem.empty:
            st.markdown(f'<div class="data-quality-indicator quality-good">Mech & Chem: {len(df_mechem)} Records</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size: 0.8rem; margin: 0.1rem 0;">Property Classes: {len(st.session_state.property_classes)}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">Mech & Chem: Limited Access</div>', unsafe_allow_html=True)
        
        # Thread data quality
        thread_status = []
        for standard, url in thread_files.items():
            df_thread = load_thread_data(url)
            if not df_thread.empty:
                thread_status.append(f"{standard}: ✅")
            else:
                thread_status.append(f"{standard}: ❌")
        
        st.markdown(f'<div class="data-quality-indicator quality-good">Thread Data: Available</div>', unsafe_allow_html=True)
        for status in thread_status:
            st.markdown(f'<div style="font-size: 0.8rem; margin: 0.1rem 0;">{status}</div>', unsafe_allow_html=True)
        
        # AI Status
        if st.session_state.ai_model_loaded:
            st.markdown('<div class="data-quality-indicator quality-good">AI Assistant: Advanced Mode</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-quality-indicator quality-warning">AI Assistant: Basic Mode</div>', unsafe_allow_html=True)

# ======================================================
# 🔹 MESSENGER-STYLE CHAT INTERFACE WITH ADVANCED AI
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
    
    # Initialize AI assistant with all data sources
    ai_assistant = AdvancedFastenerAI(df, df_iso4014, df_mechem, thread_files, df_din7991, df_asme_b18_3)
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
            🤖 PiU - Advanced Fastener Intelligence
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
    
    # AI Status Indicator
    if st.session_state.ai_model_loaded:
        st.success("✅ Advanced AI Mode: Semantic search and technical reasoning enabled")
    else:
        st.warning("⚠️ Basic AI Mode: Install transformers, sentence-transformers, chromadb for full capabilities")
    
    # Quick questions for complex queries
    st.markdown("### 🔬 Technical Questions")
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
    
    # Chat container
    st.markdown("### 💬 Advanced AI Chat")
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display chat messages
    for msg in st.session_state.chat_messages:
        if msg['role'] == 'user':
            st.markdown(f"""
            <div class="message user-message">
                <div>{msg['content']}</div>
                <div class="message-time">{msg['time']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Format AI response with proper line breaks
            formatted_content = msg['content'].replace('\n', '<br>')
            st.markdown(f"""
            <div class="message ai-message">
                <div>{formatted_content}</div>
                <div class="message-time">{msg['time']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Show typing indicator if AI is thinking
    if st.session_state.ai_thinking:
        show_typing_indicator()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_input("Ask complex technical questions...", key="chat_input", label_visibility="collapsed")
    
    with col2:
        send_button = st.button("Send", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Process user input
    if send_button and user_input.strip():
        add_message("user", user_input.strip())
        st.session_state.ai_thinking = True
        st.rerun()
    
    # Process AI response if thinking
    if st.session_state.ai_thinking:
        # Get the last user message
        last_user_message = st.session_state.chat_messages[-1]['content']
        
        # Simulate thinking delay
        time.sleep(1)
        
        # Get AI response using advanced processing
        ai_response = ai_assistant.process_complex_query(last_user_message)
        add_message("ai", ai_response)
        
        # Learn from this interaction
        ai_assistant.learn_from_interaction(last_user_message, ai_response, was_helpful=True)
        
        st.session_state.ai_thinking = False
        st.rerun()
    
    # Clear chat button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with col2:
        if st.button("🔄 Reload AI Models", use_container_width=True):
            st.session_state.ai_model_loaded = False
            st.rerun()

# ======================================================
# 🔹 Enhanced Export Functionality
# ======================================================
def export_to_excel(df, filename_prefix):
    """Export dataframe to Excel with formatting"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Data']
                
                # Add some basic formatting
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
                    label="📥 Download Excel File",
                    data=f,
                    file_name=f"fastener_data_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"excel_export_{timestamp}"
                )
    else:  # CSV
        csv_data = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV File",
            data=csv_data,
            file_name=f"fastener_data_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"csv_export_{timestamp}"
        )

# ======================================================
# 🔹 Enhanced Batch Processing
# ======================================================
def process_batch_data(uploaded_file):
    """Enhanced batch processing with progress bar"""
    try:
        if uploaded_file.name.endswith('.xlsx'):
            batch_df = pd.read_excel(uploaded_file)
        else:
            batch_df = pd.read_csv(uploaded_file)
        
        # Validate required columns
        required_cols = ['Product', 'Size', 'Length']
        missing_cols = [col for col in required_cols if col not in batch_df.columns]
        
        if missing_cols:
            st.error(f"Missing required columns: {missing_cols}")
            return None
        
        # Process with progress bar
        progress_bar = st.progress(0)
        results = []
        
        for i, row in batch_df.iterrows():
            # Simulate processing - replace with actual calculation logic
            processed_row = {
                'Product': row['Product'],
                'Size': row['Size'],
                'Length': row['Length'],
                'Calculated_Weight': f"Result_{i}",  # Replace with actual calculation
                'Status': 'Processed'
            }
            results.append(processed_row)
            progress_bar.progress((i + 1) / len(batch_df))
            time.sleep(0.1)  # Simulate processing time
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"Batch processing error: {str(e)}")
        return None

# ======================================================
# 🔹 Enhanced Calculation History
# ======================================================
def save_calculation_history(calculation_data):
    """Save calculation to history"""
    if 'calculation_history' not in st.session_state:
        st.session_state.calculation_history = []
    
    calculation_data['timestamp'] = datetime.now().isoformat()
    st.session_state.calculation_history.append(calculation_data)
    
    # Keep only last 20 calculations
    if len(st.session_state.calculation_history) > 20:
        st.session_state.calculation_history = st.session_state.calculation_history[-20:]

def show_calculation_history():
    """Display calculation history"""
    if 'calculation_history' in st.session_state and st.session_state.calculation_history:
        st.markdown("### 📝 Recent Calculations")
        for calc in reversed(st.session_state.calculation_history[-5:]):  # Show last 5
            with st.container():
                st.markdown(f"""
                <div class="calculation-card">
                    <strong>{calc.get('product', 'N/A')}</strong> | 
                    Size: {calc.get('size', 'N/A')} | 
                    Weight: {calc.get('weight', 'N/A')} kg
                    <br><small>{calc.get('timestamp', '')}</small>
                </div>
                """, unsafe_allow_html=True)

# ======================================================
# 🔹 ENHANCED PRODUCT INTELLIGENCE CENTER - FIXED FILTERING
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

def clean_dataframe_columns(df):
    """Remove empty columns and clean dataframe - ENHANCED VERSION"""
    if df.empty:
        return df
    
    # Remove completely empty columns
    df = df.dropna(axis=1, how='all')
    
    # Remove columns with all the same value
    for col in df.columns:
        if df[col].nunique() <= 1:
            df = df.drop(col, axis=1)
    
    # Remove columns that are mostly empty (>90% NaN)
    threshold = len(df) * 0.1  # Keep columns with at least 10% data
    df = df.dropna(axis=1, thresh=threshold)
    
    # Remove columns with only whitespace or empty strings
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check if all values are empty strings or whitespace
            if df[col].str.strip().replace('', pd.NA).isna().all():
                df = df.drop(col, axis=1)
    
    return df

def show_enhanced_product_database():
    """Enhanced Product Intelligence Center with comprehensive filtering"""
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
            🎯 Product Intelligence Center
        </h1>
        <p style="margin:0; opacity: 0.9;">Advanced Multi-Product Search & Technical Specifications</p>
        <div style="margin-top: 1rem;">
            <span class="engineering-badge">Multi-Product Search</span>
            <span class="material-badge">Technical Filters</span>
            <span class="grade-badge">Professional Export</span>
            <span class="technical-badge">Real-time Analytics</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if df.empty and df_mechem.empty and df_iso4014.empty and not st.session_state.din7991_loaded and not st.session_state.asme_b18_3_loaded:
        st.error("🚫 No data sources available. Please check your data connections.")
        return
    
    # Quick Stats - UPDATED: Shows all 4 dimensional standards
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = len(df) + (len(df_iso4014) if not df_iso4014.empty else 0) + (len(df_din7991) if st.session_state.din7991_loaded else 0) + (len(df_asme_b18_3) if st.session_state.asme_b18_3_loaded else 0)
    total_dimensional_standards = st.session_state.dimensional_standards_count
    total_threads = len(thread_files)
    total_mecert = len(df_mechem) if not df_mechem.empty else 0
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">📊 Total Products</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_products:,}</h2>
            <p style="color: #7f8c8d; margin:0;">Database Records</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">🌍 Dimensional Standards</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_dimensional_standards}</h2>
            <p style="color: #7f8c8d; margin:0;">ASME B18.2.1, ASME B18.3, ISO 4014, DIN-7991</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">⚡ Thread Types</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_threads}</h2>
            <p style="color: #7f8c8d; margin:0;">Available</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">🔬 ME&CERT</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_mecert}</h2>
            <p style="color: #7f8c8d; margin:0;">Properties</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Debug mode toggle
    with st.sidebar:
        st.session_state.debug_mode = st.checkbox("🔧 Debug Mode", value=st.session_state.debug_mode)
    
    # Multi-Product Search System
    st.markdown("### 🔍 Multi-Product Search System")
    st.info("💡 Search up to 10 different products simultaneously with individual specifications")
    
    # Initialize multi-search products
    if 'multi_search_products' not in st.session_state:
        st.session_state.multi_search_products = []
    
    # Add new product search
    col1, col2 = st.columns([3, 1])
    with col1:
        new_product_name = st.text_input("Add Product Search", placeholder="Enter product name (e.g., Hex Bolt, Stud, Threaded Rod)")
    with col2:
        if st.button("➕ Add Product", use_container_width=True) and new_product_name:
            if len(st.session_state.multi_search_products) < 10:
                st.session_state.multi_search_products.append({
                    'name': new_product_name,
                    'filters': {}
                })
                st.rerun()
            else:
                st.warning("Maximum 10 products allowed")
    
    # Display current product searches
    if st.session_state.multi_search_products:
        st.markdown("#### 📋 Active Product Searches")
        for idx, product in enumerate(st.session_state.multi_search_products):
            with st.expander(f"🔧 {product['name']} - Search Configuration", expanded=True):
                configure_product_search(idx, product)
    
    # Main Filtering Sections
    st.markdown("---")
    
    # Section A: Dimensional Specifications
    st.markdown("""
    <div class="filter-section">
        <h3 class="filter-header">📐 Section A - Dimensional Specifications</h3>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Dimensional Standards - UPDATED: All four dimensional standards
        dimensional_standards = ["All"]
        if not df.empty:
            dimensional_standards.append("ASME B18.2.1")
        if not df_iso4014.empty:
            dimensional_standards.append("ISO 4014")
        if st.session_state.din7991_loaded:
            dimensional_standards.append("DIN-7991")
        if st.session_state.asme_b18_3_loaded:
            dimensional_standards.append("ASME B18.3")
        
        dimensional_standard = st.selectbox("Dimensional Standard", dimensional_standards, key="dimensional_standard")
    
    with col2:
        # Product Type - Based on selected standard using actual data from Excel
        if dimensional_standard == "All":
            # Combine all products from all standards
            all_products = set()
            for standard_products in st.session_state.available_products.values():
                all_products.update(standard_products)
            product_types = ["All"] + sorted([p for p in all_products if p != "All"])
        else:
            product_types = get_products_for_standard(dimensional_standard)
        
        dimensional_product = st.selectbox("Product Type", product_types, key="dimensional_product")
    
    with col3:
        # Series System - Based on selected standard
        if dimensional_standard == "All":
            series_options = ["All", "Inch", "Metric"]
        else:
            series_system = get_series_for_standard(dimensional_standard)
            series_options = [series_system]
        
        dimensional_series = st.selectbox("Series System", series_options, key="dimensional_series")
    
    with col4:
        # Size Filter - Get sizes from the actual selected standard
        temp_df = get_filtered_dataframe(dimensional_product, dimensional_standard)
        size_options = get_safe_size_options(temp_df)
        dimensional_size = st.selectbox("Size", size_options, key="dimensional_size")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Section B: Thread Specifications
    st.markdown("""
    <div class="filter-section">
        <h3 class="filter-header">🔩 Section B - Thread Specifications</h3>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Thread Standards
        thread_standards = ["All"]
        if dimensional_series == "Inch" or dimensional_series == "All":
            thread_standards += ["ASME B1.1"]
        if dimensional_series == "Metric" or dimensional_series == "All":
            thread_standards += ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
        
        thread_standard = st.selectbox("Thread Standard", thread_standards, key="thread_standard")
    
    with col2:
        # Thread Size
        thread_size_options = ["All"]
        if thread_standard != "All":
            df_thread = get_thread_data(thread_standard)
            if not df_thread.empty and "Thread" in df_thread.columns:
                thread_size_options += sorted(df_thread['Thread'].dropna().unique())
        thread_size = st.selectbox("Thread Size", thread_size_options, key="thread_size")
    
    with col3:
        # Tolerance Class
        tolerance_options = ["All"]
        if dimensional_series == "Inch" or dimensional_series == "All":
            tolerance_options += ["1A", "2A", "3A"]
        if dimensional_series == "Metric" or dimensional_series == "All":
            tolerance_options += ["6g", "6H", "4g", "4H", "8g", "8H"]
        
        tolerance_class = st.selectbox("Tolerance Class", tolerance_options, key="tolerance_class")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Section C: Material Properties
    st.markdown("""
    <div class="filter-section">
        <h3 class="filter-header">🧪 Section C - Material Properties</h3>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Property Class (Grades)
        property_classes = ["All"]
        
        # Add property classes from Mechanical & Chemical data
        if st.session_state.property_classes:
            property_classes.extend(sorted(st.session_state.property_classes))
        else:
            # Fallback to main database if Mechanical & Chemical data not available
            if not df.empty and 'Product Grade' in df.columns:
                grades = df['Product Grade'].dropna().unique()
                property_classes.extend(sorted(grades))
            if not df_iso4014.empty and 'Product Grade' in df_iso4014.columns:
                iso_grades = df_iso4014['Product Grade'].dropna().unique()
                for grade in iso_grades:
                    if grade not in property_classes:
                        property_classes.append(grade)
        
        property_class = st.selectbox("Property Class (Grade)", property_classes, key="property_class")
        
        # Show Mechanical & Chemical details when a property class is selected
        if property_class != "All":
            with st.expander(f"🔬 View Mechanical & Chemical Details for {property_class}", expanded=False):
                show_mechanical_chemical_details(property_class)
    
    with col2:
        # Standards based on Property Class
        material_standards = ["All"]
        
        if property_class != "All":
            # Get standards from Mechanical & Chemical data
            mechem_standards = get_standards_for_property_class(property_class)
            if mechem_standards:
                material_standards.extend(sorted(mechem_standards))
            else:
                # Fallback to main database standards
                grade_standards = []
                if not df.empty and 'Product Grade' in df.columns:
                    grade_df = df[df['Product Grade'] == property_class]
                    grade_standards.extend(grade_df['Standards'].dropna().unique().tolist())
                if not df_iso4014.empty and 'Product Grade' in df_iso4014.columns:
                    iso_grade_df = df_iso4014[df_iso4014['Product Grade'] == property_class]
                    if not iso_grade_df.empty:
                        grade_standards.append("ISO 4014")
                
                material_standards.extend(sorted(set(grade_standards)))
        
        material_standard = st.selectbox("Material Standard", material_standards, key="material_standard")
        
        # Data source indicator
        if property_class != "All":
            if mechem_standards:
                st.success("✅ Data from Mechanical & Chemical Properties")
            else:
                st.info("ℹ️ Data from main product database")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Apply Filters Button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 APPLY FILTERS & SEARCH", use_container_width=True, type="primary"):
            # Store current filters
            st.session_state.current_filters_dimensional = {
                'product': dimensional_product,
                'series': dimensional_series,
                'standard': dimensional_standard,
                'size': dimensional_size
            }
            st.session_state.current_filters_thread = {
                'standard': thread_standard,
                'size': thread_size,
                'class': tolerance_class
            }
            st.session_state.current_filters_material = {
                'property_class': property_class,
                'standard': material_standard
            }
            st.rerun()
    
    # Display Results
    if (st.session_state.current_filters_dimensional or 
        st.session_state.current_filters_thread or 
        st.session_state.current_filters_material):
        
        show_filtered_results()
    
    # Quick Search Section
    st.markdown("---")
    st.markdown("### ⚡ Quick Search & Filters")
    
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    
    with quick_col1:
        st.markdown("**Dimensional Quick Search**")
        quick_size = st.selectbox("Quick Size Filter", ["All"] + get_safe_size_options(df), key="quick_size")
        if st.button("🔍 Search by Size", use_container_width=True) and quick_size != "All":
            st.session_state.current_filters_dimensional = {'size': quick_size}
            st.rerun()
    
    with quick_col2:
        st.markdown("**Thread Quick Search**")
        quick_thread = st.selectbox("Quick Thread Filter", ["All"] + thread_standards, key="quick_thread")
        if st.button("🔩 Search by Thread", use_container_width=True) and quick_thread != "All":
            st.session_state.current_filters_thread = {'standard': quick_thread}
            st.rerun()
    
    with quick_col3:
        st.markdown("**Material Quick Search**")
        quick_grade = st.selectbox("Quick Grade Filter", ["All"] + property_classes, key="quick_grade")
        if st.button("🧪 Search by Grade", use_container_width=True) and quick_grade != "All":
            st.session_state.current_filters_material = {'property_class': quick_grade}
            st.rerun()

def configure_product_search(index, product):
    """Configure individual product search parameters"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # UPDATED: All dimensional standards
        standard_options = ["All"]
        if not df.empty:
            standard_options.append("ASME B18.2.1")
        if not df_iso4014.empty:
            standard_options.append("ISO 4014")
        if st.session_state.din7991_loaded:
            standard_options.append("DIN-7991")
        if st.session_state.asme_b18_3_loaded:
            standard_options.append("ASME B18.3")
        
        product['filters']['standard'] = st.selectbox(
            "Standard", 
            standard_options, 
            key=f"prod_std_{index}"
        )
    
    with col2:
        # Product types based on selected standard using actual data
        if product['filters']['standard'] == "All":
            # Combine all products from all standards
            all_products = set()
            for standard_products in st.session_state.available_products.values():
                all_products.update(standard_products)
            product_options = ["All"] + sorted([p for p in all_products if p != "All"])
        else:
            product_options = get_products_for_standard(product['filters']['standard'])
        
        product['filters']['type'] = st.selectbox(
            "Product Type", 
            product_options, 
            key=f"prod_type_{index}"
        )
    
    with col3:
        # Size options based on selected standard and product
        temp_df = get_filtered_dataframe(product['filters']['type'], product['filters']['standard'])
        size_options = get_safe_size_options(temp_df)
        product['filters']['size'] = st.selectbox(
            "Size", 
            size_options, 
            key=f"prod_size_{index}"
        )
    
    # Remove product button
    if st.button("🗑️ Remove Product", key=f"remove_{index}"):
        st.session_state.multi_search_products.pop(index)
        st.rerun()

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

def show_filtered_results():
    """Display filtered results in professional format"""
    
    # Apply all filters
    filtered_df = apply_all_filters()
    
    if st.session_state.debug_mode:
        st.markdown("### 🐛 Debug Information")
        st.write("Current Filters:", {
            'dimensional': st.session_state.current_filters_dimensional,
            'thread': st.session_state.current_filters_thread,
            'material': st.session_state.current_filters_material
        })
        st.write("DataFrame Info:")
        st.write(f"Shape: {filtered_df.shape}")
        st.write("Columns:", filtered_df.columns.tolist() if not filtered_df.empty else "No columns")
        st.write("First few rows:")
        st.dataframe(filtered_df.head() if not filtered_df.empty else pd.DataFrame())
    
    if filtered_df.empty:
        st.warning("🚫 No products match the current filters. Try adjusting your search criteria.")
        return
    
    # Clean the dataframe - remove empty columns using enhanced cleaner
    filtered_df = clean_dataframe_columns(filtered_df)
    
    # Results Header
    st.markdown(f"""
    <div class="engineering-header" style="padding: 1.5rem; margin-bottom: 1rem;">
        <h3 style="margin:0;">🎯 Filtered Results: {len(filtered_df)} Products Found</h3>
        <p style="margin:0; opacity: 0.9;">Professional Technical Data Display</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        unique_products = filtered_df['Product'].nunique() if 'Product' in filtered_df.columns else 0
        st.metric("Unique Products", unique_products)
    
    with col2:
        unique_sizes = filtered_df['Size'].nunique() if 'Size' in filtered_df.columns else 0
        st.metric("Unique Sizes", unique_sizes)
    
    with col3:
        unique_standards = filtered_df['Standards'].nunique() if 'Standards' in filtered_df.columns else 0
        st.metric("Standards", unique_standards)
    
    with col4:
        data_completeness = (filtered_df.count().sum() / (filtered_df.shape[0] * filtered_df.shape[1])) * 100
        st.metric("Data Quality", f"{data_completeness:.1f}%")
    
    # Professional Data Display
    st.markdown("### 📊 Professional Data Display")
    
    # Enhanced DataFrame with styling
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=600,
        column_config={
            "Product": st.column_config.TextColumn("Product", width="medium"),
            "Size": st.column_config.TextColumn("Size", width="small"),
            "Standards": st.column_config.TextColumn("Standard", width="medium"),
            "Product Grade": st.column_config.TextColumn("Grade", width="small"),
        }
    )
    
    # Export Section
    st.markdown("---")
    st.markdown("### 📤 Professional Export Options")
    
    export_col1, export_col2, export_col3 = st.columns([2, 1, 1])
    
    with export_col1:
        export_format = st.selectbox("Export Format", ["Excel", "CSV"], key="export_format")
    
    with export_col2:
        include_analysis = st.checkbox("Include Analysis", value=True)
    
    with export_col3:
        if st.button("🚀 Generate Export", use_container_width=True):
            export_filtered_data(filtered_df, export_format, include_analysis)
    
    # Visual Analysis
    if len(filtered_df) > 1:
        st.markdown("---")
        st.markdown("### 📈 Visual Analysis")
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            if 'Product' in filtered_df.columns:
                product_counts = filtered_df['Product'].value_counts().head(8)
                if len(product_counts) > 0:
                    fig_products = px.bar(
                        x=product_counts.index,
                        y=product_counts.values,
                        title="Product Distribution",
                        labels={'x': 'Product', 'y': 'Count'},
                        color=product_counts.values,
                        color_continuous_scale='blues'
                    )
                    st.plotly_chart(fig_products, use_container_width=True)
        
        with viz_col2:
            if 'Size' in filtered_df.columns:
                size_counts = filtered_df['Size'].value_counts().head(8)
                if len(size_counts) > 0:
                    fig_sizes = px.pie(
                        values=size_counts.values,
                        names=size_counts.index,
                        title="Size Distribution"
                    )
                    st.plotly_chart(fig_sizes, use_container_width=True)

def apply_all_filters():
    """Apply all dimensional, thread, and material filters - COMPLETELY FIXED VERSION"""
    
    filtered_dfs = []
    dim_filters = st.session_state.current_filters_dimensional
    
    if st.session_state.debug_mode:
        st.sidebar.write("🔧 Debug - Applying filters:", dim_filters)
    
    # Helper function to apply size filter safely - FIXED VERSION
    def apply_size_filter(df_temp, size_filter):
        if size_filter == "All" or 'Size' not in df_temp.columns:
            return df_temp
        try:
            # Convert both to string for safe comparison - handle NaN values
            df_temp = df_temp.copy()
            df_temp['Size_Str'] = df_temp['Size'].astype(str)
            return df_temp[df_temp['Size_Str'] == str(size_filter)]
        except Exception as e:
            if st.session_state.debug_mode:
                st.sidebar.write(f"❌ Size filter error: {e}")
            return pd.DataFrame()
    
    # Handle ASME B18.2.1 data
    if not df.empty:
        asme_temp = df.copy()
        include_asme = False
        
        # Check if ASME B18.2.1 should be included
        if dim_filters.get('standard') in ["All", "ASME B18.2.1"]:
            include_asme = True
            
            # Apply product filter
            if dim_filters.get('product') and dim_filters['product'] != "All" and 'Product' in asme_temp.columns:
                asme_temp = asme_temp[asme_temp['Product'] == dim_filters['product']]
            
            # Apply size filter
            asme_temp = apply_size_filter(asme_temp, dim_filters.get('size'))
            
        if include_asme and not asme_temp.empty:
            filtered_dfs.append(asme_temp)
            if st.session_state.debug_mode:
                st.sidebar.write(f"✅ ASME B18.2.1: {len(asme_temp)} records")
    
    # Handle ISO 4014 data
    if not df_iso4014.empty:
        iso_temp = df_iso4014.copy()
        include_iso = False
        
        # Check if ISO 4014 should be included
        if dim_filters.get('standard') in ["All", "ISO 4014"]:
            include_iso = True
            
            # Apply product filter
            if dim_filters.get('product') and dim_filters['product'] != "All" and 'Product' in iso_temp.columns:
                iso_temp = iso_temp[iso_temp['Product'] == dim_filters['product']]
            
            # Apply size filter
            if include_iso:
                iso_temp = apply_size_filter(iso_temp, dim_filters.get('size'))
            
        if include_iso and not iso_temp.empty:
            filtered_dfs.append(iso_temp)
            if st.session_state.debug_mode:
                st.sidebar.write(f"✅ ISO 4014: {len(iso_temp)} records")
    
    # Handle DIN-7991 data
    if st.session_state.din7991_loaded:
        din_temp = df_din7991.copy()
        include_din = False
        
        # Check if DIN-7991 should be included
        if dim_filters.get('standard') in ["All", "DIN-7991"]:
            include_din = True
            
            # Apply product filter
            if dim_filters.get('product') and dim_filters['product'] != "All" and 'Product' in din_temp.columns:
                din_temp = din_temp[din_temp['Product'] == dim_filters['product']]
            
            # Apply size filter
            if include_din:
                din_temp = apply_size_filter(din_temp, dim_filters.get('size'))
            
        if include_din and not din_temp.empty:
            filtered_dfs.append(din_temp)
            if st.session_state.debug_mode:
                st.sidebar.write(f"✅ DIN-7991: {len(din_temp)} records")
    
    # Handle ASME B18.3 data
    if st.session_state.asme_b18_3_loaded:
        asme_b18_3_temp = df_asme_b18_3.copy()
        include_asme_b18_3 = False
        
        # Check if ASME B18.3 should be included
        if dim_filters.get('standard') in ["All", "ASME B18.3"]:
            include_asme_b18_3 = True
            
            # Apply product filter
            if dim_filters.get('product') and dim_filters['product'] != "All" and 'Product' in asme_b18_3_temp.columns:
                asme_b18_3_temp = asme_b18_3_temp[asme_b18_3_temp['Product'] == dim_filters['product']]
            
            # Apply size filter
            if include_asme_b18_3:
                asme_b18_3_temp = apply_size_filter(asme_b18_3_temp, dim_filters.get('size'))
            
        if include_asme_b18_3 and not asme_b18_3_temp.empty:
            filtered_dfs.append(asme_b18_3_temp)
            if st.session_state.debug_mode:
                st.sidebar.write(f"✅ ASME B18.3: {len(asme_b18_3_temp)} records")
    
    # Apply material filters
    mat_filters = st.session_state.current_filters_material
    if mat_filters and mat_filters.get('property_class') and mat_filters['property_class'] != "All":
        for i, temp_df in enumerate(filtered_dfs):
            # Handle different grade column names
            grade_col = None
            for col in temp_df.columns:
                if 'grade' in col.lower():
                    grade_col = col
                    break
            
            if grade_col:
                try:
                    filtered_dfs[i] = temp_df[temp_df[grade_col] == mat_filters['property_class']]
                    if st.session_state.debug_mode:
                        st.sidebar.write(f"✅ Applied grade filter: {mat_filters['property_class']}")
                except Exception as e:
                    if st.session_state.debug_mode:
                        st.sidebar.write(f"❌ Grade filter error: {e}")
    
    # Combine all filtered dataframes
    if filtered_dfs:
        final_df = pd.concat(filtered_dfs, ignore_index=True)
        if st.session_state.debug_mode:
            st.sidebar.write(f"🎯 Final combined: {len(final_df)} records")
        return final_df
    else:
        if st.session_state.debug_mode:
            st.sidebar.write("❌ No dataframes to combine")
        return pd.DataFrame()

def export_filtered_data(filtered_df, format_type, include_analysis=True):
    """Export filtered data with professional formatting"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        if format_type == "Excel":
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                    # Main data sheet
                    filtered_df.to_excel(writer, sheet_name='Filtered_Data', index=False)
                    
                    # Analysis sheet if requested
                    if include_analysis:
                        analysis_data = {
                            'Metric': ['Total Records', 'Unique Products', 'Unique Sizes', 'Unique Standards', 'Data Completeness'],
                            'Value': [
                                len(filtered_df),
                                filtered_df['Product'].nunique() if 'Product' in filtered_df.columns else 0,
                                filtered_df['Size'].nunique() if 'Size' in filtered_df.columns else 0,
                                filtered_df['Standards'].nunique() if 'Standards' in filtered_df.columns else 0,
                                f"{(filtered_df.count().sum() / (filtered_df.shape[0] * filtered_df.shape[1])) * 100:.1f}%"
                            ]
                        }
                        pd.DataFrame(analysis_data).to_excel(writer, sheet_name='Analysis', index=False)
                    
                    # Formatting
                    workbook = writer.book
                    worksheet = writer.sheets['Filtered_Data']
                    
                    # Auto-adjust column widths
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
                
                with open(tmp.name, 'rb') as f:
                    st.download_button(
                        label="📥 Download Excel File",
                        data=f,
                        file_name=f"JSC_Product_Data_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"excel_export_{timestamp}"
                    )
        
        else:  # CSV
            csv_data = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV File",
                data=csv_data,
                file_name=f"JSC_Product_Data_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"csv_export_{timestamp}"
            )
            
        st.success("✅ Export generated successfully!")
        
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")

# ======================================================
# 🔹 ENHANCED HOME DASHBOARD WITH PROFESSIONAL DESIGN
# ======================================================
def show_enhanced_home():
    """Show professional engineering dashboard"""
    
    # Professional Header Section
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; font-size: 2.5rem;">🔧 JSC Industries</h1>
        <p style="margin:0; font-size: 1.2rem; opacity: 0.9;">Professional Fastener Intelligence Platform v4.0</p>
        <div style="margin-top: 1rem;">
            <span class="engineering-badge">AI-Powered</span>
            <span class="material-badge">Material Science</span>
            <span class="grade-badge">Multi-Standard</span>
            <span class="technical-badge">Engineering Grade</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Professional Key Metrics - UPDATED: Shows all 4 dimensional standards
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = len(df) + (len(df_iso4014) if not df_iso4014.empty else 0) + (len(df_din7991) if st.session_state.din7991_loaded else 0) + (len(df_asme_b18_3) if st.session_state.asme_b18_3_loaded else 0)
    total_dimensional_standards = st.session_state.dimensional_standards_count
    total_threads = len(thread_files)
    total_mecert = len(df_mechem) if not df_mechem.empty else 0
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">📊 Products</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_products}</h2>
            <p style="color: #7f8c8d; margin:0;">Total Records</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">🌍 Dimensional Standards</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_dimensional_standards}</h2>
            <p style="color: #7f8c8d; margin:0;">ASME B18.2.1, ASME B18.3, ISO 4014, DIN-7991</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">⚡ Thread Types</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_threads}</h2>
            <p style="color: #7f8c8d; margin:0;">Available</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #3498db; margin:0;">🔬 ME&CERT</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_mecert}</h2>
            <p style="color: #7f8c8d; margin:0;">Properties</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Professional Quick Actions
    st.markdown('<h2 class="section-header">🚀 Engineering Tools</h2>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    actions = [
        ("📦 Product Database", "Professional product discovery with engineering filters", "database"),
        ("🧮 Engineering Calculator", "Advanced weight and strength calculations", "calculator"),
        ("📊 Analytics Dashboard", "Visual insights and performance metrics", "analytics"),
        ("🔧 Compare Products", "Side-by-side technical comparison", "compare"),
        ("🤖 AI Assistant", "Technical queries and material analysis", "ai"),
        ("📋 Export Reports", "Generate professional engineering reports", "export")
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
    
    # Professional System Status
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="section-header">📈 System Status</h3>', unsafe_allow_html=True)
        
        # Check data status with professional badges
        status_items = [
            ("ASME B18.2.1 Data", not df.empty, "engineering-badge"),
            ("ISO 4014 Data", not df_iso4014.empty, "technical-badge"),
            ("DIN-7991 Data", st.session_state.din7991_loaded, "material-badge"),
            ("ASME B18.3 Data", st.session_state.asme_b18_3_loaded, "grade-badge"),
            ("ME&CERT Data", not df_mechem.empty, "engineering-badge"),
            ("Thread Data", any(not load_thread_data(url).empty for url in thread_files.values()), "technical-badge"),
        ]
        
        for item_name, status, badge_class in status_items:
            if status:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0;">✅ {item_name} - Active</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0; background: #6c757d;">⚠️ {item_name} - Limited</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<h3 class="section-header">🕒 Engineering Features</h3>', unsafe_allow_html=True)
        
        features = [
            "🎯 Professional dimensional analysis",
            "🧪 Material science and chemistry", 
            "🔧 Grade specifications and standards",
            "📊 Technical data visualization",
            "🤖 AI-powered technical assistance",
            "📋 Professional reporting"
        ]
        
        for feature in features:
            st.markdown(f'<div style="padding: 0.5rem; border-left: 3px solid #3498db; margin: 0.2rem 0; background: var(--neutral-light);">• {feature}</div>', unsafe_allow_html=True)
        
        # Installation guide
        with st.expander("🔧 Install AI Dependencies"):
            st.code("""
pip install transformers sentence-transformers chromadb scikit-learn
pip install torch --index-url https://download.pytorch.org/whl/cpu
            """)
        
        # Show recent calculations if any
        show_calculation_history()
    
    # Professional Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #7f8c8d; padding: 2rem;">
        <p><strong>JSC Industries Professional Engineering Platform v4.0</strong></p>
        <p>Born to Perform • Engineered for Precision • Professional Grade</p>
    </div>
    """, unsafe_allow_html=True)

# ======================================================
# 🔹 ENHANCED CALCULATIONS SECTION WITH ALL PRODUCT TYPES
# ======================================================
def show_enhanced_calculations():
    st.markdown("""
    <div class="engineering-header">
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
            
            # Enhanced product options including threaded rod and stud
            if series == "Inch":
                product_options = ["Hex Bolt", "Heavy Hex Bolt", "Hex Screw", "Heavy Hex Screw", "Hexagon Socket Head Cap Screws", "Threaded Rod", "Stud", "Washer"]
                standard_options = ["ASME B1.1", "ASME B18.2.1", "ASME B18.3"]
            else:
                product_options = ["Hex Bolt", "Hexagon Socket Countersunk Head Cap Screw", "Hexagon Socket Head Cap Screws", "Threaded Rod", "Stud", "Nut", "Washer"]
                standard_options = ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine", "ISO 4014", "DIN-7991"]
            
            selected_product = st.selectbox("Product Type", product_options)
            selected_standard = st.selectbox("Applicable Standard", standard_options)
            
            # Diameter type selection
            diameter_type = st.radio("Diameter Type", ["Body Diameter", "Pitch Diameter"], 
                                   help="Select whether to use body diameter or pitch diameter for calculation")
        
        with col2:
            # Get size options based on standard
            size_options = []
            if selected_standard == "ISO 4014":
                df_source = df_iso4014
                size_options = sorted(df_source['Size'].dropna().unique()) if not df_iso4014.empty else []
            elif selected_standard == "DIN-7991":
                df_source = df_din7991
                size_options = sorted(df_source['Size'].dropna().unique()) if st.session_state.din7991_loaded else []
            elif selected_standard == "ASME B18.3":
                df_source = df_asme_b18_3
                size_options = sorted(df_source['Size'].dropna().unique()) if st.session_state.asme_b18_3_loaded else []
            elif selected_standard in thread_files:
                df_thread = get_thread_data(selected_standard)
                size_options = sorted(df_thread['Thread'].dropna().unique()) if not df_thread.empty else []
            elif selected_standard == "ASME B18.2.1":
                df_source = df
                size_options = sorted(df_source['Size'].dropna().unique()) if not df.empty else []
            
            selected_size = st.selectbox("Size Specification", size_options) if size_options else st.selectbox("Size Specification", ["No sizes available"])
            
            length_val = st.number_input("Length Value", min_value=0.1, value=10.0, step=0.1)
            length_unit = st.selectbox("Length Unit", ["mm", "inch", "meter", "ft"])
            
            # Class selection based on series
            if series == "Inch":
                class_options = ["1A", "2A", "3A"]
            else:
                class_options = ["6g", "6H", "4g", "4H", "8g", "8H"]
            
            selected_class = st.selectbox("Select Class", class_options)

        # Calculate button
        st.markdown("---")
        if st.button("🚀 Calculate Weight", use_container_width=True, key="calculate_weight"):
            diameter_mm = None
            diameter_source = ""
            
            # Auto-detect diameter based on diameter type selection
            if diameter_type == "Body Diameter":
                # Body diameter is always manual input
                st.info("Please enter Body Diameter manually:")
                manual_col1, manual_col2 = st.columns(2)
                with manual_col1:
                    body_dia = st.number_input("Enter Body Diameter", min_value=0.1, step=0.1, value=5.0, key="manual_dia")
                with manual_col2:
                    diameter_unit = st.selectbox("Diameter Unit", ["mm", "inch"], key="diameter_unit")
                diameter_mm = body_dia * 25.4 if diameter_unit == "inch" else body_dia
                diameter_source = f"Manual Body Diameter: {diameter_mm:.2f} mm"
                    
            else:  # Pitch Diameter
                # Get pitch diameter from thread data
                if selected_standard in thread_files and selected_size != "No sizes available":
                    df_thread = get_thread_data(selected_standard)
                    if not df_thread.empty:
                        thread_row = df_thread[df_thread["Thread"] == selected_size]
                        if not thread_row.empty and "Pitch Diameter (Min)" in thread_row.columns:
                            pitch_val = thread_row["Pitch Diameter (Min)"].values[0]
                            diameter_mm = pitch_val if series == "Metric" else pitch_val * 25.4
                            diameter_source = f"Pitch Diameter from {selected_standard}: {diameter_mm:.2f} mm"
                            st.info(diameter_source)
                
                # If pitch diameter not found, allow manual input
                if diameter_mm is None:
                    st.warning("Pitch diameter not found in database. Please enter manually:")
                    manual_col1, manual_col2 = st.columns(2)
                    with manual_col1:
                        pitch_dia = st.number_input("Enter Pitch Diameter", min_value=0.1, step=0.1, value=4.5, key="pitch_dia")
                    with manual_col2:
                        diameter_unit = st.selectbox("Diameter Unit", ["mm", "inch"], key="pitch_diameter_unit")
                    diameter_mm = pitch_dia * 25.4 if diameter_unit == "inch" else pitch_dia
                    diameter_source = f"Manual Pitch Diameter: {diameter_mm:.2f} mm"

            # Perform calculation
            if diameter_mm is not None and diameter_mm > 0:
                length_mm = convert_length_to_mm(length_val, length_unit)
                weight_kg = calculate_weight_enhanced(selected_product, diameter_mm, length_mm, 
                                                    diameter_type.lower().replace(" ", "_"))
                if weight_kg > 0:
                    st.success(f"✅ **Calculation Result:**")
                    st.metric("Estimated Weight", f"{weight_kg} Kg", f"Class: {selected_class}")
                    
                    # Detailed information
                    st.info(f"""
                    **Parameters Used:**
                    - Product: {selected_product}
                    - {diameter_source}
                    - Length: {length_mm:.2f} mm ({length_val} {length_unit})
                    - Standard: {selected_standard}
                    - Diameter Type: {diameter_type}
                    - Thread Class: {selected_class}
                    """)
                    
                    # Save to calculation history
                    calculation_data = {
                        'product': selected_product,
                        'size': selected_size,
                        'weight': weight_kg,
                        'diameter': diameter_mm,
                        'length': length_mm,
                        'standard': selected_standard,
                        'diameter_type': diameter_type,
                        'class': selected_class
                    }
                    save_calculation_history(calculation_data)
                else:
                    st.error("❌ Failed to calculate weight. Please check inputs.")
            else:
                st.error("❌ Please provide valid diameter information.")
        
        # Show calculation history
        show_calculation_history()
    
    with tab2:
        st.markdown("### Batch Weight Processor")
        st.info("📁 Upload a CSV/Excel file with columns: Product, Size, Length, Diameter (optional)")
        uploaded_file = st.file_uploader("Choose batch file", type=["csv", "xlsx"], key="batch_upload")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    batch_df = pd.read_excel(uploaded_file)
                else:
                    batch_df = pd.read_csv(uploaded_file)
                
                st.write("Preview of uploaded data:")
                st.dataframe(batch_df.head())
                
                if st.button("Process Batch", use_container_width=True, key="process_batch"):
                    with st.spinner("Processing batch data..."):
                        results_df = process_batch_data(uploaded_file)
                        if results_df is not None:
                            st.success(f"✅ Processed {len(results_df)} records successfully!")
                            st.dataframe(results_df)
                            
                            # Export batch results
                            st.markdown("### 📤 Export Batch Results")
                            export_col1, export_col2 = st.columns(2)
                            with export_col1:
                                batch_export_format = st.selectbox("Export Format", ["CSV", "Excel"], key="batch_export")
                            with export_col2:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("📥 Download Results", use_container_width=True, key="download_batch"):
                                    enhanced_export_data(results_df, batch_export_format)
                    
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    with tab3:
        st.markdown("### Calculation Analytics")
        st.info("📈 Visual insights and calculation history")
        
        if 'calculation_history' in st.session_state and st.session_state.calculation_history:
            # Convert history to dataframe for visualization
            history_df = pd.DataFrame(st.session_state.calculation_history)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Weight distribution
                if 'weight' in history_df.columns:
                    try:
                        fig_weights = px.histogram(history_df, x='weight', 
                                                 title='Weight Distribution History',
                                                 labels={'weight': 'Weight (kg)'})
                        st.plotly_chart(fig_weights, use_container_width=True)
                    except Exception as e:
                        st.info("Could not generate weight distribution chart")
            
            with col2:
                # Products frequency
                if 'product' in history_df.columns:
                    product_counts = history_df['product'].value_counts()
                    if len(product_counts) > 0:
                        fig_products = px.pie(values=product_counts.values, 
                                            names=product_counts.index,
                                            title='Products Calculated')
                        st.plotly_chart(fig_products, use_container_width=True)
        else:
            st.info("No calculation history available. Perform some calculations to see analytics here.")

# ======================================================
# 🔹 Help System
# ======================================================
def show_help_system():
    """Show contextual help system"""
    with st.sidebar:
        st.markdown("---")
        with st.expander("ℹ️ AI Capabilities Guide"):
            st.markdown("""
            **Advanced AI Features:**
            
            🧪 **Chemical Analysis**
            - "What is C% in Grade 5?"
            - "Chemical composition of stainless steel"
            - "Mn% content in different grades"
            
            🔧 **Mechanical Properties**  
            - "Tensile strength of Grade 8"
            - "Compare hardness of different materials"
            - "Yield strength specifications"
            
            📊 **Database Queries**
            - "Find all M12 bolts with specific properties"
            - "Show me materials with high corrosion resistance"
            - "List products by strength category"
            
            🔍 **Semantic Search**
            - Natural language understanding
            - Cross-database knowledge
            - Technical term recognition
            """)

# ======================================================
# 🔹 Section Dispatcher
# ======================================================
def show_section(title):
    if title == "📦 Product Database":
        show_enhanced_product_database()
    elif title == "🧮 Calculations":
        show_enhanced_calculations()
    elif title == "🤖 PiU (AI Assistant)":
        show_chat_interface()
    else:
        st.info(f"⚠️ Section {title} is coming soon!")
    
    st.markdown("---")
    if st.button("🏠 Back to Dashboard", use_container_width=True):
        st.session_state.selected_section = None

# ======================================================
# 🔹 Main Application
# ======================================================
st.markdown("**Professional Engineering Edition v4.0 ✅**")

# Add help system to sidebar
show_help_system()

# Add data quality indicators to sidebar
show_data_quality_indicators()

if st.session_state.selected_section is None:
    show_enhanced_home()
else:
    show_section(st.session_state.selected_section)

# ======================================================
# 🔹 Professional Footer
# ======================================================
st.markdown("""
    <hr>
    <div style='text-align: center; color: gray; padding: 2rem;'>
        <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
            <span class="engineering-badge">Professional</span>
            <span class="technical-badge">Precise</span>
            <span class="material-badge">Reliable</span>
            <span class="grade-badge">Engineering Grade</span>
        </div>
        <p><strong>© 2024 JSC Industries Pvt Ltd</strong> | Born to Perform • Engineered for Excellence</p>
        <p style="font-size: 0.8rem;">Professional Fastener Intelligence Platform v4.0 | Engineering Grade Design</p>
    </div>
""", unsafe_allow_html=True)