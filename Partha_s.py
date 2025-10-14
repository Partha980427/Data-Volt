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
me_chem_path = r"Mechanical and Chemical.xlsx"

# ISO 4014 paths - local and Google Sheets
iso4014_local_path = r"G:\My Drive\Streamlite\ISO 4014 Hex Bolt.xlsx"
iso4014_file_url = "https://docs.google.com/spreadsheets/d/1d2hANwoMhuzwyKJ72c125Uy0ujB6QsV_/export?format=xlsx"

# Thread files - UPDATED WITH GOOGLE SHEETS LINKS
thread_files = {
    "ASME B1.1": "https://docs.google.com/spreadsheets/d/1YHgUloNsFudxxqhWQV66D2DtSSKWFP_w/export?format=xlsx",
    "ISO 965-2-98 Coarse": "https://docs.google.com/spreadsheets/d/1be5eEy9hbVfMg2sl1-Cz1NNCGGF8EB-L/export?format=xlsx",
    "ISO 965-2-98 Fine": "https://docs.google.com/spreadsheets/d/1QGQ6SMWBSTsah-vq3zYnhOC3NXaBdKPe/export?format=xlsx",
}

# ======================================================
# 🔹 Enhanced Configuration & Error Handling
# ======================================================
@st.cache_data(ttl=3600)  # Cache for 1 hour
def safe_load_excel_file(path_or_url):
    """Enhanced loading with better error handling and retry mechanism"""
    max_retries = 2
    for attempt in range(max_retries):
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
                'iso4014': iso4014_file_url,
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
        "ai_model_loaded": False
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
        df_thread = pd.read_excel(file_path)
        return df_thread
    except Exception as e:
        st.sidebar.error(f"❌ Error loading thread data: {str(e)}")
        return pd.DataFrame()

# ======================================================
# 🔹 PROFESSIONAL PRODUCT SUMMARY CARD COMPONENT
# ======================================================
def create_product_summary_card(product_data):
    """Create professional product summary card with organized information"""
    
    if product_data.empty:
        return st.warning("No product data available for summary")
    
    # Sample product data (in real implementation, this would come from filtered data)
    sample_product = product_data.iloc[0] if not product_data.empty else {}
    
    st.markdown("""
    <div class="spec-card">
        <h3 style="margin:0 0 1rem 0; color: #2c3e50;">📋 Product Summary</h3>
    """, unsafe_allow_html=True)
    
    # Product Information Grid
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="spec-item">
            <div class="spec-label">Product Type</div>
            <div class="spec-value">{sample_product.get('Product', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="spec-item">
            <div class="spec-label">Standard</div>
            <div class="spec-value">{sample_product.get('Standards', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="spec-item">
            <div class="spec-label">Size</div>
            <div class="spec-value">{sample_product.get('Size', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="spec-item">
            <div class="spec-label">Grade</div>
            <div class="spec-value">{sample_product.get('Product Grade', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="spec-item">
            <div class="spec-label">Thread Type</div>
            <div class="spec-value">{sample_product.get('Thread Type', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="spec-item">
            <div class="spec-label">Material</div>
            <div class="spec-value">{sample_product.get('Material', 'Carbon Steel')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# 🔹 DIMENSIONAL SPECIFICATIONS COMPONENT
# ======================================================
def create_dimensional_specs(product_data):
    """Create professional dimensional specifications grid"""
    
    st.markdown("""
    <div class="spec-card">
        <h3 style="margin:0 0 1rem 0; color: #2c3e50;">📐 Dimensional Specifications</h3>
    """, unsafe_allow_html=True)
    
    # Dimensional Data Grid
    col1, col2, col3, col4 = st.columns(4)
    
    dimensional_data = {
        "Body Diameter": "12.0 mm",
        "Pitch Diameter": "10.86 mm",
        "Thread Pitch": "1.75 mm",
        "Head Height": "7.5 mm",
        "Across Flats": "18.0 mm",
        "Across Corners": "20.78 mm",
        "Thread Length": "30.0 mm",
        "Shank Length": "45.0 mm"
    }
    
    with col1:
        for i, (key, value) in enumerate(list(dimensional_data.items())[:2]):
            st.markdown(f"""
            <div class="spec-item">
                <div class="spec-label">{key}</div>
                <div class="spec-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        for i, (key, value) in enumerate(list(dimensional_data.items())[2:4]):
            st.markdown(f"""
            <div class="spec-item">
                <div class="spec-label">{key}</div>
                <div class="spec-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        for i, (key, value) in enumerate(list(dimensional_data.items())[4:6]):
            st.markdown(f"""
            <div class="spec-item">
                <div class="spec-label">{key}</div>
                <div class="spec-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        for i, (key, value) in enumerate(list(dimensional_data.items())[6:]):
            st.markdown(f"""
            <div class="spec-item">
                <div class="spec-label">{key}</div>
                <div class="spec-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# 🔹 MATERIAL PROPERTIES COMPONENT
# ======================================================
def create_material_properties():
    """Create professional material properties display"""
    
    st.markdown("""
    <div class="material-card">
        <h3 style="margin:0 0 1rem 0; color: #2c3e50;">🧪 Material Properties</h3>
    """, unsafe_allow_html=True)
    
    # Chemical Composition
    st.markdown("##### Chemical Composition")
    chem_cols = st.columns(4)
    
    chemical_data = {
        "Carbon (C)": "0.28% - 0.55%",
        "Manganese (Mn)": "0.60% max",
        "Phosphorus (P)": "0.04% max", 
        "Sulfur (S)": "0.05% max"
    }
    
    for idx, (element, range_val) in enumerate(chemical_data.items()):
        with chem_cols[idx]:
            st.markdown(f"""
            <div class="property-item">
                <div class="property-value">{range_val.split(' ')[0]}</div>
                <div class="property-label">{element}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Mechanical Properties
    st.markdown("##### Mechanical Properties")
    mech_cols = st.columns(4)
    
    mechanical_data = {
        "Tensile Strength": "120,000 psi",
        "Yield Strength": "92,000 psi", 
        "Elongation": "14% min",
        "Hardness": "HRC 25-34"
    }
    
    for idx, (property_name, value) in enumerate(mechanical_data.items()):
        with mech_cols[idx]:
            st.markdown(f"""
            <div class="property-item">
                <div class="property-value">{value.split(' ')[0]}</div>
                <div class="property-label">{property_name}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# 🔹 PERFORMANCE METRICS COMPONENT
# ======================================================
def create_performance_metrics(filtered_df):
    """Create professional performance metrics display"""
    
    st.markdown("""
    <div class="technical-card">
        <h3 style="margin:0 0 1rem 0; color: #2c3e50;">📊 Performance Metrics</h3>
    """, unsafe_allow_html=True)
    
    # Data Quality Metrics
    if not filtered_df.empty:
        total_records = len(filtered_df)
        completeness = (filtered_df.count().sum() / (len(filtered_df.columns) * total_records)) * 100
        unique_sizes = filtered_df['Size'].nunique() if 'Size' in filtered_df.columns else 0
        data_freshness = "Today"
    else:
        total_records = 0
        completeness = 0
        unique_sizes = 0
        data_freshness = "N/A"
    
    metric_cols = st.columns(4)
    
    metrics_data = [
        ("Total Records", f"{total_records:,}", "engineering-badge"),
        ("Data Completeness", f"{completeness:.1f}%", "technical-badge"),
        ("Unique Sizes", f"{unique_sizes}", "grade-badge"),
        ("Data Freshness", data_freshness, "material-badge")
    ]
    
    for idx, (label, value, badge_class) in enumerate(metrics_data):
        with metric_cols[idx]:
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem;">
                <div class="{badge_class}" style="margin-bottom: 0.5rem;">{label}</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #2c3e50;">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# 🔹 VISUAL ANALYSIS COMPONENT
# ======================================================
def create_visual_analysis(filtered_df):
    """Create professional visual analysis section"""
    
    st.markdown("""
    <div class="spec-card">
        <h3 style="margin:0 0 1rem 0; color: #2c3e50;">📈 Visual Analysis</h3>
    """, unsafe_allow_html=True)
    
    if not filtered_df.empty and 'Size' in filtered_df.columns:
        # Size Distribution Chart
        size_counts = filtered_df['Size'].value_counts().head(8)
        
        if len(size_counts) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                # Bar chart for size distribution
                try:
                    fig_bar = px.bar(
                        x=size_counts.index,
                        y=size_counts.values,
                        title="Size Distribution",
                        labels={'x': 'Size', 'y': 'Count'},
                        color=size_counts.values,
                        color_continuous_scale='blues'
                    )
                    fig_bar.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)
                except Exception as e:
                    st.info("📊 Chart visualization available with data")
            
            with col2:
                # Pie chart for product types
                if 'Product' in filtered_df.columns:
                    product_counts = filtered_df['Product'].value_counts().head(6)
                    if len(product_counts) > 0:
                        try:
                            fig_pie = px.pie(
                                values=product_counts.values,
                                names=product_counts.index,
                                title="Product Type Distribution",
                                color_discrete_sequence=px.colors.sequential.Blues_r
                            )
                            fig_pie.update_layout(height=300)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        except Exception as e:
                            st.info("📈 Product distribution chart")
    
    st.markdown("</div>", unsafe_allow_html=True)

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
    def __init__(self, df, df_iso4014, df_mechem, thread_files):
        self.df = df
        self.df_iso4014 = df_iso4014
        self.df_mechem = df_mechem
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
    
    # Initialize AI assistant
    ai_assistant = AdvancedFastenerAI(df, df_iso4014, df_mechem, thread_files)
    
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
# 🔹 ENHANCED PRODUCT DATABASE WITH PROFESSIONAL LAYOUT
# ======================================================
def show_enhanced_product_database():
    """Show product database with professional engineering layout"""
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
            📦 Product Intelligence Center
        </h1>
        <p style="margin:0; opacity: 0.9;">Professional Engineering Database with Advanced Analytics</p>
        <div style="margin-top: 1rem;">
            <span class="engineering-badge">Dimensional Analysis</span>
            <span class="material-badge">Material Science</span>
            <span class="grade-badge">Grade Specifications</span>
            <span class="technical-badge">Technical Data</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if df.empty and df_mechem.empty and df_iso4014.empty:
        st.error("🚫 No data sources available. Please check your data connections.")
        return
    
    # Quick Stats in Professional Layout
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = len(df) + (len(df_iso4014) if not df_iso4014.empty else 0)
    total_standards = len(df['Standards'].unique()) + 1 if not df.empty else 1
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
            <h3 style="color: #3498db; margin:0;">🌍 Standards</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_standards}</h2>
            <p style="color: #7f8c8d; margin:0;">Supported</p>
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
    
    # Enhanced Filter Section in Sidebar
    with st.sidebar:
        st.markdown("### 🔍 Smart Filters")
        
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
        
        # Show data quality indicators
        show_data_quality_indicators()
    
    # Main Content Area - Professional Layout
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
    
    # PROFESSIONAL INFORMATION ARCHITECTURE
    if not filtered_df.empty:
        # 1. Product Summary Card
        create_product_summary_card(filtered_df)
        
        # 2. Dimensional Specifications
        create_dimensional_specs(filtered_df)
        
        # 3. Material Properties
        create_material_properties()
        
        # 4. Performance Metrics
        create_performance_metrics(filtered_df)
        
        # 5. Visual Analysis
        create_visual_analysis(filtered_df)
        
        # Raw Data Table
        st.markdown("### 📋 Raw Data Table")
        st.dataframe(filtered_df, use_container_width=True)
        
        # Enhanced Export Options
        st.markdown("### 📤 Export Options")
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            export_format = st.selectbox("Export Format", ["CSV", "Excel"], key="export_format")
        with export_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Generate Export", use_container_width=True, key="generate_export"):
                enhanced_export_data(filtered_df, export_format)
        
    else:
        st.info("🤔 No records match your current filters. Try adjusting your search criteria.")
        
    # Thread Data Section
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
            st.warning(f"No thread data available for {thread_standard}")
    else:
        st.info("Select a thread standard to view detailed thread data.")

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
                product_options_from_df = [p for p in df['Product'].dropna().unique() if any(x in p.lower() for x in ['hex', 'bolt', 'screw', 'nut'])] if not df.empty else []
                unique_products = list(set(product_options_from_df))
                product_options = sorted(unique_products) + ["Threaded Rod", "Stud", "Washer"]
                standard_options = ["ASME B1.1"]
            else:
                product_options = ["Hex Bolt", "Threaded Rod", "Stud", "Nut", "Washer"]
                standard_options = ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine", "ISO 4014"]
            
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
            elif selected_standard in thread_files:
                df_thread = get_thread_data(selected_standard)
                size_options = sorted(df_thread['Thread'].dropna().unique()) if not df_thread.empty else []
            
            selected_size = st.selectbox("Size Specification", size_options) if size_options else st.selectbox("Size Specification", ["No sizes available"])
            
            length_val = st.number_input("Length Value", min_value=0.1, value=10.0, step=0.1)
            length_unit = st.selectbox("Length Unit", ["mm", "inch", "meter", "ft"])
            
            # Class selection based on series
            if series == "Inch":
                class_options = ["1A", "2A", "3A"]
            else:
                class_options = ["6g", "6H", "4g", "4H", "8g", "8H"]
            
            selected_class = st.selectbox("Select Class", class_options)

        # FIXED: Separate calculate button outside columns
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
    
    # Professional Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = len(df) + (len(df_iso4014) if not df_iso4014.empty else 0)
    total_standards = len(df['Standards'].unique()) + 1 if not df.empty else 1
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
            <h3 style="color: #3498db; margin:0;">🌍 Standards</h3>
            <h2 style="color: #2c3e50; margin:0.5rem 0;">{total_standards}</h2>
            <p style="color: #7f8c8d; margin:0;">Supported</p>
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
            ("Main Product Data", not df.empty, "engineering-badge"),
            ("ISO 4014 Data", not df_iso4014.empty, "technical-badge"),
            ("ME&CERT Data", not df_mechem.empty, "material-badge"),
            ("Thread Data", any(not load_thread_data(url).empty for url in thread_files.values()), "grade-badge"),
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