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
import threading
from functools import lru_cache
import concurrent.futures
from typing import Dict, List, Optional, Tuple
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
# HIGH-PERFORMANCE CACHING AND PRELOADING
# ======================================================

@st.cache_data(ttl=3600, show_spinner=False, max_entries=1000)
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

# ======================================================
# HIGH-PERFORMANCE THREAD DATA MANAGER
# ======================================================

class ThreadDataManager:
    """High-performance thread data manager with intelligent caching"""
    
    def __init__(self):
        self._cache = {}
        self._size_cache = {}
        self._class_cache = {}
        self._lock = threading.RLock()
    
    @st.cache_data(ttl=7200, show_spinner=False)
    def _load_thread_data(_self, standard_name, file_path):
        """Internal cached data loader"""
        try:
            df_thread = safe_load_excel_file_enhanced(file_path)
            if df_thread.empty:
                return pd.DataFrame()
            
            # Clean column names
            df_thread.columns = [str(col).strip() for col in df_thread.columns]
            
            # Find thread size column
            thread_col = None
            for col in df_thread.columns:
                col_lower = str(col).lower()
                if any(x in col_lower for x in ['thread', 'size', 'nominal', 'major']):
                    thread_col = col
                    break
            
            # Find class column
            class_col = None
            for col in df_thread.columns:
                col_lower = str(col).lower()
                if any(x in col_lower for x in ['class', 'tolerance']):
                    class_col = col
                    break
            
            # Standardize column names
            if thread_col:
                df_thread = df_thread.rename(columns={thread_col: 'Thread'})
            if class_col:
                df_thread = df_thread.rename(columns={class_col: 'Class'})
            
            # Clean data
            if 'Thread' in df_thread.columns:
                df_thread['Thread'] = df_thread['Thread'].astype(str).str.strip()
                df_thread = df_thread[~df_thread['Thread'].isin(['nan', ''])]
            
            if 'Class' in df_thread.columns:
                df_thread['Class'] = df_thread['Class'].astype(str).str.strip()
                df_thread = df_thread[~df_thread['Class'].isin(['nan', ''])]
            
            df_thread['Standard'] = standard_name
            return df_thread
            
        except Exception as e:
            st.error(f"Error loading thread data for {standard_name}: {str(e)}")
            return pd.DataFrame()
    
    def get_thread_data(self, standard_name, file_path):
        """Get thread data with intelligent caching"""
        with self._lock:
            cache_key = f"{standard_name}_{file_path}"
            if cache_key not in self._cache:
                self._cache[cache_key] = self._load_thread_data(standard_name, file_path)
            return self._cache[cache_key].copy()
    
    def get_thread_sizes(self, standard_name, file_path):
        """Get thread sizes with caching"""
        with self._lock:
            cache_key = f"sizes_{standard_name}"
            if cache_key not in self._size_cache:
                df_thread = self.get_thread_data(standard_name, file_path)
                if df_thread.empty or 'Thread' not in df_thread.columns:
                    self._size_cache[cache_key] = ["All"]
                else:
                    unique_sizes = df_thread['Thread'].dropna().unique()
                    unique_sizes = [str(size).strip() for size in unique_sizes if str(size).strip() != '']
                    sorted_sizes = safe_sort_sizes_optimized(unique_sizes)
                    self._size_cache[cache_key] = ["All"] + sorted_sizes
            return self._size_cache[cache_key]
    
    def get_thread_classes(self, standard_name, file_path):
        """Get thread classes with caching"""
        with self._lock:
            cache_key = f"classes_{standard_name}"
            if cache_key not in self._class_cache:
                df_thread = self.get_thread_data(standard_name, file_path)
                if df_thread.empty or 'Class' not in df_thread.columns:
                    self._class_cache[cache_key] = ["All"]
                else:
                    unique_classes = df_thread['Class'].dropna().unique()
                    unique_classes = [str(cls).strip() for cls in unique_classes if str(cls).strip() != '']
                    sorted_classes = sorted(unique_classes)
                    self._class_cache[cache_key] = ["All"] + sorted_classes
            return self._class_cache[cache_key]
    
    def get_pitch_diameter_min(self, standard_name, file_path, thread_size, tolerance_class):
        """Get minimum pitch diameter for inch series with tolerance class"""
        try:
            df_thread = self.get_thread_data(standard_name, file_path)
            if df_thread.empty:
                return None
            
            # Filter by thread size and tolerance class
            filtered_df = df_thread[
                (df_thread['Thread'].astype(str).str.strip() == str(thread_size).strip()) &
                (df_thread['Class'].astype(str).str.strip() == str(tolerance_class).strip())
            ]
            
            if filtered_df.empty:
                return None
            
            # Look for pitch diameter columns - prioritize minimum values
            pitch_cols = []
            for col in filtered_df.columns:
                col_lower = str(col).lower()
                if 'pitch' in col_lower and 'diameter' in col_lower:
                    if 'min' in col_lower:
                        pitch_cols.insert(0, col)  # Prioritize min columns
                    else:
                        pitch_cols.append(col)
            
            for col in pitch_cols:
                pitch_val = filtered_df[col].iloc[0]
                if pd.notna(pitch_val):
                    return float(pitch_val)
            
            return None
            
        except Exception as e:
            st.error(f"Error getting pitch diameter: {str(e)}")
            return None

# Initialize thread data manager
thread_manager = ThreadDataManager()

# ======================================================
# HIGH-PERFORMANCE WEIGHT CALCULATION ENGINE
# ======================================================

class FastWeightCalculator:
    """High-performance weight calculation engine with intelligent caching"""
    
    def __init__(self):
        self._pitch_cache = {}
        self._head_height_cache = {}
        self._width_flats_cache = {}
        self._lock = threading.RLock()
        self._precomputed_volumes = {}
        
        # Precompute common values
        self._density = 0.00785  # g/mm³
        self._sqrt_3 = math.sqrt(3)
        self._pi = math.pi
        
        # Metric thread pitch lookup table (major_dia: pitch)
        self._metric_pitches = {
            1.0: 0.25, 1.2: 0.25, 1.4: 0.3, 1.6: 0.35, 1.8: 0.35,
            2.0: 0.4, 2.2: 0.45, 2.5: 0.45, 3.0: 0.5, 3.5: 0.6,
            4.0: 0.7, 4.5: 0.75, 5.0: 0.8, 6.0: 1.0, 7.0: 1.0,
            8.0: 1.25, 9.0: 1.25, 10.0: 1.5, 11.0: 1.5, 12.0: 1.75,
            14.0: 2.0, 16.0: 2.0, 18.0: 2.5, 20.0: 2.5, 22.0: 2.5,
            24.0: 3.0, 27.0: 3.0, 30.0: 3.5, 33.0: 3.5, 36.0: 4.0
        }
    
    def _get_metric_pitch(self, major_dia: float) -> float:
        """Fast metric pitch lookup with fallback"""
        # Exact match
        if major_dia in self._metric_pitches:
            return self._metric_pitches[major_dia]
        
        # Find closest diameter
        closest_dia = min(self._metric_pitches.keys(), key=lambda x: abs(x - major_dia))
        return self._metric_pitches[closest_dia]
    
    @lru_cache(maxsize=1000)
    def _calculate_head_volume_cached(self, product_type: str, diameter_mm: float, 
                                    head_height: float, width_flats: float) -> float:
        """Cached head volume calculation"""
        product_lower = product_type.lower()
        
        try:
            if any(x in product_lower for x in ["hex bolt", "hex cap screw", "heavy hex", "nut"]):
                # Hex head volume formula: V = (3√3/2) * s² * h
                side_length = width_flats / self._sqrt_3
                return (3 * self._sqrt_3 / 2) * (side_length ** 2) * head_height
            
            elif "socket head" in product_lower:
                # Cylindrical head
                head_dia = 1.5 * diameter_mm
                return self._pi * (head_dia/2)**2 * head_height
            
            elif "button head" in product_lower:
                # Spherical segment
                head_dia = 1.5 * diameter_mm
                head_height_val = 0.5 * diameter_mm
                return (self._pi * head_height_val / 6) * (3 * (head_dia/2)**2 + head_height_val**2)
            
            elif "flat head" in product_lower or "countersunk" in product_lower:
                # Conical head
                head_dia = 2.0 * diameter_mm
                head_height_val = 0.5 * diameter_mm
                R = head_dia / 2
                r = diameter_mm / 2
                return (self._pi * head_height_val * (R**2 + R*r + r**2)) / 3
            
            else:
                # Default hex head
                s = 1.5 * diameter_mm
                h = 0.625 * diameter_mm
                return (3 * self._sqrt_3 / 2) * (s ** 2) * h
                
        except Exception:
            return 0.0
    
    def _get_pitch_diameter_fast(self, standard: str, thread_size: str, thread_class: str = None) -> Optional[float]:
        """Fast pitch diameter lookup with caching - ENHANCED FOR INCH SERIES"""
        cache_key = f"{standard}_{thread_size}_{thread_class}"
        
        with self._lock:
            if cache_key in self._pitch_cache:
                return self._pitch_cache[cache_key]
            
            # For inch series with tolerance class, get minimum pitch diameter
            if standard == "ASME B1.1" and thread_class:
                pitch_dia_min = thread_manager.get_pitch_diameter_min(standard, thread_files[standard], thread_size, thread_class)
                if pitch_dia_min is not None:
                    # Convert inch to mm for inch series
                    pitch_dia_mm = pitch_dia_min * 25.4
                    self._pitch_cache[cache_key] = pitch_dia_mm
                    return pitch_dia_mm
            
            # Try database lookup first for other standards
            pitch_dia = self._get_pitch_diameter_from_db(standard, thread_size, thread_class)
            if pitch_dia is not None:
                # Convert to mm if needed
                if standard == "ASME B1.1" and pitch_dia < 10:  # Assume it's in inches if small value
                    pitch_dia *= 25.4
                self._pitch_cache[cache_key] = pitch_dia
                return pitch_dia
            
            # Fallback to estimation for metric threads
            if thread_size and thread_size.startswith('M'):
                try:
                    major_dia = float(thread_size[1:])
                    pitch = self._get_metric_pitch(major_dia)
                    pitch_dia_est = major_dia - 0.6495 * pitch
                    self._pitch_cache[cache_key] = pitch_dia_est
                    return pitch_dia_est
                except (ValueError, TypeError):
                    pass
            
            self._pitch_cache[cache_key] = None
            return None
    
    def _get_pitch_diameter_from_db(self, standard: str, thread_size: str, thread_class: str = None) -> Optional[float]:
        """Database lookup for pitch diameter"""
        try:
            if standard in thread_files:
                df_thread = thread_manager.get_thread_data(standard, thread_files[standard])
                if df_thread.empty:
                    return None
                
                # Filter by thread size and class
                temp_df = df_thread.copy()
                if 'Thread' in temp_df.columns and thread_size and thread_size != "All":
                    temp_df = temp_df[temp_df['Thread'].astype(str).str.strip() == str(thread_size).strip()]
                
                if 'Class' in temp_df.columns and thread_class and thread_class != "All":
                    temp_df = temp_df[
                        temp_df['Class'].astype(str).str.strip().str.upper() == 
                        str(thread_class).strip().upper()
                    ]
                
                if temp_df.empty:
                    return None
                
                # Look for pitch diameter columns
                for col in temp_df.columns:
                    col_lower = str(col).lower()
                    if 'pitch' in col_lower and 'diameter' in col_lower:
                        pitch_val = temp_df[col].iloc[0]
                        if pd.notna(pitch_val):
                            return float(pitch_val)
                
            return None
        except Exception:
            return None
    
    def _get_head_dimensions_fast(self, standard: str, product: str, size: str) -> Tuple[float, float]:
        """Fast head dimension lookup with caching"""
        cache_key = f"{standard}_{product}_{size}"
        
        with self._lock:
            if cache_key in self._head_height_cache and cache_key in self._width_flats_cache:
                return self._head_height_cache[cache_key], self._width_flats_cache[cache_key]
            
            head_height, width_flats = self._get_head_dimensions_from_db(standard, product, size)
            
            # Cache the results
            self._head_height_cache[cache_key] = head_height
            self._width_flats_cache[cache_key] = width_flats
            
            return head_height, width_flats
    
    def _get_head_dimensions_from_db(self, standard: str, product: str, size: str) -> Tuple[float, float]:
        """Database lookup for head dimensions"""
        default_head_height = 0.667
        default_width_flats = 1.5
        
        try:
            df_source = None
            if standard == "ASME B18.2.1" and not df.empty:
                df_source = df
            elif standard == "ISO 4014" and not df_iso4014.empty:
                df_source = df_iso4014
            elif standard == "DIN-7991" and st.session_state.din7991_loaded:
                df_source = df_din7991
            elif standard == "ASME B18.3" and st.session_state.asme_b18_3_loaded:
                df_source = df_asme_b18_3
            
            if df_source is None:
                return default_head_height, default_width_flats
            
            # Filter dataframe
            temp_df = df_source.copy()
            if 'Product' in temp_df.columns and product != "All":
                temp_df = temp_df[temp_df['Product'] == product]
            if 'Size' in temp_df.columns and size != "All":
                temp_df = temp_df[temp_df['Size'].astype(str).str.strip() == str(size).strip()]
            
            if temp_df.empty:
                return default_head_height, default_width_flats
            
            # Look for head height
            head_height = default_head_height
            for col in temp_df.columns:
                col_lower = str(col).lower()
                if 'head' in col_lower and 'height' in col_lower:
                    head_val = temp_df[col].iloc[0]
                    if pd.notna(head_val):
                        head_height = float(head_val)
                        break
            
            # Look for width across flats
            width_flats = default_width_flats
            for col in temp_df.columns:
                col_lower = str(col).lower()
                if 'width' in col_lower and 'across' in col_lower and 'flats' in col_lower:
                    width_val = temp_df[col].iloc[0]
                    if pd.notna(width_val):
                        width_flats = float(width_val)
                        break
            
            return head_height, width_flats
            
        except Exception:
            return default_head_height, default_width_flats
    
    def calculate_weight_fast(self, product: str, diameter_mm: float, length_mm: float, 
                            diameter_type: str = "body", thread_standard: str = None, 
                            thread_size: str = None, thread_class: str = None,
                            dimensional_standard: str = None, dimensional_product: str = None, 
                            dimensional_size: str = None) -> float:
        """HIGH-PERFORMANCE weight calculation"""
        
        if diameter_mm <= 0 or length_mm <= 0:
            return 0.0
        
        try:
            # Calculate shank volume
            V_shank = self._pi * (diameter_mm / 2) ** 2 * length_mm
            
            # Handle threaded products
            product_lower = product.lower()
            if diameter_type == "pitch_diameter" and thread_standard and thread_size:
                pitch_dia = self._get_pitch_diameter_fast(thread_standard, thread_size, thread_class)
                if pitch_dia:
                    diameter_mm = pitch_dia
            
            # Thread volume reduction for threaded products
            thread_reduction = 1.0
            if any(x in product_lower for x in ["threaded rod", "stud"]):
                if diameter_mm <= 3:
                    thread_reduction = 0.85
                elif diameter_mm <= 10:
                    thread_reduction = 0.80
                else:
                    thread_reduction = 0.75
                V_shank *= thread_reduction
            
            # Calculate head volume
            head_volume = 0.0
            if not any(x in product_lower for x in ["threaded rod", "stud"]):
                if dimensional_standard and dimensional_product and dimensional_size:
                    head_height, width_flats = self._get_head_dimensions_fast(
                        dimensional_standard, dimensional_product, dimensional_size
                    )
                else:
                    # Use defaults based on product type
                    if "heavy" in product_lower:
                        head_height, width_flats = 0.667, 1.5
                    else:
                        head_height, width_flats = 0.625, 1.5
                
                head_volume = self._calculate_head_volume_cached(
                    product, diameter_mm, head_height, width_flats
                )
            
            # Calculate total weight
            total_volume = V_shank + head_volume
            weight_grams = total_volume * self._density
            weight_kg = weight_grams / 1000
            
            return round(weight_kg, 4)
            
        except Exception as e:
            if st.session_state.debug_mode:
                st.error(f"Error in fast weight calculation: {str(e)}")
            return 0.0

# Initialize fast weight calculator
fast_calculator = FastWeightCalculator()

# ======================================================
# ENHANCED CONFIGURATION & ERROR HANDLING
# ======================================================

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
        "performance_mode": True,
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
        # Calculator session state - NEW STRUCTURE
        "calc_product": "Hex Bolt",
        "calc_series": "Inch",
        "calc_dimensional_standard": "ASME B18.2.1",
        "calc_size": "All",
        "calc_diameter_type": "Body Diameter",
        "calc_thread_standard": "ASME B1.1",
        "calc_tolerance_class": "2A",
        "calc_length_unit": "mm",
        "calc_length": 50.0,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    load_config()
    save_user_preferences()

# ======================================================
# OPTIMIZED DATA LOADING AND PROCESSING
# ======================================================

@st.cache_data(ttl=3600)
def load_all_data_sources():
    """Load all data sources with optimized caching"""
    data_sources = {}
    
    # Load main data
    data_sources['df'] = safe_load_excel_file_enhanced(url) if url else safe_load_excel_file_enhanced(local_excel_path)
    
    # Load Mechanical and Chemical data
    data_sources['df_mechem'] = safe_load_excel_file_enhanced(me_chem_google_url)
    if data_sources['df_mechem'].empty:
        data_sources['df_mechem'] = safe_load_excel_file_enhanced(me_chem_path)
    
    # Load ISO 4014 data
    data_sources['df_iso4014'] = safe_load_excel_file_enhanced(iso4014_file_url)
    if data_sources['df_iso4014'].empty:
        data_sources['df_iso4014'] = safe_load_excel_file_enhanced(iso4014_local_path)
    
    # Load DIN-7991 data
    data_sources['df_din7991'] = safe_load_excel_file_enhanced(din7991_file_url)
    if data_sources['df_din7991'].empty:
        data_sources['df_din7991'] = safe_load_excel_file_enhanced(din7991_local_path)
    
    # Load ASME B18.3 data
    data_sources['df_asme_b18_3'] = safe_load_excel_file_enhanced(asme_b18_3_file_url)
    if data_sources['df_asme_b18_3'].empty:
        data_sources['df_asme_b18_3'] = safe_load_excel_file_enhanced(asme_b18_3_local_path)
    
    return data_sources

# Initialize data sources
data_sources = load_all_data_sources()
df = data_sources['df']
df_mechem = data_sources['df_mechem']
df_iso4014 = data_sources['df_iso4014']
df_din7991 = data_sources['df_din7991']
df_asme_b18_3 = data_sources['df_asme_b18_3']

# ======================================================
# OPTIMIZED DATA PROCESSING FUNCTIONS
# ======================================================

@st.cache_data(ttl=3600)
def process_standard_data_optimized():
    """Optimized standard data processing"""
    standard_products = {}
    standard_series = {}
    
    # Process ASME B18.2.1
    if not df.empty:
        if 'Product' in df.columns:
            asme_products = df['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in asme_products if p and str(p).strip() != '']
            standard_products['ASME B18.2.1'] = ["All"] + sorted(cleaned_products)
        else:
            standard_products['ASME B18.2.1'] = ["All", "Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screws", "Heavy Hex Screws"]
        standard_series['ASME B18.2.1'] = "Inch"
    
    # Process ASME B18.3 Data
    if not df_asme_b18_3.empty:
        if 'Product' in df_asme_b18_3.columns:
            asme_b18_3_products = df_asme_b18_3['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in asme_b18_3_products if p and str(p).strip() != '']
            standard_products['ASME B18.3'] = ["All"] + sorted(cleaned_products)
        else:
            standard_products['ASME B18.3'] = ["All", "Hexagon Socket Head Cap Screws"]
        standard_series['ASME B18.3'] = "Inch"
    
    # Process DIN-7991 Data
    if not df_din7991.empty:
        if 'Product' in df_din7991.columns:
            din_products = df_din7991['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in din_products if p and str(p).strip() != '']
            standard_products['DIN-7991'] = ["All"] + sorted(cleaned_products)
        else:
            standard_products['DIN-7991'] = ["All", "Hexagon Socket Countersunk Head Cap Screw"]
        standard_series['DIN-7991'] = "Metric"
    
    # Process ISO 4014 Data
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
standard_products, standard_series = process_standard_data_optimized()

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

@st.cache_data(ttl=3600)
def process_mechanical_chemical_data_optimized():
    """Optimized mechanical & chemical data processing"""
    if df_mechem.empty:
        return [], []
    
    try:
        me_chem_columns = df_mechem.columns.tolist()
        
        # Find property class columns efficiently
        property_class_cols = []
        possible_class_cols = ['Grade', 'Class', 'Property Class', 'Material Grade', 'Type', 'Designation', 'Material']
        
        for col in me_chem_columns:
            col_lower = str(col).lower()
            for possible in possible_class_cols:
                if possible.lower() in col_lower:
                    property_class_cols.append(col)
                    break
        
        # Collect unique property classes
        all_property_classes = set()
        for prop_col in property_class_cols:
            if prop_col in df_mechem.columns:
                unique_classes = df_mechem[prop_col].dropna().unique()
                for cls in unique_classes:
                    if pd.notna(cls) and str(cls).strip() != '':
                        all_property_classes.add(str(cls).strip())
        
        property_classes = sorted(list(all_property_classes))
        
        st.session_state.me_chem_columns = me_chem_columns
        st.session_state.property_classes = property_classes
        
        return me_chem_columns, property_classes
        
    except Exception as e:
        st.error(f"Error processing Mechanical & Chemical data: {str(e)}")
        return [], []

# Initialize Mechanical & Chemical data processing
me_chem_columns, property_classes = process_mechanical_chemical_data_optimized()

# ======================================================
# OPTIMIZED UTILITY FUNCTIONS
# ======================================================

@lru_cache(maxsize=1000)
def size_to_float_cached(size_str: str) -> float:
    """Cached size conversion"""
    try:
        if not size_str or not isinstance(size_str, str):
            return 0.0
        
        size_str = size_str.strip()
        if not size_str:
            return 0.0
        
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
        
    except Exception:
        return 0.0

def safe_sort_sizes_optimized(size_list):
    """Optimized size sorting"""
    if not size_list:
        return []
    
    try:
        return sorted(size_list, key=lambda x: (size_to_float_cached(x), str(x)))
    except:
        try:
            return sorted(size_list, key=str)
        except:
            return list(size_list)

def convert_length_to_mm_fast(length_val, unit):
    """Fast length conversion"""
    try:
        length_val = float(length_val)
        unit = unit.lower()
        if unit == "inch":
            return length_val * 25.4
        elif unit == "meter":
            return length_val * 1000
        elif unit == "ft":
            return length_val * 304.8
        return length_val
    except (ValueError, TypeError):
        return 0.0

def get_safe_size_options_optimized(temp_df):
    """Optimized size options retrieval"""
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
            sorted_sizes = safe_sort_sizes_optimized(unique_sizes)
            size_options.extend(sorted_sizes)
    except Exception as e:
        if st.session_state.debug_mode:
            st.warning(f"Size processing warning: {str(e)}")
        try:
            unique_sizes = temp_df['Size'].dropna().unique()
            unique_sizes = [str(size) for size in unique_sizes if str(size).strip() != '']
            size_options.extend(list(unique_sizes))
        except:
            pass
    
    return size_options

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
    
    .performance-badge {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
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
    
    .performance-indicator {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: 600;
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
# ENHANCED SINGLE ITEM CALCULATOR WITH NEW UI ORDER
# ======================================================

def get_available_products():
    """Get all available products from all standards"""
    all_products = set()
    for standard_products_list in st.session_state.available_products.values():
        all_products.update(standard_products_list)
    return ["All"] + sorted([p for p in all_products if p != "All"])

def get_dimensional_standards_for_product_series(product, series):
    """Get dimensional standards based on product and series"""
    standards = ["All"]
    
    if product.lower() in ["threaded rod", "stud"]:
        return ["Not Required"]
    
    if series == "Inch":
        if product.lower() in ["hex bolt", "heavy hex bolt", "hex cap screws", "heavy hex screws"]:
            standards.extend(["ASME B18.2.1"])
        elif "socket" in product.lower():
            standards.extend(["ASME B18.3"])
    elif series == "Metric":
        if product.lower() in ["hex bolt"]:
            standards.extend(["ISO 4014"])
        elif "socket" in product.lower():
            standards.extend(["DIN-7991"])
    
    return standards

def get_thread_standards_for_series(series):
    """Get thread standards based on series"""
    if series == "Inch":
        return ["ASME B1.1"]
    elif series == "Metric":
        return ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
    return []

def get_size_options_for_product_standard(product, standard, series):
    """Get size options based on product, standard and series"""
    if product.lower() in ["threaded rod", "stud"]:
        # For threaded rod and stud, get sizes from thread standards
        thread_standards = get_thread_standards_for_series(series)
        all_sizes = set()
        for thread_std in thread_standards:
            sizes = thread_manager.get_thread_sizes(thread_std, thread_files[thread_std])
            all_sizes.update(sizes)
        return ["All"] + sorted([s for s in all_sizes if s != "All"])
    
    # For other products, get from dimensional standards
    if standard == "ASME B18.2.1" and not df.empty:
        temp_df = df.copy()
        if product != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product]
        return get_safe_size_options_optimized(temp_df)
    elif standard == "ISO 4014" and not df_iso4014.empty:
        temp_df = df_iso4014.copy()
        if product != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product]
        return get_safe_size_options_optimized(temp_df)
    elif standard == "DIN-7991" and st.session_state.din7991_loaded:
        temp_df = df_din7991.copy()
        if product != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product]
        return get_safe_size_options_optimized(temp_df)
    elif standard == "ASME B18.3" and st.session_state.asme_b18_3_loaded:
        temp_df = df_asme_b18_3.copy()
        if product != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product]
        return get_safe_size_options_optimized(temp_df)
    
    return ["All"]

def get_tolerance_classes_for_standard(standard, series):
    """Get tolerance classes based on standard and series"""
    if series == "Inch" and standard == "ASME B1.1":
        return ["1A", "2A", "3A"]
    elif series == "Metric":
        return ["6g", "6H"]  # Common metric tolerance classes
    return []

def get_body_diameter_from_db(standard, product, size):
    """Get body diameter from dimensional database"""
    try:
        df_source = None
        if standard == "ASME B18.2.1" and not df.empty:
            df_source = df
        elif standard == "ISO 4014" and not df_iso4014.empty:
            df_source = df_iso4014
        elif standard == "DIN-7991" and st.session_state.din7991_loaded:
            df_source = df_din7991
        elif standard == "ASME B18.3" and st.session_state.asme_b18_3_loaded:
            df_source = df_asme_b18_3
        
        if df_source is None:
            return None
        
        # Filter dataframe
        temp_df = df_source.copy()
        if 'Product' in temp_df.columns and product != "All":
            temp_df = temp_df[temp_df['Product'] == product]
        if 'Size' in temp_df.columns and size != "All":
            temp_df = temp_df[temp_df['Size'].astype(str).str.strip() == str(size).strip()]
        
        if temp_df.empty:
            return None
        
        # Look for body diameter columns
        for col in temp_df.columns:
            col_lower = str(col).lower()
            if any(x in col_lower for x in ['diameter', 'dia']) and 'pitch' not in col_lower:
                dia_val = temp_df[col].iloc[0]
                if pd.notna(dia_val):
                    # Convert to mm if it's in inches (small value)
                    dia_float = float(dia_val)
                    if dia_float < 10:  # Assume it's in inches if small value
                        return dia_float * 25.4
                    return dia_float
        
        return None
        
    except Exception as e:
        st.error(f"Error getting body diameter: {str(e)}")
        return None

def show_optimized_single_item_calculator():
    """Optimized single item weight calculator with NEW UI ORDER"""
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; display: flex; align-items: center; gap: 1rem;">
            Single Item Weight Calculator - OPTIMIZED
        </h1>
        <p style="margin:0; opacity: 0.9;">High-performance calculator with intelligent caching</p>
        <div style="margin-top: 0.5rem;">
            <span class="engineering-badge">Fast Calculations</span>
            <span class="technical-badge">Intelligent Caching</span>
            <span class="performance-badge">High Performance</span>
            <span class="material-badge">Optimized Database</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Performance indicator
    if st.session_state.performance_mode:
        st.markdown('<div class="performance-indicator">🚀 PERFORMANCE MODE: Optimized calculations enabled</div>', unsafe_allow_html=True)
    
    # Main input form with NEW ORDER
    with st.form("optimized_calculator_form"):
        st.markdown("### Product Configuration")
        
        # 1. Product Type
        product_options = get_available_products()
        selected_product = st.selectbox(
            "1. Product Type", 
            product_options, 
            key="calc_product_new",
            index=product_options.index(st.session_state.calc_product) if st.session_state.calc_product in product_options else 0
        )
        st.session_state.calc_product = selected_product
        
        # 2. Series
        series_options = ["Inch", "Metric"]
        selected_series = st.selectbox(
            "2. Series", 
            series_options, 
            key="calc_series_new",
            index=series_options.index(st.session_state.calc_series) if st.session_state.calc_series in series_options else 0
        )
        st.session_state.calc_series = selected_series
        
        # 3. Dimensional Standards
        dimensional_standards = get_dimensional_standards_for_product_series(selected_product, selected_series)
        selected_dimensional_standard = st.selectbox(
            "3. Dimensional Standards", 
            dimensional_standards, 
            key="calc_dimensional_standard_new",
            help="Not required for Threaded Rod and Stud",
            index=0
        )
        st.session_state.calc_dimensional_standard = selected_dimensional_standard
        
        # 4. Size Specification
        size_options = get_size_options_for_product_standard(selected_product, selected_dimensional_standard, selected_series)
        selected_size = st.selectbox(
            "4. Size Specification", 
            size_options, 
            key="calc_size_new",
            index=size_options.index(st.session_state.calc_size) if st.session_state.calc_size in size_options else 0
        )
        st.session_state.calc_size = selected_size
        
        st.markdown("### Diameter Configuration")
        
        # 5. Diameter Type
        diameter_type_options = ["Body Diameter", "Pitch Diameter"]
        selected_diameter_type = st.radio(
            "5. Diameter Type", 
            diameter_type_options, 
            key="calc_diameter_type_new",
            index=diameter_type_options.index(st.session_state.calc_diameter_type) if st.session_state.calc_diameter_type in diameter_type_options else 0
        )
        st.session_state.calc_diameter_type = selected_diameter_type
        
        # Conditional fields for Pitch Diameter
        if selected_diameter_type == "Pitch Diameter":
            col1, col2 = st.columns(2)
            
            with col1:
                # 5a. Thread Standard
                thread_standards = get_thread_standards_for_series(selected_series)
                selected_thread_standard = st.selectbox(
                    "5a. Thread Standard", 
                    thread_standards, 
                    key="calc_thread_standard_new",
                    index=0
                )
                st.session_state.calc_thread_standard = selected_thread_standard
            
            with col2:
                # 5b. Tolerance Class (only for Inch series)
                if selected_series == "Inch":
                    tolerance_options = get_tolerance_classes_for_standard(selected_thread_standard, selected_series)
                    selected_tolerance = st.selectbox(
                        "5b. Tolerance Class", 
                        tolerance_options, 
                        key="calc_tolerance_class_new",
                        index=1
                    )
                    st.session_state.calc_tolerance_class = selected_tolerance
                else:
                    # For metric, no tolerance class needed
                    selected_tolerance = None
                    st.session_state.calc_tolerance_class = None
                    st.info("Tolerance Class not required for Metric series")
        else:
            selected_thread_standard = None
            selected_tolerance = None
        
        st.markdown("### Length Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 6. Length Unit
            length_unit_options = ["mm", "inch", "meter", "ft"]
            length_unit = st.selectbox(
                "6. Length Unit", 
                length_unit_options, 
                key="calc_length_unit_new",
                index=length_unit_options.index(st.session_state.calc_length_unit) if st.session_state.calc_length_unit in length_unit_options else 0
            )
            st.session_state.calc_length_unit = length_unit
        
        with col2:
            # 7. Length Value
            length_value = st.number_input(
                "7. Length Value", 
                min_value=0.1, 
                value=float(st.session_state.calc_length), 
                step=0.1, 
                key="calc_length_new"
            )
            st.session_state.calc_length = length_value
        
        # Calculate button
        calculate_btn = st.form_submit_button("Calculate Weight (FAST)", use_container_width=True, type="primary")
    
    # FAST CALCULATION LOGIC
    if calculate_btn:
        # Validate inputs
        if selected_product == "All":
            st.error("Please select a specific product type")
            return
        
        if selected_size == "All":
            st.error("Please select a specific size")
            return
        
        if selected_dimensional_standard == "All" and selected_product.lower() not in ["threaded rod", "stud"]:
            st.error("Please select a dimensional standard for this product type")
            return
        
        # Convert length to mm
        length_mm = convert_length_to_mm_fast(length_value, length_unit)
        
        if length_mm <= 0:
            st.error("Please enter a valid length value")
            return
        
        # Determine diameter based on diameter type
        diameter_mm = 0
        diameter_source = ""
        
        if selected_diameter_type == "Body Diameter":
            # For Body Diameter, we need to get the body diameter from dimensional data
            if selected_dimensional_standard != "All" and selected_dimensional_standard != "Not Required":
                # Try to get body diameter from dimensional database
                body_dia = get_body_diameter_from_db(selected_dimensional_standard, selected_product, selected_size)
                if body_dia:
                    diameter_mm = body_dia
                    diameter_source = f"Body Diameter from {selected_dimensional_standard}: {diameter_mm:.2f} mm"
                else:
                    st.error("Could not fetch body diameter from database. Please check your selections.")
                    return
            else:
                st.error("Body Diameter requires a dimensional standard selection")
                return
        else:
            # For Pitch Diameter, get from thread database
            if selected_thread_standard:
                pitch_dia = fast_calculator._get_pitch_diameter_fast(selected_thread_standard, selected_size, selected_tolerance)
                if pitch_dia:
                    diameter_mm = pitch_dia
                    diameter_source = f"Pitch Diameter from {selected_thread_standard}: {diameter_mm:.2f} mm"
                else:
                    st.error("Could not fetch pitch diameter from database. Please check thread standard and size.")
                    return
            else:
                st.error("Pitch Diameter requires a thread standard selection")
                return
        
        if diameter_mm > 0 and length_mm > 0:
            # FAST WEIGHT CALCULATION
            start_time = time.time()
            
            weight_kg = fast_calculator.calculate_weight_fast(
                product=selected_product,
                diameter_mm=diameter_mm,
                length_mm=length_mm,
                diameter_type=selected_diameter_type.lower().replace(" ", "_"),
                thread_standard=selected_thread_standard,
                thread_size=selected_size,
                thread_class=selected_tolerance,
                dimensional_standard=selected_dimensional_standard if selected_dimensional_standard != "All" and selected_dimensional_standard != "Not Required" else None,
                dimensional_product=selected_product,
                dimensional_size=selected_size
            )
            
            calculation_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if weight_kg > 0:
                # Display results with performance info
                st.success("### Calculation Results (OPTIMIZED)")
                
                result_col1, result_col2, result_col3 = st.columns(3)
                
                with result_col1:
                    st.metric("Estimated Weight", f"{weight_kg:.4f} kg")
                    st.metric("Weight (grams)", f"{weight_kg * 1000:.2f} g")
                
                with result_col2:
                    st.metric("Diameter Used", f"{diameter_mm:.2f} mm")
                    st.metric("Length", f"{length_mm:.2f} mm")
                
                with result_col3:
                    st.metric("Weight (lbs)", f"{weight_kg * 2.20462:.4f} lbs")
                    st.metric("Calculation Time", f"{calculation_time:.2f} ms")
                
                # Show performance comparison
                if calculation_time < 10:
                    st.success(f"⚡ **High Performance**: Calculation completed in {calculation_time:.2f} milliseconds")
                elif calculation_time < 50:
                    st.info(f"🚀 **Good Performance**: Calculation completed in {calculation_time:.2f} milliseconds")
                else:
                    st.warning(f"🐢 **Acceptable Performance**: Calculation completed in {calculation_time:.2f} milliseconds")
                
                # Show calculation details
                with st.expander("Calculation Details"):
                    st.info(f"""
                    **Parameters Used:**
                    - Product: {selected_product}
                    - Series: {selected_series}
                    - Dimensional Standard: {selected_dimensional_standard}
                    - Size: {selected_size}
                    - Diameter Type: {selected_diameter_type}
                    - {diameter_source}
                    - Length: {length_value} {length_unit} ({length_mm:.2f} mm)
                    - Thread Standard: {selected_thread_standard if selected_thread_standard else 'N/A'}
                    - Tolerance Class: {selected_tolerance if selected_tolerance else 'N/A'}
                    - Material: Carbon Steel (7.85 g/cm³)
                    - Performance: {calculation_time:.2f} ms calculation time
                    """)
                
                # Save to history
                calculation_data = {
                    'product': selected_product,
                    'size': selected_size,
                    'weight_kg': weight_kg,
                    'weight_g': weight_kg * 1000,
                    'weight_lbs': weight_kg * 2.20462,
                    'diameter_mm': diameter_mm,
                    'length_mm': length_mm,
                    'series': selected_series,
                    'dimensional_standard': selected_dimensional_standard,
                    'diameter_type': selected_diameter_type,
                    'thread_standard': selected_thread_standard,
                    'tolerance_class': selected_tolerance,
                    'calculation_time_ms': calculation_time,
                    'timestamp': datetime.now().isoformat()
                }
                save_calculation_history(calculation_data)
                
                st.balloons()
                
            else:
                st.error("Failed to calculate weight. Please check your inputs and try again.")
        else:
            st.error("Invalid diameter or length values")

# ======================================================
# OPTIMIZED BATCH PROCESSING
# ======================================================

def process_single_row_optimized(row, row_index):
    """Process single row optimized for batch processing"""
    # Extract parameters
    product = row.get('Product', '')
    size = row.get('Size', '')
    length_val = row.get('Length', 0)
    length_unit = row.get('Length_Unit', 'mm')
    diameter_type = row.get('Diameter_Type', 'body')
    thread_standard = row.get('Thread_Standard', 'ASME B1.1')
    thread_class = row.get('Thread_Class', '2A')
    dimensional_standard = row.get('Dimensional_Standard', 'ASME B18.2.1')
    
    # Convert length
    length_mm = convert_length_to_mm_fast(length_val, length_unit)
    
    # Get diameter
    diameter_mm = 0
    if diameter_type == "body":
        diameter_mm = get_body_diameter_from_db(dimensional_standard, product, size)
        if not diameter_mm:
            diameter_mm = 0
    else:
        pitch_dia = fast_calculator._get_pitch_diameter_fast(thread_standard, size, thread_class)
        if pitch_dia:
            diameter_mm = pitch_dia
        else:
            diameter_mm = 0
    
    # Calculate weight using fast calculator
    weight_kg = fast_calculator.calculate_weight_fast(
        product=product,
        diameter_mm=diameter_mm,
        length_mm=length_mm,
        diameter_type=diameter_type,
        thread_standard=thread_standard,
        thread_size=size,
        thread_class=thread_class,
        dimensional_standard=dimensional_standard,
        dimensional_product=product,
        dimensional_size=size
    )
    
    # Prepare result
    result_row = {
        'Row_Index': row_index,
        'Product': product,
        'Size': size,
        'Length': f"{length_val} {length_unit}",
        'Diameter_Type': diameter_type,
        'Diameter_Used_mm': round(diameter_mm, 2),
        'Calculated_Weight_kg': weight_kg,
        'Thread_Standard': thread_standard,
        'Thread_Class': thread_class,
        'Status': 'Success' if weight_kg > 0 else 'Failed'
    }
    
    return result_row

def process_batch_calculation_optimized(batch_df):
    """Optimized batch processing with parallel execution"""
    try:
        progress_bar = st.progress(0)
        results = []
        
        # Pre-cache common lookups
        st.info("🔄 Pre-caching data for faster batch processing...")
        
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_row = {}
            
            for i, row in batch_df.iterrows():
                future = executor.submit(process_single_row_optimized, row, i)
                future_to_row[future] = i
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_row):
                i = future_to_row[future]
                try:
                    result_row = future.result()
                    results.append(result_row)
                    
                    # Update progress
                    progress = (len(results) / len(batch_df))
                    progress_bar.progress(progress)
                    
                except Exception as e:
                    st.error(f"Error processing row {i}: {str(e)}")
                    # Add error result
                    error_row = {
                        'Product': batch_df.iloc[i].get('Product', 'Unknown'),
                        'Size': batch_df.iloc[i].get('Size', 'Unknown'),
                        'Status': 'Error',
                        'Error': str(e)
                    }
                    results.append(error_row)
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"Batch processing error: {str(e)}")
        return None

# ======================================================
# ADVANCED AI ASSISTANT (COMPLETE IMPLEMENTATION)
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

# Initialize AI Assistant
ai_assistant = AdvancedFastenerAI(df, df_iso4014, df_mechem, thread_files, df_din7991, df_asme_b18_3)

def show_chat_interface():
    """Show AI assistant chat interface"""
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0;">PiU - Fastener Intelligence Assistant</h1>
        <p style="margin:0; opacity: 0.9;">Ask technical questions about fasteners, materials, and standards</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat container
    st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        if message["role"] == "user":
            st.markdown(f'<div class="message user-message">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="message ai-message">{message["content"]}</div>', unsafe_allow_html=True)
    
    # Typing indicator
    if st.session_state.ai_thinking:
        st.markdown('''
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick questions
    st.markdown("### Quick Questions")
    quick_questions = [
        "What is the carbon content in Grade 5?",
        "Explain tensile strength for fasteners",
        "What are the mechanical properties of Grade 8?",
        "How to calculate fastener weight?",
        "What is the difference between Grade 2 and Grade 5?"
    ]
    
    cols = st.columns(3)
    for idx, question in enumerate(quick_questions):
        with cols[idx % 3]:
            if st.button(question, key=f"quick_{idx}", use_container_width=True):
                process_user_message(question)
    
    # Chat input
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    user_input = st.text_input("Ask a question about fasteners...", key="chat_input")
    if st.button("Send", key="send_message", use_container_width=True) and user_input:
        process_user_message(user_input)
    st.markdown('</div>', unsafe_allow_html=True)

def process_user_message(message):
    """Process user message and generate AI response"""
    # Add user message to chat
    st.session_state.chat_messages.append({"role": "user", "content": message})
    
    # Show typing indicator
    st.session_state.ai_thinking = True
    st.rerun()
    
    # Generate AI response
    try:
        response = ai_assistant.process_complex_query(message)
        
        # Add AI response to chat
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        
        # Learn from interaction
        ai_assistant.learn_from_interaction(message, response, True)
        
    except Exception as e:
        error_response = f"I apologize, but I encountered an error processing your question: {str(e)}"
        st.session_state.chat_messages.append({"role": "assistant", "content": error_response})
    
    # Hide typing indicator
    st.session_state.ai_thinking = False
    st.rerun()

# ======================================================
# ENHANCED PRODUCT DATABASE (COMPLETE IMPLEMENTATION)
# ======================================================

def show_enhanced_product_database():
    """Show enhanced product database with multiple sections"""
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0;">Product Database - Professional Fastener Intelligence</h1>
        <p style="margin:0; opacity: 0.9;">Comprehensive fastener data across multiple standards and specifications</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Section toggles
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Section A - Dimensional Standards", use_container_width=True):
            st.session_state.section_a_view = True
            st.session_state.section_b_view = False
            st.session_state.section_c_view = False
    with col2:
        if st.button("Section B - Thread Data", use_container_width=True):
            st.session_state.section_a_view = False
            st.session_state.section_b_view = True
            st.session_state.section_c_view = False
    with col3:
        if st.button("Section C - Material Properties", use_container_width=True):
            st.session_state.section_a_view = False
            st.session_state.section_b_view = False
            st.session_state.section_c_view = True
    
    # Display selected section
    if st.session_state.section_a_view:
        show_section_a_dimensional()
    elif st.session_state.section_b_view:
        show_section_b_thread_data()
    elif st.session_state.section_c_view:
        show_section_c_material_properties()

def show_section_a_dimensional():
    """Show Section A - Dimensional Standards"""
    st.markdown("### Section A - Dimensional Standards Database")
    
    with st.container():
        st.markdown('<div class="independent-section">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Product filter
            product_options = get_available_products()
            selected_product = st.selectbox(
                "Product Type",
                product_options,
                key="section_a_product"
            )
            st.session_state.section_a_current_product = selected_product
        
        with col2:
            # Standard filter
            standard_options = ["All"] + list(st.session_state.available_products.keys())
            selected_standard = st.selectbox(
                "Standard",
                standard_options,
                key="section_a_standard"
            )
            st.session_state.section_a_current_standard = selected_standard
        
        with col3:
            # Size filter
            size_options = get_size_options_for_product_standard(
                selected_product, 
                selected_standard, 
                "Inch"  # Default series
            )
            selected_size = st.selectbox(
                "Size",
                size_options,
                key="section_a_size"
            )
            st.session_state.section_a_current_size = selected_size
        
        # Filter and display data
        if st.button("Search Dimensional Data", use_container_width=True):
            filtered_df = filter_dimensional_data(selected_product, selected_standard, selected_size)
            if not filtered_df.empty:
                st.session_state.section_a_results = filtered_df
                st.success(f"Found {len(filtered_df)} records")
                st.dataframe(filtered_df, use_container_width=True)
                
                # Export options
                export_col1, export_col2 = st.columns(2)
                with export_col1:
                    export_format = st.selectbox("Export Format", ["CSV", "Excel"], key="section_a_export")
                with export_col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Export Data", use_container_width=True, key="export_section_a"):
                        enhanced_export_data(filtered_df, export_format)
            else:
                st.warning("No data found for the selected filters")
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_section_b_thread_data():
    """Show Section B - Thread Data"""
    st.markdown("### Section B - Thread Data Database")
    
    with st.container():
        st.markdown('<div class="independent-section">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Thread standard filter
            thread_standards = list(thread_files.keys())
            selected_standard = st.selectbox(
                "Thread Standard",
                ["All"] + thread_standards,
                key="section_b_standard"
            )
            st.session_state.section_b_current_standard = selected_standard
        
        with col2:
            # Size filter
            size_options = ["All"]
            if selected_standard != "All":
                sizes = thread_manager.get_thread_sizes(selected_standard, thread_files[selected_standard])
                size_options.extend(sizes)
            selected_size = st.selectbox(
                "Thread Size",
                size_options,
                key="section_b_size"
            )
            st.session_state.section_b_current_size = selected_size
        
        with col3:
            # Class filter
            class_options = ["All"]
            if selected_standard != "All":
                classes = thread_manager.get_thread_classes(selected_standard, thread_files[selected_standard])
                class_options.extend(classes)
            selected_class = st.selectbox(
                "Thread Class",
                class_options,
                key="section_b_class"
            )
            st.session_state.section_b_current_class = selected_class
        
        # Filter and display data
        if st.button("Search Thread Data", use_container_width=True):
            filtered_df = filter_thread_data(selected_standard, selected_size, selected_class)
            if not filtered_df.empty:
                st.session_state.section_b_results = filtered_df
                st.success(f"Found {len(filtered_df)} records")
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.warning("No thread data found for the selected filters")
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_section_c_material_properties():
    """Show Section C - Material Properties"""
    st.markdown("### Section C - Material & Chemical Properties")
    
    with st.container():
        st.markdown('<div class="independent-section">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Property class filter
            class_options = ["All"] + st.session_state.property_classes
            selected_class = st.selectbox(
                "Property Class",
                class_options,
                key="section_c_class"
            )
            st.session_state.section_c_current_class = selected_class
        
        with col2:
            # Standard filter
            standard_options = ["All"] + list(df_mechem['Standards'].unique()) if 'Standards' in df_mechem.columns else ["All"]
            selected_standard = st.selectbox(
                "Standard",
                standard_options,
                key="section_c_standard"
            )
            st.session_state.section_c_current_standard = selected_standard
        
        # Filter and display data
        if st.button("Search Material Properties", use_container_width=True):
            filtered_df = filter_material_data(selected_class, selected_standard)
            if not filtered_df.empty:
                st.session_state.section_c_results = filtered_df
                st.success(f"Found {len(filtered_df)} records")
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.warning("No material data found for the selected filters")
        
        st.markdown('</div>', unsafe_allow_html=True)

def filter_dimensional_data(product, standard, size):
    """Filter dimensional data based on criteria"""
    try:
        # Determine which dataframe to use based on standard
        df_source = None
        if standard == "ASME B18.2.1" and not df.empty:
            df_source = df
        elif standard == "ISO 4014" and not df_iso4014.empty:
            df_source = df_iso4014
        elif standard == "DIN-7991" and st.session_state.din7991_loaded:
            df_source = df_din7991
        elif standard == "ASME B18.3" and st.session_state.asme_b18_3_loaded:
            df_source = df_asme_b18_3
        
        if df_source is None:
            return pd.DataFrame()
        
        # Apply filters
        filtered_df = df_source.copy()
        
        if product != "All" and 'Product' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Product'] == product]
        
        if size != "All" and 'Size' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Size'].astype(str).str.strip() == str(size).strip()]
        
        return filtered_df
        
    except Exception as e:
        st.error(f"Error filtering dimensional data: {str(e)}")
        return pd.DataFrame()

def filter_thread_data(standard, size, thread_class):
    """Filter thread data based on criteria"""
    try:
        if standard == "All":
            return pd.DataFrame()
        
        df_thread = thread_manager.get_thread_data(standard, thread_files[standard])
        if df_thread.empty:
            return pd.DataFrame()
        
        filtered_df = df_thread.copy()
        
        if size != "All" and 'Thread' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Thread'].astype(str).str.strip() == str(size).strip()]
        
        if thread_class != "All" and 'Class' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Class'].astype(str).str.strip() == str(thread_class).strip()]
        
        return filtered_df
        
    except Exception as e:
        st.error(f"Error filtering thread data: {str(e)}")
        return pd.DataFrame()

def filter_material_data(property_class, standard):
    """Filter material data based on criteria"""
    try:
        if df_mechem.empty:
            return pd.DataFrame()
        
        filtered_df = df_mechem.copy()
        
        if property_class != "All":
            # Find the property class column
            class_col = None
            for col in filtered_df.columns:
                if any(keyword in col.lower() for keyword in ['grade', 'class', 'property']):
                    class_col = col
                    break
            
            if class_col:
                filtered_df = filtered_df[filtered_df[class_col].astype(str).str.strip() == str(property_class).strip()]
        
        if standard != "All" and 'Standards' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Standards'].astype(str).str.strip() == str(standard).strip()]
        
        return filtered_df
        
    except Exception as e:
        st.error(f"Error filtering material data: {str(e)}")
        return pd.DataFrame()

# ======================================================
# OPTIMIZED CALCULATIONS PAGE
# ======================================================

def show_optimized_calculations():
    """Optimized calculations page with performance improvements"""
    
    tab1, tab2, tab3 = st.tabs(["Single Calculator (FAST)", "Batch Processor (OPTIMIZED)", "Analytics"])
    
    with tab1:
        show_optimized_single_item_calculator()
    
    with tab2:
        st.markdown("### Batch Weight Processor - OPTIMIZED")
        st.success("🚀 **Performance Enhanced**: Now with parallel processing and intelligent caching")
        
        st.info("Upload a CSV/Excel file with columns: Product, Size, Length, Diameter_Type, Thread_Standard, Thread_Class")
        
        # Download template
        st.markdown("### Download Batch Template")
        template_data = {
            'Product': ['Hex Bolt', 'Threaded Rod', 'Hex Cap Screws'],
            'Size': ['1/4', 'M6', '3/8'],
            'Length': [50, 100, 75],
            'Length_Unit': ['mm', 'mm', 'mm'],
            'Diameter_Type': ['Body Diameter', 'Pitch Diameter', 'Body Diameter'],
            'Thread_Standard': ['ASME B1.1', 'ISO 965-2-98 Coarse', 'ASME B1.1'],
            'Thread_Class': ['2A', '6g', '2A'],
            'Dimensional_Standard': ['ASME B18.2.1', 'ISO 4014', 'ASME B18.2.1']
        }
        template_df = pd.DataFrame(template_data)
        csv_template = template_df.to_csv(index=False)
        st.download_button(
            label="Download Batch Template (CSV)",
            data=csv_template,
            file_name="batch_weight_template.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        uploaded_file = st.file_uploader("Choose batch file", type=["csv", "xlsx"], key="batch_upload_opt")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    batch_df = pd.read_excel(uploaded_file)
                else:
                    batch_df = pd.read_csv(uploaded_file)
                
                st.write("Preview of uploaded data:")
                st.dataframe(batch_df.head())
                
                required_cols = ['Product', 'Size', 'Length']
                missing_cols = [col for col in required_cols if col not in batch_df.columns]
                
                if missing_cols:
                    st.error(f"Missing required columns: {missing_cols}")
                else:
                    if st.button("Process Batch Calculation (OPTIMIZED)", use_container_width=True, key="process_batch_opt"):
                        start_time = time.time()
                        with st.spinner("🔄 Processing batch data with parallel execution..."):
                            results_df = process_batch_calculation_optimized(batch_df)
                            processing_time = time.time() - start_time
                            
                            if results_df is not None:
                                st.session_state.batch_calculation_results = results_df
                                st.success(f"✅ Processed {len(results_df)} records in {processing_time:.2f} seconds!")
                                st.dataframe(results_df)
                                
                                # Show performance summary
                                success_count = len(results_df[results_df['Status'] == 'Success'])
                                failed_count = len(results_df[results_df['Status'] == 'Failed'])
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Successful Calculations", success_count)
                                with col2:
                                    st.metric("Failed Calculations", failed_count)
                                with col3:
                                    st.metric("Processing Time", f"{processing_time:.2f}s")
                                
                                # Performance comparison
                                avg_time_per_record = processing_time / len(results_df) * 1000  # ms per record
                                if avg_time_per_record < 10:
                                    st.success(f"⚡ **Excellent Performance**: {avg_time_per_record:.1f} ms per record")
                                elif avg_time_per_record < 50:
                                    st.info(f"🚀 **Good Performance**: {avg_time_per_record:.1f} ms per record")
                                else:
                                    st.warning(f"🐢 **Acceptable Performance**: {avg_time_per_record:.1f} ms per record")
                            
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
        # Show batch results if available
        if not st.session_state.batch_calculation_results.empty:
            st.markdown("### Export Batch Results")
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                batch_export_format = st.selectbox("Export Format", ["CSV", "Excel"], key="batch_export")
            with export_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Download Batch Results", use_container_width=True, key="download_batch"):
                    enhanced_export_data(st.session_state.batch_calculation_results, batch_export_format)
    
    with tab3:
        st.markdown("### Calculation Analytics")
        st.info("Performance metrics and calculation history")
        
        if 'calculation_history' in st.session_state and st.session_state.calculation_history:
            history_df = pd.DataFrame(st.session_state.calculation_history)
            
            # Performance metrics
            if 'calculation_time_ms' in history_df.columns:
                avg_calc_time = history_df['calculation_time_ms'].mean()
                st.metric("Average Calculation Time", f"{avg_calc_time:.2f} ms")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'weight_kg' in history_df.columns:
                    try:
                        fig_weights = px.histogram(history_df, x='weight_kg', 
                                                 title='Weight Distribution History',
                                                 labels={'weight_kg': 'Weight (kg)'})
                        st.plotly_chart(fig_weights, use_container_width=True)
                    except Exception:
                        st.info("Could not generate weight distribution chart")
            
            with col2:
                if 'product' in history_df.columns:
                    product_counts = history_df['product'].value_counts()
                    if len(product_counts) > 0:
                        fig_products = px.pie(values=product_counts.values, 
                                            names=product_counts.index,
                                            title='Products Calculated')
                        st.plotly_chart(fig_products, use_container_width=True)
            
            # Show recent calculations with performance data
            st.markdown("### Recent Calculation Details")
            display_cols = [col for col in history_df.columns if col not in ['timestamp', 'calculation_time_ms']]
            if 'calculation_time_ms' in history_df.columns:
                display_cols.append('calculation_time_ms')  # Add at end
            st.dataframe(history_df[display_cols].tail(10), use_container_width=True)
        else:
            st.info("No calculation history available. Perform some calculations to see analytics here.")

# ======================================================
# KEEPING YOUR EXISTING FUNCTIONS (with minor optimizations)
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
                time_info = f" - {calc.get('calculation_time_ms', 'N/A')}ms" if 'calculation_time_ms' in calc else ""
                st.markdown(f"""
                <div class="calculation-card">
                    <strong>{calc.get('product', 'N/A')}</strong> | 
                    Size: {calc.get('size', 'N/A')} | 
                    Weight: {calc.get('weight_kg', 'N/A')} kg{time_info}
                    <br><small>{calc.get('timestamp', '')}</small>
                </div>
                """, unsafe_allow_html=True)

def enhanced_export_data(filtered_df, export_format):
    """Enhanced export with multiple format options"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if export_format == "Excel":
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                    filtered_df.to_excel(writer, sheet_name='Data', index=False)
                    
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
                
                with open(tmp.name, 'rb') as f:
                    st.download_button(
                        label="Download Excel File",
                        data=f,
                        file_name=f"fastener_data_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"excel_export_{timestamp}"
                    )
        except Exception as e:
            st.error(f"Excel export error: {str(e)}")
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
# PERFORMANCE MONITORING
# ======================================================

def show_performance_monitor():
    """Show performance monitoring dashboard"""
    with st.sidebar:
        st.markdown("---")
        with st.expander("Performance Monitor"):
            st.markdown("**Cache Statistics:**")
            st.text(f"Pitch Cache: {len(fast_calculator._pitch_cache)}")
            st.text(f"Head Height Cache: {len(fast_calculator._head_height_cache)}")
            st.text(f"Width Flats Cache: {len(fast_calculator._width_flats_cache)}")
            
            if 'calculation_history' in st.session_state:
                history_df = pd.DataFrame(st.session_state.calculation_history)
                if 'calculation_time_ms' in history_df.columns:
                    avg_time = history_df['calculation_time_ms'].mean()
                    st.metric("Avg Calc Time", f"{avg_time:.1f} ms")
            
            # Thread data cache info
            st.markdown("**Thread Data Cache:**")
            st.text(f"Thread Data: {len(thread_manager._cache)}")
            st.text(f"Size Cache: {len(thread_manager._size_cache)}")
            st.text(f"Class Cache: {len(thread_manager._class_cache)}")

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
            df_thread = thread_manager.get_thread_data(standard, url)
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
# HELP SYSTEM
# ======================================================

def show_help_system():
    """Show contextual help system"""
    with st.sidebar:
        st.markdown("---")
        with st.expander("OPTIMIZED Weight Calculator Guide"):
            st.markdown("""
            **OPTIMIZED SINGLE ITEM CALCULATOR:**
            
            **New UI Order:**
            1. **Product Type**: Select from dropdown
            2. **Series**: Choose Inch or Metric  
            3. **Dimensional Standards**: Auto-populated based on product and series
            4. **Size Specification**: Auto-populated based on selections
            5. **Diameter Type**: Choose Body or Pitch Diameter
               - For Pitch Diameter:
                 - Thread Standard (auto-selected by series)
                 - Tolerance Class (only for Inch series - 1A, 2A, 3A)
            6. **Length Unit**: Select unit
            7. **Length Value**: Enter length
            
            **Enhanced Features:**
            - 🚀 **Automatic diameter fetching** from databases
            - ⚡ **Inch to mm conversion** for all calculations
            - 🔧 **Tolerance-class specific** pitch diameters for inch series
            - 📊 **Independent operation** from product database
            - 💾 **Streamlit app data** instead of local files
            """)

# ======================================================
# KEEPING YOUR EXISTING UI COMPONENTS
# ======================================================

def show_enhanced_home():
    """Show professional engineering dashboard"""
    
    st.markdown("""
    <div class="engineering-header">
        <h1 style="margin:0; font-size: 2.5rem;">JSC Industries</h1>
        <p style="margin:0; font-size: 1.2rem; opacity: 0.9;">Professional Fastener Intelligence Platform v4.0 - OPTIMIZED</p>
        <div style="margin-top: 1rem;">
            <span class="engineering-badge">Optimized Calculator</span>
            <span class="performance-badge">High Performance</span>
            <span class="technical-badge">Intelligent Caching</span>
            <span class="material-badge">Fast Database</span>
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
    
    st.markdown('<h2 class="section-header">Engineering Tools - OPTIMIZED</h2>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    actions = [
        ("Product Database", "Professional product discovery with engineering filters", "database"),
        ("Engineering Calculator", "OPTIMIZED weight calculations with high performance", "calculator"),
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
        st.markdown('<h3 class="section-header">System Status - OPTIMIZED</h3>', unsafe_allow_html=True)
        
        status_items = [
            ("ASME B18.2.1 Data", not df.empty, "engineering-badge"),
            ("ISO 4014 Data", not df_iso4014.empty, "technical-badge"),
            ("DIN-7991 Data", st.session_state.din7991_loaded, "material-badge"),
            ("ASME B18.3 Data", st.session_state.asme_b18_3_loaded, "grade-badge"),
            ("ME&CERT Data", not df_mechem.empty, "engineering-badge"),
            ("Thread Data", any(not thread_manager.get_thread_data(std, url).empty for std, url in thread_files.items()), "technical-badge"),
            ("Weight Calculations", True, "engineering-badge"),
            ("Optimized Calculator", True, "performance-badge"),
        ]
        
        for item_name, status, badge_class in status_items:
            if status:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0;">{item_name} - Active</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0; background: #6c757d;">{item_name} - Limited</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<h3 class="section-header">OPTIMIZED Features</h3>', unsafe_allow_html=True)
        
        features = [
            "High-performance weight calculations",
            "Intelligent caching system", 
            "Parallel batch processing",
            "Fast database lookups",
            "Thread-safe operations",
            "Memory-efficient data structures",
            "Real-time performance monitoring",
            "Optimized mathematical calculations",
            "Smart preloading of common data",
            "Background data processing"
        ]
        
        for feature in features:
            st.markdown(f'<div style="padding: 0.5rem; border-left: 3px solid #3498db; margin: 0.2rem 0; background: var(--neutral-light);">• {feature}</div>', unsafe_allow_html=True)
    
    show_calculation_history()

# ======================================================
# SECTION DISPATCHER
# ======================================================

def show_section(title):
    if title == "Product Database":
        show_enhanced_product_database()
    elif title == "Calculations":
        show_optimized_calculations()
    elif title == "PiU (AI Assistant)":
        show_chat_interface()
    else:
        st.info(f"Section {title} is coming soon!")
    
    st.markdown("---")
    if st.button("Back to Dashboard", use_container_width=True):
        st.session_state.selected_section = None
        st.rerun()

# ======================================================
# MAIN OPTIMIZED APPLICATION
# ======================================================

def main_optimized():
    """Main application with all optimizations"""
    
    # Initialize session state
    initialize_session_state()
    
    # Show performance monitor
    show_performance_monitor()
    
    # Show help system
    show_help_system()
    
    # Show data quality indicators
    show_data_quality_indicators()
    
    # Navigation
    with st.sidebar:
        st.markdown("## Navigation")
        
        sections = [
            "Home Dashboard",
            "Product Database", 
            "Calculations (OPTIMIZED)",
            "PiU (AI Assistant)"
        ]
        
        for section in sections:
            if st.button(section, use_container_width=True, key=f"nav_opt_{section}"):
                if section == "Home Dashboard":
                    st.session_state.selected_section = None
                elif section == "Calculations (OPTIMIZED)":
                    st.session_state.selected_section = "Calculations"
                else:
                    st.session_state.selected_section = section
                st.rerun()
        
        # Debug mode toggle
        st.markdown("---")
        st.session_state.debug_mode = st.checkbox("Debug Mode", value=st.session_state.debug_mode)
        st.session_state.performance_mode = st.checkbox("Performance Mode", value=st.session_state.performance_mode)
    
    # Section dispatcher with optimizations
    if st.session_state.selected_section is None:
        show_enhanced_home()
    elif st.session_state.selected_section == "Calculations":
        show_optimized_calculations()
    else:
        show_section(st.session_state.selected_section)
    
    # Footer with performance info
    st.markdown("""
        <hr>
        <div style='text-align: center; color: gray; padding: 2rem;'>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
                <span class="engineering-badge">OPTIMIZED Calculator</span>
                <span class="performance-badge">High Performance</span>
                <span class="technical-badge">Intelligent Caching</span>
                <span class="material-badge">Fast Database</span>
            </div>
            <p><strong>© 2024 JSC Industries Pvt Ltd</strong> | Born to Perform • Engineered for Excellence</p>
            <p style="font-size: 0.8rem;">Professional Fastener Intelligence Platform v4.0 - OPTIMIZED Performance Edition</p>
        </div>
    """, unsafe_allow_html=True)

# Run the optimized application
if __name__ == "__main__":
    main_optimized()