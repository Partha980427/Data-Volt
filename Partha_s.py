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
import logging
from logging.handlers import RotatingFileHandler
import sys
import traceback
from typing import Dict, List, Optional, Tuple, Any
import requests
from io import BytesIO
import hashlib

# ======================================================
# ENHANCED LOGGING CONFIGURATION
# ======================================================
def setup_logging():
    """Setup comprehensive logging for the application"""
    logger = logging.getLogger('FastenerIntelligence')
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

warnings.filterwarnings('ignore')

# ======================================================
# ENHANCED PATHS & FILES WITH FALLBACK MECHANISM
# ======================================================
class DataConfig:
    """Enhanced data configuration with fallback mechanisms"""
    
    def __init__(self):
        self.primary_sources = {
            "main_data": {
                "google": "https://docs.google.com/spreadsheets/d/11Icre8F3X8WA5BVwkJx75NOH3VzF6G7b/export?format=xlsx",
                "local": r"G:\My Drive\Streamlite\ASME B18.2.1 Hex Bolt and Heavy Hex Bolt.xlsx"
            },
            "me_chem_data": {
                "google": "https://docs.google.com/spreadsheets/d/12lBzI67Wb0yZyJKYxpDCLzHF9zvS2Fha/export?format=xlsx",
                "local": r"G:\My Drive\Streamlite\Mechanical and Chemical.xlsx"
            },
            "iso4014": {
                "google": "https://docs.google.com/spreadsheets/d/1d2hANwoMhuzwyKJ72c125Uy0ujB6QsV_/export?format=xlsx",
                "local": r"G:\My Drive\Streamlite\ISO 4014 Hex Bolt.xlsx"
            },
            "din7991": {
                "google": "https://docs.google.com/spreadsheets/d/1PjptIbFfebdF1h_Aj124fNgw5jNBWlvn/export?format=xlsx",
                "local": r"G:\My Drive\Streamlite\DIN-7991.xlsx"
            },
            "asme_b18_3": {
                "google": "https://docs.google.com/spreadsheets/d/1dPNGwf7bv5A77rMSPpl11dhcJTXQfob1/export?format=xlsx",
                "local": r"G:\My Drive\Streamlite\ASME B18.3.xlsx"
            }
        }
        
        self.thread_files = {
            "ASME B1.1": "https://docs.google.com/spreadsheets/d/1YHgUloNsFudxxqhWQV66D2DtSSKWFP_w/export?format=xlsx",
            "ISO 965-2-98 Coarse": "https://docs.google.com/spreadsheets/d/1be5eEy9hbVfMg2sl1-Cz1NNCGGF8EB-L/export?format=xlsx",
            "ISO 965-2-98 Fine": "https://docs.google.com/spreadsheets/d/1QGQ6SMWBSTsah-vq3zYnhOC3NXaBdKPe/export?format=xlsx",
        }
        
        self.fallback_data = self._create_fallback_data()
    
    def _create_fallback_data(self) -> Dict[str, Any]:
        """Create comprehensive fallback data for all product types"""
        return {
            'products': {
                'ASME B18.2.1': ['Hex Bolt', 'Heavy Hex Bolt', 'Hex Cap Screws', 'Heavy Hex Screws', 'Threaded Rod'],
                'ISO 4014': ['Hex Bolt', 'Threaded Rod'],
                'DIN-7991': ['Hexagon Socket Countersunk Head Cap Screw', 'Threaded Rod'],
                'ASME B18.3': ['Hexagon Socket Head Cap Screws', 'Threaded Rod']
            },
            'series': {
                'ASME B18.2.1': 'Inch',
                'ISO 4014': 'Metric', 
                'DIN-7991': 'Metric',
                'ASME B18.3': 'Inch'
            },
            'sizes': {
                'ASME B18.2.1': ['1/4', '5/16', '3/8', '7/16', '1/2', '9/16', '5/8', '3/4', '7/8', '1'],
                'ISO 4014': ['M6', 'M8', 'M10', 'M12', 'M16', 'M20', 'M24', 'M30'],
                'DIN-7991': ['M4', 'M5', 'M6', 'M8', 'M10'],
                'ASME B18.3': ['#4', '#6', '#8', '#10', '1/4', '5/16', '3/8', '7/16', '1/2']
            },
            'thread_sizes': {
                'ASME B1.1': ['1/4', '5/16', '3/8', '7/16', '1/2', '9/16', '5/8', '3/4'],
                'ISO 965-2-98 Coarse': ['M6', 'M8', 'M10', 'M12', 'M16', 'M20'],
                'ISO 965-2-98 Fine': ['M8x1', 'M10x1', 'M12x1.5', 'M16x1.5', 'M20x1.5']
            },
            'property_classes': ['4.6', '4.8', '5.8', '6.8', '8.8', '9.8', '10.9', '12.9', 'A', 'B', 'B7', '304', '316', 'A193', 'A320']
        }

# Initialize data configuration
data_config = DataConfig()

# ======================================================
# ENHANCED DATA LOADING WITH COMPREHENSIVE FALLBACKS
# ======================================================
class DataLoader:
    """Enhanced data loader with robust error handling and fallbacks"""
    
    def __init__(self):
        self.loaded_data = {}
        self.quality_metrics = {}
    
    def safe_load_excel_enhanced(self, source_name: str, max_retries: int = 3, timeout: int = 30) -> pd.DataFrame:
        """Enhanced loading with comprehensive fallback mechanism"""
        logger.info(f"Loading data for: {source_name}")
        
        if source_name in self.loaded_data:
            logger.info(f"Returning cached data for: {source_name}")
            return self.loaded_data[source_name]
        
        source_config = data_config.primary_sources.get(source_name, {})
        if not source_config:
            logger.error(f"No configuration found for: {source_name}")
            return self._create_empty_dataframe_with_structure(source_name)
        
        # Try Google Sheets first
        df = self._load_from_google_sheets(source_config.get('google', ''), source_name, max_retries, timeout)
        
        # If Google Sheets fails, try local file
        if df.empty:
            df = self._load_from_local_file(source_config.get('local', ''), source_name)
        
        # If both fail, use fallback data
        if df.empty:
            df = self._create_fallback_dataframe(source_name)
            logger.warning(f"Using fallback data for: {source_name}")
        
        # Validate and clean the dataframe
        df = self._validate_and_clean_dataframe(df, source_name)
        
        # Store in cache
        self.loaded_data[source_name] = df
        
        # Update quality metrics
        self._update_quality_metrics(source_name, df)
        
        return df
    
    def _load_from_google_sheets(self, url: str, source_name: str, max_retries: int, timeout: int) -> pd.DataFrame:
        """Load data from Google Sheets with retry mechanism"""
        if not url.startswith('http'):
            return pd.DataFrame()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1} to load Google Sheets: {source_name}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                if len(response.content) < 100:
                    logger.warning(f"File seems too small: {source_name}")
                    continue
                
                df = pd.read_excel(BytesIO(response.content))
                logger.info(f"Successfully loaded Google Sheets: {source_name} - Shape: {df.shape}")
                return df
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {source_name}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All attempts failed for Google Sheets: {source_name}")
                time.sleep(1)
        
        return pd.DataFrame()
    
    def _load_from_local_file(self, file_path: str, source_name: str) -> pd.DataFrame:
        """Load data from local file"""
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size < 100:
                    logger.warning(f"File seems too small: {file_path}")
                    return pd.DataFrame()
                
                df = pd.read_excel(file_path)
                logger.info(f"Successfully loaded local file: {source_name} - Shape: {df.shape}")
                return df
            else:
                logger.warning(f"Local file not found: {file_path}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading local file {file_path}: {str(e)}")
            return pd.DataFrame()
    
    def _create_fallback_dataframe(self, source_name: str) -> pd.DataFrame:
        """Create fallback dataframe when all sources fail"""
        logger.info(f"Creating fallback dataframe for: {source_name}")
        
        if source_name == "main_data":
            return self._create_asme_b18_2_1_fallback()
        elif source_name == "me_chem_data":
            return self._create_me_chem_fallback()
        elif source_name == "iso4014":
            return self._create_iso4014_fallback()
        elif source_name == "din7991":
            return self._create_din7991_fallback()
        elif source_name == "asme_b18_3":
            return self._create_asme_b18_3_fallback()
        else:
            return pd.DataFrame()
    
    def _create_asme_b18_2_1_fallback(self) -> pd.DataFrame:
        """Create fallback data for ASME B18.2.1"""
        data = {
            'Product': ['Hex Bolt', 'Heavy Hex Bolt', 'Hex Cap Screws', 'Heavy Hex Screws', 'Threaded Rod'] * 10,
            'Size': ['1/4', '5/16', '3/8', '7/16', '1/2'] * 10,
            'Body_Diameter_Min': [0.225, 0.286, 0.344, 0.400, 0.454] * 10,
            'Body_Diameter_Max': [0.250, 0.312, 0.375, 0.438, 0.500] * 10,
            'Width_Across_Flats_Min': [0.375, 0.484, 0.577, 0.669, 0.750] * 10,
            'Width_Across_Flats_Max': [0.388, 0.500, 0.595, 0.690, 0.775] * 10,
            'Head_Height_Min': [0.163, 0.211, 0.243, 0.283, 0.317] * 10,
            'Head_Height_Max': [0.188, 0.236, 0.268, 0.308, 0.342] * 10,
            'Thread': ['1/4-20', '5/18-18', '3/8-16', '7/16-14', '1/2-13'] * 10,
            'Standards': ['ASME B18.2.1'] * 50
        }
        return pd.DataFrame(data)
    
    def _create_me_chem_fallback(self) -> pd.DataFrame:
        """Create fallback data for Mechanical & Chemical"""
        data = {
            'Grade': ['4.8', '8.8', '10.9', 'A', 'B', 'B7', '304'] * 10,
            'Property Class': ['4.8', '8.8', '10.9', 'A', 'B', 'B7', '304'] * 10,
            'Standard': ['ISO 898-1', 'ISO 898-1', 'ISO 898-1', 'ISO 4014', 'ISO 4014', 'ASTM A193', 'ASTM A276'] * 10,
            'Tensile_Strength_Min_MPa': [420, 800, 1040, 400, 500, 860, 515] * 10,
            'Yield_Strength_Min_MPa': [340, 640, 940, 240, 300, 725, 205] * 10,
            'Elongation_Min_Percent': [14, 12, 9, 22, 20, 16, 40] * 10,
            'Carbon_Max': [0.55, 0.55, 0.55, 0.50, 0.55, 0.45, 0.08] * 10,
            'Manganese_Max': [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 2.00] * 10
        }
        return pd.DataFrame(data)
    
    def _create_iso4014_fallback(self) -> pd.DataFrame:
        """Create fallback data for ISO 4014"""
        data = {
            'Product': ['Hex Bolt'] * 20,
            'Size': ['M6', 'M8', 'M10', 'M12', 'M16'] * 4,
            'Product Grade': ['A', 'B'] * 10,
            'Basic_Major_Diameter_Min': [5.974, 7.974, 9.974, 11.966, 15.966] * 4,
            'Basic_Major_Diameter_Max': [6.000, 8.000, 10.000, 12.000, 16.000] * 4,
            'Width_Across_Flats_Min': [10.00, 13.00, 16.00, 18.00, 24.00] * 4,
            'Width_Across_Flats_Max': [10.23, 13.27, 16.27, 18.27, 24.33] * 4,
            'Head_Height_Min': [4.15, 5.65, 7.00, 8.45, 11.40] * 4,
            'Head_Height_Max': [4.85, 6.35, 7.80, 9.25, 12.20] * 4,
            'Standards': ['ISO-4014-2011'] * 20
        }
        return pd.DataFrame(data)
    
    def _create_din7991_fallback(self) -> pd.DataFrame:
        """Create fallback data for DIN-7991"""
        data = {
            'Product': ['Hexagon Socket Countersunk Head Cap Screw'] * 15,
            'Size': ['M4', 'M5', 'M6', 'M8', 'M10'] * 3,
            'dk_min': [7.66, 9.36, 11.05, 14.55, 18.30] * 3,
            'dk_max': [8.00, 10.00, 12.00, 16.00, 20.00] * 3,
            'k_min': [2.12, 2.60, 3.10, 4.15, 5.20] * 3,
            'k_max': [2.38, 2.90, 3.50, 4.65, 5.80] * 3,
            'Standards': ['DIN-7991'] * 15
        }
        return pd.DataFrame(data)
    
    def _create_asme_b18_3_fallback(self) -> pd.DataFrame:
        """Create fallback data for ASME B18.3"""
        data = {
            'Product': ['Hexagon Socket Head Cap Screws'] * 15,
            'Size': ['#4', '#6', '#8', '#10', '1/4'] * 3,
            'Head Diameter (Min)': [0.158, 0.213, 0.276, 0.332, 0.375] * 3,
            'Head Diameter (Max)': [0.168, 0.223, 0.286, 0.342, 0.385] * 3,
            'Head Height (Min)': [0.112, 0.145, 0.179, 0.215, 0.250] * 3,
            'Head Height (Max)': [0.122, 0.155, 0.189, 0.225, 0.260] * 3,
            'Standards': ['ASME B18.3'] * 15
        }
        return pd.DataFrame(data)
    
    def _create_empty_dataframe_with_structure(self, source_name: str) -> pd.DataFrame:
        """Create empty dataframe with proper structure"""
        structures = {
            "main_data": ['Product', 'Size', 'Body_Diameter_Min', 'Body_Diameter_Max', 
                         'Width_Across_Flats_Min', 'Width_Across_Flats_Max', 'Standards'],
            "me_chem_data": ['Grade', 'Property Class', 'Standard', 'Tensile_Strength_Min_MPa', 
                            'Yield_Strength_Min_MPa', 'Elongation_Min_Percent'],
            "iso4014": ['Product', 'Size', 'Product Grade', 'Basic_Major_Diameter_Min', 
                       'Basic_Major_Diameter_Max', 'Width_Across_Flats_Min', 'Standards'],
            "din7991": ['Product', 'Size', 'dk_min', 'dk_max', 'k_min', 'k_max', 'Standards'],
            "asme_b18_3": ['Product', 'Size', 'Head Diameter (Min)', 'Head Diameter (Max)', 
                          'Head Height (Min)', 'Head Height (Max)', 'Standards']
        }
        
        columns = structures.get(source_name, [])
        return pd.DataFrame(columns=columns)
    
    def _validate_and_clean_dataframe(self, df: pd.DataFrame, source_name: str) -> pd.DataFrame:
        """Validate and clean the dataframe"""
        if df.empty:
            return df
        
        # Clean column names
        df.columns = [str(col).strip().replace(' ', '_') for col in df.columns]
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Fill NaN values in critical columns
        critical_columns = {
            "main_data": ['Product', 'Size', 'Standards'],
            "me_chem_data": ['Grade', 'Property_Class', 'Standard'],
            "iso4014": ['Product', 'Size', 'Standards'],
            "din7991": ['Product', 'Size', 'Standards'],
            "asme_b18_3": ['Product', 'Size', 'Standards']
        }
        
        crit_cols = critical_columns.get(source_name, [])
        for col in crit_cols:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown')
        
        logger.info(f"Cleaned dataframe for {source_name}: {df.shape}")
        return df
    
    def _update_quality_metrics(self, source_name: str, df: pd.DataFrame):
        """Update data quality metrics"""
        if df.empty:
            self.quality_metrics[source_name] = {
                'status': 'empty',
                'completeness': 0,
                'row_count': 0,
                'column_count': 0
            }
        else:
            total_cells = len(df) * len(df.columns)
            non_null_cells = total_cells - df.isnull().sum().sum()
            completeness = (non_null_cells / total_cells) * 100 if total_cells > 0 else 0
            
            self.quality_metrics[source_name] = {
                'status': 'loaded',
                'completeness': round(completeness, 2),
                'row_count': len(df),
                'column_count': len(df.columns)
            }
    
    def load_thread_data_enhanced(self, standard_name: str) -> pd.DataFrame:
        """Enhanced thread data loading with fallback"""
        cache_key = f"thread_{standard_name}"
        
        if cache_key in self.loaded_data:
            return self.loaded_data[cache_key]
        
        file_url = data_config.thread_files.get(standard_name)
        if not file_url:
            logger.warning(f"No URL found for thread standard: {standard_name}")
            return self._create_thread_fallback(standard_name)
        
        # Try to load from Google Sheets
        df = self._load_from_google_sheets(file_url, f"thread_{standard_name}", 2, 20)
        
        # If loading fails, use fallback
        if df.empty:
            df = self._create_thread_fallback(standard_name)
            logger.warning(f"Using fallback thread data for: {standard_name}")
        
        # Standardize column names
        df = self._standardize_thread_columns(df, standard_name)
        
        # Cache the result
        self.loaded_data[cache_key] = df
        self._update_quality_metrics(cache_key, df)
        
        return df
    
    def _create_thread_fallback(self, standard_name: str) -> pd.DataFrame:
        """Create fallback thread data"""
        if standard_name == "ASME B1.1":
            data = {
                'Thread': ['1/4', '5/16', '3/8', '7/16', '1/2', '9/16', '5/8', '3/4'],
                'Class': ['2A', '2A', '2A', '2A', '2A', '2A', '2A', '2A'],
                'Basic_Major_Diameter': [0.2500, 0.3125, 0.3750, 0.4375, 0.5000, 0.5625, 0.6250, 0.7500],
                'Pitch_Diameter_Min': [0.2175, 0.2764, 0.3344, 0.3911, 0.4500, 0.5084, 0.5660, 0.6850],
                'Pitch_Diameter_Max': [0.2211, 0.2800, 0.3380, 0.3947, 0.4536, 0.5120, 0.5696, 0.6886],
                'Minor_Diameter_Min': [0.1887, 0.2443, 0.2983, 0.3492, 0.4056, 0.4620, 0.5160, 0.6279]
            }
        elif "ISO" in standard_name:
            data = {
                'Thread': ['M6', 'M8', 'M10', 'M12', 'M16', 'M20'],
                'Class': ['6g', '6g', '6g', '6g', '6g', '6g'],
                'Pitch_Diameter_Min': [5.350, 7.188, 9.026, 10.863, 14.701, 18.376],
                'Pitch_Diameter_Max': [5.480, 7.320, 9.160, 11.000, 14.840, 18.540],
                'Minor_Diameter_Min': [4.917, 6.647, 8.376, 10.106, 13.835, 17.294]
            }
        else:
            data = {
                'Thread': ['M6', 'M8', 'M10'],
                'Class': ['6g', '6g', '6g'],
                'Pitch_Diameter_Min': [5.350, 7.188, 9.026],
                'Pitch_Diameter_Max': [5.480, 7.320, 9.160]
            }
        
        df = pd.DataFrame(data)
        df['Standard'] = standard_name
        return df
    
    def _standardize_thread_columns(self, df: pd.DataFrame, standard_name: str) -> pd.DataFrame:
        """Standardize thread column names"""
        if df.empty:
            return df
        
        column_mapping = {
            'thread': ['Thread', 'Size', 'Thread_Size', 'Nominal_Size', 'Basic_Major_Diameter'],
            'class': ['Class', 'Tolerance', 'Tolerance_Class', 'Thread_Class'],
            'pitch_diameter': ['Pitch_Diameter', 'Pitch_Dia', 'Pitch_Diameter_Min']
        }
        
        # Apply column mapping
        for target_col, possible_names in column_mapping.items():
            found_col = self._find_column(df, possible_names)
            if found_col and found_col != target_col:
                df = df.rename(columns={found_col: target_col})
        
        # Ensure standard column exists
        if 'Standard' not in df.columns:
            df['Standard'] = standard_name
        
        return df
    
    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find column using exact or partial matching"""
        # First try exact match
        for col in df.columns:
            if col in possible_names:
                return col
        
        # Then try case-insensitive partial match
        for col in df.columns:
            col_lower = col.lower()
            for name in possible_names:
                if name.lower() in col_lower:
                    return col
        
        return None
    
    def get_data_quality_report(self) -> Dict[str, Any]:
        """Get comprehensive data quality report"""
        return self.quality_metrics

# Initialize data loader
data_loader = DataLoader()

# ======================================================
# ENHANCED CONFIGURATION & ERROR HANDLING
# ======================================================
class AppConfig:
    """Enhanced application configuration management"""
    
    def __init__(self):
        self.default_config = {
            'data_sources': {
                'main_data': data_config.primary_sources['main_data']['google'],
                'me_chem_data': data_config.primary_sources['me_chem_data']['google'],
                'iso4014': data_config.primary_sources['iso4014']['google'],
                'din7991': data_config.primary_sources['din7991']['google'],
                'asme_b18_3': data_config.primary_sources['asme_b18_3']['google'],
                'thread_files': data_config.thread_files
            },
            'ui': {
                'theme': 'light',
                'page_title': 'JSC Industries - Fastener Intelligence',
                'auto_refresh': True,
                'show_quality_indicators': True
            },
            'features': {
                'batch_processing': True,
                'analytics': True,
                'export_enabled': True,
                'calculation_history': True
            },
            'calculations': {
                'default_material': 'Carbon Steel',
                'default_units': 'mm',
                'precision': 4
            }
        }
        
        self.user_prefs = {
            'default_standard': 'ASME B1.1',
            'preferred_units': 'metric',
            'recent_searches': [],
            'favorite_filters': {},
            'theme_preference': 'light',
            'auto_save': True
        }
    
    def load_config(self):
        """Load configuration from session state"""
        if 'app_config' not in st.session_state:
            st.session_state.app_config = self.default_config
        return st.session_state.app_config
    
    def save_user_preferences(self):
        """Save user preferences to session state"""
        if 'user_prefs' not in st.session_state:
            st.session_state.user_prefs = self.user_prefs
    
    def update_preference(self, key: str, value: Any):
        """Update user preference"""
        if 'user_prefs' in st.session_state:
            st.session_state.user_prefs[key] = value

# Initialize app configuration
app_config = AppConfig()

# ======================================================
# ENHANCED SESSION STATE MANAGEMENT
# ======================================================
class SessionManager:
    """Enhanced session state management"""
    
    def __init__(self):
        self.defaults = {
            # UI State
            "selected_section": None,
            "debug_mode": False,
            "section_a_view": True,
            "section_b_view": True,
            "section_c_view": True,
            "show_professional_card": False,
            
            # Filter States
            "current_filters": {},
            "current_filters_dimensional": {},
            "current_filters_thread": {},
            "current_filters_material": {},
            "product_intelligence_filters": {},
            "section_a_filters": {},
            "section_b_filters": {},
            "section_c_filters": {},
            
            # Current Selections
            "section_a_current_product": "All",
            "section_a_current_series": "All",
            "section_a_current_standard": "All",
            "section_a_current_size": "All",
            "section_a_current_grade": "All",
            "section_b_current_standard": "All",
            "section_b_current_size": "All",
            "section_b_current_class": "All",
            "section_c_current_class": "All",
            "section_c_current_standard": "All",
            
            # Results
            "section_a_results": pd.DataFrame(),
            "section_b_results": pd.DataFrame(),
            "section_c_results": pd.DataFrame(),
            "combined_results": pd.DataFrame(),
            "batch_result_df": None,
            "multi_search_products": [],
            
            # Data State
            "me_chem_columns": [],
            "property_classes": [],
            "din7991_loaded": False,
            "asme_b18_3_loaded": False,
            "dimensional_standards_count": 0,
            "available_products": {},
            "available_series": {},
            "thread_data_cache": {},
            
            # Calculation State
            "calculation_history": [],
            "batch_calculation_results": pd.DataFrame(),
            "selected_product_details": None,
            
            # Weight Calculator State
            "weight_calc_product": "Select Product",
            "weight_calc_series": "Select Series",
            "weight_calc_standard": "Select Standard",
            "weight_calc_size": "Select Size",
            "weight_calc_grade": "Select Grade",
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
            "weight_form_submitted": False,
            
            # Export State
            "export_format": "csv"
        }
    
    def initialize(self):
        """Initialize all session state variables"""
        for key, value in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        # Load configurations
        app_config.load_config()
        app_config.save_user_preferences()
        
        logger.info("Session state initialized successfully")
    
    def reset_section(self, section: str):
        """Reset specific section state"""
        if section == "all":
            for key in self.defaults.keys():
                if key.endswith('_results') or key.endswith('_filters'):
                    st.session_state[key] = self.defaults[key]
        elif section == "a":
            st.session_state.section_a_results = pd.DataFrame()
            st.session_state.section_a_filters = {}
        elif section == "b":
            st.session_state.section_b_results = pd.DataFrame()
            st.session_state.section_b_filters = {}
        elif section == "c":
            st.session_state.section_c_results = pd.DataFrame()
            st.session_state.section_c_filters = {}
        
        logger.info(f"Reset section: {section}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get session state summary for debugging"""
        summary = {}
        for key in self.defaults.keys():
            value = st.session_state.get(key)
            if isinstance(value, pd.DataFrame):
                summary[key] = f"DataFrame({value.shape})"
            elif isinstance(value, (list, dict)):
                summary[key] = f"{type(value).__name__}({len(value)})"
            else:
                summary[key] = value
        return summary

# Initialize session manager
session_manager = SessionManager()

# ======================================================
# ENHANCED DATA PROCESSING UTILITIES
# ======================================================
class DataProcessor:
    """Enhanced data processing utilities"""
    
    @staticmethod
    def size_to_float(size_str: str) -> float:
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
            logger.warning(f"Error converting size to float: {size_str} - {e}")
            return 0.0
    
    @staticmethod
    def safe_sort_sizes(size_list: List[str]) -> List[str]:
        """Safely sort size list with multiple fallbacks"""
        if not size_list or len(size_list) == 0:
            return []
        
        try:
            return sorted(size_list, key=lambda x: (DataProcessor.size_to_float(x), str(x)))
        except Exception as e:
            logger.warning(f"Primary sort failed, using string sort: {e}")
            try:
                return sorted(size_list, key=str)
            except:
                return list(size_list)
    
    @staticmethod
    def get_safe_size_options(temp_df: pd.DataFrame) -> List[str]:
        """Completely safe way to get size options"""
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
                sorted_sizes = DataProcessor.safe_sort_sizes(unique_sizes)
                size_options.extend(sorted_sizes)
            else:
                return ["All"]
        except Exception as e:
            logger.warning(f"Size processing warning: {str(e)}")
            try:
                unique_sizes = temp_df['Size'].dropna().unique()
                unique_sizes = [str(size) for size in unique_sizes if str(size).strip() != '']
                size_options.extend(list(unique_sizes))
            except:
                pass
        
        return size_options
    
    @staticmethod
    def convert_to_mm(value: float, from_unit: str) -> float:
        """Convert any unit to millimeters - FIXED: No unnecessary conversion"""
        try:
            if pd.isna(value):
                return 0.0
            
            value = float(value)
            
            # Only convert if the unit is NOT mm
            if from_unit == 'mm':
                return value  # Already in mm, no conversion needed
            elif from_unit == 'inch':
                return value * 25.4  # Convert inches to mm
            elif from_unit == 'ft':
                return value * 304.8  # Convert feet to mm
            elif from_unit == 'meter':
                return value * 1000  # Convert meters to mm
            else:
                return value  # Assume mm if unknown unit
        except Exception as e:
            logger.warning(f"Unit conversion error: {str(e)}")
            return value
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: List[str] = []) -> Tuple[bool, str]:
        """Validate dataframe structure"""
        if df.empty:
            return False, "DataFrame is empty"
        
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        return True, "Valid"

# Initialize data processor
data_processor = DataProcessor()

# ======================================================
# ENHANCED PRODUCT DATA MANAGEMENT
# ======================================================
class ProductManager:
    """Enhanced product data management with fallback support"""
    
    def __init__(self):
        self.standard_products = {}
        self.standard_series = {}
        self.dimensional_standards_count = 0
    
    def process_standard_data(self) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
        """Process all standard data with enhanced fallback support"""
        logger.info("Processing standard data...")
        
        # Load all data sources
        df = data_loader.safe_load_excel_enhanced("main_data")
        df_iso4014 = data_loader.safe_load_excel_enhanced("iso4014")
        df_din7991 = data_loader.safe_load_excel_enhanced("din7991")
        df_asme_b18_3 = data_loader.safe_load_excel_enhanced("asme_b18_3")
        
        # Process ASME B18.2.1
        self._process_asme_b18_2_1(df)
        
        # Process ASME B18.3
        self._process_asme_b18_3(df_asme_b18_3)
        
        # Process DIN-7991
        self._process_din7991(df_din7991)
        
        # Process ISO 4014
        self._process_iso4014(df_iso4014)
        
        # Add Threaded Rod to all standards
        self._add_threaded_rod_to_all()
        
        # Count dimensional standards
        self._count_dimensional_standards(df, df_iso4014, df_din7991, df_asme_b18_3)
        
        # Store in session state
        st.session_state.available_products = self.standard_products
        st.session_state.available_series = self.standard_series
        st.session_state.dimensional_standards_count = self.dimensional_standards_count
        
        logger.info("Standard data processing completed")
        return self.standard_products, self.standard_series
    
    def _process_asme_b18_2_1(self, df: pd.DataFrame):
        """Process ASME B18.2.1 data"""
        if not df.empty and 'Product' in df.columns:
            asme_products = df['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in asme_products if p and str(p).strip() != '']
            self.standard_products['ASME B18.2.1'] = ["All"] + sorted(cleaned_products)
        else:
            self.standard_products['ASME B18.2.1'] = data_config.fallback_data['products']['ASME B18.2.1']
        self.standard_series['ASME B18.2.1'] = "Inch"
    
    def _process_asme_b18_3(self, df: pd.DataFrame):
        """Process ASME B18.3 data"""
        if not df.empty and 'Product' in df.columns:
            asme_b18_3_products = df['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in asme_b18_3_products if p and str(p).strip() != '']
            self.standard_products['ASME B18.3'] = ["All"] + sorted(cleaned_products)
        else:
            self.standard_products['ASME B18.3'] = data_config.fallback_data['products']['ASME B18.3']
        self.standard_series['ASME B18.3'] = "Inch"
        
        # Update session state
        st.session_state.asme_b18_3_loaded = not df.empty
    
    def _process_din7991(self, df: pd.DataFrame):
        """Process DIN-7991 data"""
        if not df.empty and 'Product' in df.columns:
            din_products = df['Product'].dropna().unique().tolist()
            cleaned_products = [str(p).strip() for p in din_products if p and str(p).strip() != '']
            self.standard_products['DIN-7991'] = ["All"] + sorted(cleaned_products)
        else:
            self.standard_products['DIN-7991'] = data_config.fallback_data['products']['DIN-7991']
        self.standard_series['DIN-7991'] = "Metric"
        
        # Update session state
        st.session_state.din7991_loaded = not df.empty
    
    def _process_iso4014(self, df: pd.DataFrame):
        """Process ISO 4014 data"""
        if not df.empty:
            product_col = None
            for col in df.columns:
                if 'product' in col.lower():
                    product_col = col
                    break
            
            if product_col:
                iso_products = df[product_col].dropna().unique().tolist()
                cleaned_products = [str(p).strip() for p in iso_products if p and str(p).strip() != '']
                self.standard_products['ISO 4014'] = ["All"] + sorted(cleaned_products)
            else:
                self.standard_products['ISO 4014'] = data_config.fallback_data['products']['ISO 4014']
        else:
            self.standard_products['ISO 4014'] = data_config.fallback_data['products']['ISO 4014']
        self.standard_series['ISO 4014'] = "Metric"
    
    def _add_threaded_rod_to_all(self):
        """Add Threaded Rod to all standards"""
        for standard in self.standard_products:
            if "Threaded Rod" not in self.standard_products[standard]:
                self.standard_products[standard] = ["All", "Threaded Rod"] + [
                    p for p in self.standard_products[standard] if p != "All" and p != "Threaded Rod"
                ]
    
    def _count_dimensional_standards(self, *dataframes):
        """Count available dimensional standards"""
        self.dimensional_standards_count = sum(1 for df in dataframes if not df.empty)
    
    def get_available_products(self) -> List[str]:
        """Get all available products from standards database"""
        all_products = set()
        for standard_products_list in st.session_state.available_products.values():
            all_products.update(standard_products_list)
        return ["Select Product"] + sorted([p for p in all_products if p != "All"])
    
    def get_series_for_product(self, product: str) -> List[str]:
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
    
    def get_standards_for_product_series(self, product: str, series: str) -> List[str]:
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
    
    def get_sizes_for_standard_product(self, standard: str, product: str) -> List[str]:
        """Get available sizes for specific standard and product"""
        if standard == "Select Standard" or product == "Select Product":
            return ["Select Size"]
        
        # Get the appropriate dataframe based on standard
        if standard == "ASME B18.2.1":
            temp_df = data_loader.safe_load_excel_enhanced("main_data")
        elif standard == "ISO 4014":
            temp_df = data_loader.safe_load_excel_enhanced("iso4014")
        elif standard == "DIN-7991":
            temp_df = data_loader.safe_load_excel_enhanced("din7991")
        elif standard == "ASME B18.3":
            temp_df = data_loader.safe_load_excel_enhanced("asme_b18_3")
        else:
            return ["Select Size"]
        
        # Filter by product if specified
        if product != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product]
        
        # Get size options
        size_options = data_processor.get_safe_size_options(temp_df)
        
        return ["Select Size"] + [size for size in size_options if size != "All"]

# Initialize product manager
product_manager = ProductManager()

# ======================================================
# ENHANCED MECHANICAL & CHEMICAL DATA PROCESSING
# ======================================================
class MechanicalChemicalProcessor:
    """Enhanced mechanical and chemical data processing"""
    
    def __init__(self):
        self.me_chem_columns = []
        self.property_classes = []
    
    def process_mechanical_chemical_data(self) -> Tuple[List[str], List[str]]:
        """Process and extract ALL property classes from Mechanical & Chemical data"""
        logger.info("Processing mechanical and chemical data...")
        
        df_mechem = data_loader.safe_load_excel_enhanced("me_chem_data")
        
        if df_mechem.empty:
            logger.warning("Mechanical & Chemical data is empty, using fallback")
            self._create_fallback_me_chem_data()
            return self.me_chem_columns, self.property_classes
        
        try:
            self.me_chem_columns = df_mechem.columns.tolist()
            
            # Find ALL possible property class columns
            property_class_cols = self._find_property_class_columns(df_mechem)
            
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
            self.property_classes = sorted(list(all_property_classes))
            
            # If no property classes found, use fallback
            if not self.property_classes:
                self._create_fallback_me_chem_data()
            else:
                # Store in session state
                st.session_state.me_chem_columns = self.me_chem_columns
                st.session_state.property_classes = self.property_classes
            
            # Debug info
            if st.session_state.debug_mode:
                logger.info(f"Found {len(self.property_classes)} property classes")
                logger.info(f"Property class columns: {property_class_cols}")
            
            return self.me_chem_columns, self.property_classes
            
        except Exception as e:
            logger.error(f"Error processing Mechanical & Chemical data: {str(e)}")
            self._create_fallback_me_chem_data()
            return self.me_chem_columns, self.property_classes
    
    def _find_property_class_columns(self, df: pd.DataFrame) -> List[str]:
        """Find property class columns in the dataframe"""
        property_class_cols = []
        possible_class_cols = ['Grade', 'Class', 'Property Class', 'Material Grade', 'Type', 'Designation', 'Material']
        
        for col in df.columns:
            col_lower = str(col).lower()
            for possible in possible_class_cols:
                if possible.lower() in col_lower:
                    property_class_cols.append(col)
                    break
        
        # If no specific class columns found, use first few columns that have string data
        if not property_class_cols:
            for col in df.columns[:3]:  # Check first 3 columns
                if df[col].dtype == 'object':  # String/object type
                    property_class_cols.append(col)
                    break
        
        return property_class_cols
    
    def _create_fallback_me_chem_data(self):
        """Create fallback mechanical and chemical data"""
        logger.info("Creating fallback mechanical and chemical data")
        self.property_classes = data_config.fallback_data['property_classes']
        self.me_chem_columns = ['Grade', 'Property Class', 'Standard', 'Tensile_Strength_Min_MPa', 
                               'Yield_Strength_Min_MPa', 'Elongation_Min_Percent', 'Carbon_Max', 'Manganese_Max']
        
        # Store in session state
        st.session_state.me_chem_columns = self.me_chem_columns
        st.session_state.property_classes = self.property_classes
    
    def get_standards_for_property_class(self, property_class: str) -> List[str]:
        """Get available standards for a specific property class"""
        if not property_class or property_class == "All":
            return []
        
        df_mechem = data_loader.safe_load_excel_enhanced("me_chem_data")
        
        if df_mechem.empty:
            return self._get_fallback_standards(property_class)
        
        try:
            # Find ALL possible standard columns
            standard_cols = self._find_standard_columns(df_mechem)
            
            # Find ALL possible property class columns
            property_class_cols = self._find_property_class_columns(df_mechem)
            
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
            
            # If still no standards found, return fallback standards
            if not matching_standards:
                return self._get_fallback_standards(property_class)
            
            return sorted(list(matching_standards))
            
        except Exception as e:
            logger.error(f"Error getting standards for {property_class}: {str(e)}")
            return self._get_fallback_standards(property_class)
    
    def _find_standard_columns(self, df: pd.DataFrame) -> List[str]:
        """Find standard columns in the dataframe"""
        standard_cols = []
        possible_standard_cols = ['Standard', 'Specification', 'Norm', 'Type', 'Designation']
        
        for col in df.columns:
            col_lower = str(col).lower()
            for possible in possible_standard_cols:
                if possible.lower() in col_lower:
                    standard_cols.append(col)
                    break
        
        # If no standard columns found, look for any column that might contain standard info
        if not standard_cols:
            for col in df.columns:
                if any(word in col.lower() for word in ['iso', 'astm', 'asme', 'din', 'bs', 'jis', 'gb']):
                    standard_cols.append(col)
                    break
        
        return standard_cols
    
    def _get_fallback_standards(self, property_class: str) -> List[str]:
        """Get fallback standards for property class"""
        fallback_standards = {
            '4.6': ['ISO 898-1'], '4.8': ['ISO 898-1'], '5.8': ['ISO 898-1'],
            '6.8': ['ISO 898-1'], '8.8': ['ISO 898-1'], '9.8': ['ISO 898-1'],
            '10.9': ['ISO 898-1'], '12.9': ['ISO 898-1'], 'A': ['ISO 4014'],
            'B': ['ISO 4014'], 'B7': ['ASTM A193'], '304': ['ASTM A276'],
            '316': ['ASTM A276'], 'A193': ['ASTM A193'], 'A320': ['ASTM A320']
        }
        
        return fallback_standards.get(property_class, ['ASTM A193', 'ASTM A320', 'ISO 898-1', 'ISO 3506', 'ASME B18.2.1'])
    
    def show_mechanical_chemical_details(self, property_class: str):
        """Show detailed mechanical and chemical properties for a selected property class"""
        if not property_class:
            return
        
        df_mechem = data_loader.safe_load_excel_enhanced("me_chem_data")
        
        if df_mechem.empty:
            st.info("Mechanical & Chemical data not available")
            return
        
        try:
            # Find ALL possible property class columns
            property_class_cols = self._find_property_class_columns(df_mechem)
            
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
            self._show_key_properties(filtered_data)
                    
        except Exception as e:
            logger.error(f"Error displaying mechanical/chemical details: {str(e)}")
            st.error(f"Error displaying details: {str(e)}")
    
    def _show_key_properties(self, filtered_data: pd.DataFrame):
        """Show key properties in a structured layout"""
        st.markdown("#### Key Properties")
        
        mechanical_props = []
        chemical_props = []
        other_props = []
        
        for col in filtered_data.columns:
            col_lower = str(col).lower()
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

# Initialize mechanical chemical processor
me_chem_processor = MechanicalChemicalProcessor()

# ======================================================
# ENHANCED THREAD DATA MANAGEMENT
# ======================================================
class ThreadDataManager:
    """Enhanced thread data management with simplified column mapping"""
    
    def __init__(self):
        self.thread_cache = {}
    
    def get_thread_data_enhanced(self, standard: str, thread_size: str = None, thread_class: str = None) -> pd.DataFrame:
        """Enhanced thread data retrieval with proper filtering"""
        df_thread = data_loader.load_thread_data_enhanced(standard)
        
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
    
    def get_thread_sizes_enhanced(self, standard: str) -> List[str]:
        """Get available thread sizes with proper data handling"""
        df_thread = data_loader.load_thread_data_enhanced(standard)
        
        if df_thread.empty or "Thread" not in df_thread.columns:
            return ["All"]
        
        try:
            # Get unique sizes and handle NaN values properly
            unique_sizes = df_thread['Thread'].dropna().unique()
            
            # Convert all sizes to string and filter out empty strings
            unique_sizes = [str(size).strip() for size in unique_sizes if str(size).strip() != '']
            
            if len(unique_sizes) > 0:
                sorted_sizes = data_processor.safe_sort_sizes(unique_sizes)
                return ["All"] + sorted_sizes
            else:
                return ["All"]
        except Exception as e:
            logger.warning(f"Thread size processing warning for {standard}: {str(e)}")
            return ["All"]
    
    def get_thread_classes_enhanced(self, standard: str) -> List[str]:
        """Get available thread classes with proper data handling"""
        df_thread = data_loader.load_thread_data_enhanced(standard)
        
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
            logger.warning(f"Thread class processing warning for {standard}: {str(e)}")
            return ["All"]
    
    def get_thread_standards_for_series(self, series: str) -> List[str]:
        """Get thread standards based on series"""
        if series == "Inch":
            return ["ASME B1.1"]
        elif series == "Metric":
            return ["ISO 965-2-98 Coarse", "ISO 965-2-98 Fine"]
        return ["Select Thread Standard"]
    
    def get_pitch_diameter_from_thread_data(self, thread_standard: str, thread_size: str, thread_class: str) -> Optional[float]:
        """Get pitch diameter from thread data for threaded rod calculation"""
        try:
            df_thread = self.get_thread_data_enhanced(thread_standard, thread_size, thread_class)
            
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
            logger.warning(f"Could not retrieve pitch diameter: {str(e)}")
            return None

# Initialize thread data manager
thread_manager = ThreadDataManager()

# ======================================================
# ENHANCED WEIGHT CALCULATION ENGINE
# ======================================================
class WeightCalculator:
    """Enhanced weight calculation engine with validation and fallbacks"""
    
    def __init__(self):
        self.material_densities = {
            "Carbon Steel": 7.85,
            "Stainless Steel": 8.00,
            "Alloy Steel": 7.85,
            "Brass": 8.50,
            "Aluminum": 2.70,
            "Copper": 8.96,
            "Titanium": 4.50,
            "Bronze": 8.80,
            "Inconel": 8.20,
            "Monel": 8.80,
            "Nickel": 8.90
        }
    
    def validate_calculation_parameters(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate all calculation parameters before execution"""
        errors = []
        
        required = ['product_type', 'diameter_type', 'material', 'length']
        missing = [field for field in required if field not in params]
        if missing:
            errors.append(f"Missing required parameters: {missing}")
        
        if 'diameter_value' in params and params['diameter_value'] <= 0:
            errors.append("Diameter must be positive")
        
        if 'length' in params and params['length'] <= 0:
            errors.append("Length must be positive")
        
        if 'material' in params and params['material'] not in self.material_densities:
            errors.append(f"Unknown material: {params['material']}")
        
        return len(errors) == 0, errors
    
    def get_material_density(self, material: str) -> float:
        """Get density for different materials in g/cm³"""
        return self.material_densities.get(material, 7.85)  # Default to carbon steel
    
    def calculate_shank_volume(self, diameter_mm: float, length_mm: float) -> float:
        """Calculate shank volume using cylinder formula"""
        try:
            # Shank volume formula: V = 0.7853 × d² × L
            shank_volume_mm3 = 0.7853 * (diameter_mm ** 2) * length_mm
            return shank_volume_mm3
        except Exception as e:
            logger.warning(f"Error calculating shank volume: {str(e)}")
            return 0.0
    
    def calculate_socket_head_volume(self, head_diameter_mm: float, head_height_mm: float) -> float:
        """Calculate volume for socket head using cylinder formula"""
        try:
            # For socket head, we use cylinder volume formula: V = 0.7853 × d² × h
            head_volume_mm3 = 0.7853 * (head_diameter_mm ** 2) * head_height_mm
            return head_volume_mm3
        except Exception as e:
            logger.warning(f"Error calculating socket head volume: {str(e)}")
            return 0.0
    
    def calculate_hex_head_volume(self, width_across_flats_mm: float, head_height_mm: float) -> float:
        """Calculate volume for hex head"""
        try:
            # Calculate Head Volume using the specific formula in mm³
            side_length_mm = width_across_flats_mm * 1.1547
            head_volume_mm3 = 0.65 * (side_length_mm**2) * head_height_mm
            return head_volume_mm3
        except Exception as e:
            logger.warning(f"Error calculating hex head volume: {str(e)}")
            return 0.0
    
    def calculate_weight(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enhanced weight calculation with proper data fetching for ALL products"""
        try:
            # Validate parameters
            is_valid, errors = self.validate_calculation_parameters(parameters)
            if not is_valid:
                logger.error(f"Calculation validation failed: {errors}")
                return None
            
            # Extract parameters
            product_type = parameters.get('product_type', 'Hex Bolt')
            diameter_type = parameters.get('diameter_type', 'Blank Diameter')
            diameter_value = parameters.get('diameter_value', 0.0)
            diameter_unit = parameters.get('diameter_unit', 'mm')
            length = parameters.get('length', 0.0)
            length_unit = parameters.get('length_unit', 'mm')
            material = parameters.get('material', 'Carbon Steel')
            standard = parameters.get('standard', 'ASME B18.2.1')
            size = parameters.get('size', 'All')
            grade = parameters.get('grade', 'All')
            
            # SPECIAL CASE: For Socket Head Products (ASME B18.3 and DIN-7991)
            socket_head_products = ["Hexagon Socket Head Cap Screws", "Hexagon Socket Countersunk Head Cap Screw"]
            
            if product_type in socket_head_products:
                return self._calculate_socket_head_weight(parameters, product_type, standard, size, grade)
            
            # For hex products, get hex head dimensions
            return self._calculate_hex_product_weight(parameters, product_type, standard, size, grade)
            
        except Exception as e:
            logger.error(f"Calculation error: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            return None
    
    def _calculate_socket_head_weight(self, parameters: Dict[str, Any], product_type: str, standard: str, size: str, grade: str) -> Optional[Dict[str, Any]]:
        """Calculate weight for socket head products"""
        try:
            # Get socket head dimensions
            head_diameter, head_height, original_unit = self._get_socket_head_dimensions(standard, product_type, size, grade)
            
            # Store original dimensions for display
            original_head_diameter = head_diameter
            original_head_height = head_height
            
            # Extract parameters
            diameter_type = parameters.get('diameter_type', 'Blank Diameter')
            diameter_value = parameters.get('diameter_value', 0.0)
            diameter_unit = parameters.get('diameter_unit', 'mm')
            length = parameters.get('length', 0.0)
            length_unit = parameters.get('length_unit', 'mm')
            material = parameters.get('material', 'Carbon Steel')
            
            # Convert dimensions to mm only if needed
            diameter_mm = data_processor.convert_to_mm(diameter_value, diameter_unit)
            length_mm = data_processor.convert_to_mm(length, length_unit)
            
            # Convert head dimensions to mm (they should already be in mm from database)
            if head_diameter is not None:
                head_diameter_mm = data_processor.convert_to_mm(head_diameter, original_unit)
            else:
                head_diameter_mm = diameter_mm * 1.5  # Default ratio if not available
            
            if head_height is not None:
                head_height_mm = data_processor.convert_to_mm(head_height, original_unit)
            else:
                head_height_mm = diameter_mm * 0.65  # Default ratio if not available
            
            # Get material density in g/cm³
            density_g_cm3 = self.get_material_density(material)
            
            # Calculate volumes in mm³
            shank_volume_mm3 = self.calculate_shank_volume(diameter_mm, length_mm)
            head_volume_mm3 = self.calculate_socket_head_volume(head_diameter_mm, head_height_mm)
            total_volume_mm3 = shank_volume_mm3 + head_volume_mm3
            
            # Convert mm³ to cm³ for weight calculation
            total_volume_cm3 = total_volume_mm3 / 1000
            
            # Calculate Weight in grams and kg
            weight_g = total_volume_cm3 * density_g_cm3
            weight_kg = weight_g / 1000
            weight_lb = weight_kg * 2.20462
            
            return {
                'weight_kg': weight_kg,
                'weight_g': weight_g,
                'weight_lb': weight_lb,
                'shank_volume_mm3': shank_volume_mm3,
                'head_volume_mm3': head_volume_mm3,
                'total_volume_mm3': total_volume_mm3,
                'total_volume_cm3': total_volume_cm3,
                'diameter_mm': diameter_mm,
                'length_mm': length_mm,
                'head_diameter_mm': head_diameter_mm,
                'head_height_mm': head_height_mm,
                'density_g_cm3': density_g_cm3,
                'original_diameter': f"{diameter_value} {diameter_unit}",
                'original_length': f"{length} {length_unit}",
                'original_head_diameter': f"{head_diameter} {original_unit}" if head_diameter else "N/A",
                'original_head_height': f"{head_height} {original_unit}" if head_height else "N/A",
                'calculation_method': 'Socket Head Formula',
                'formula_details': {
                    'shank_volume_formula': '0.7853 × (diameter)² × length (mm³)',
                    'head_volume_formula': '0.7853 × (head_diameter_min)² × head_height_min (mm³)',
                    'total_volume_formula': 'shank_volume + head_volume (mm³)',
                    'volume_conversion': 'mm³ to cm³: divide by 1000',
                    'weight_formula': 'total_volume_cm³ × density_g/cm³'
                },
                'dimensions_used': {
                    'diameter_input': f"{diameter_value:.4f} {diameter_unit}",
                    'diameter_calculation_mm': f"{diameter_mm:.4f}",
                    'length_input': f"{length:.4f} {length_unit}",
                    'length_calculation_mm': f"{length_mm:.4f}",
                    'head_diameter_input': f"{head_diameter:.4f} {original_unit}" if head_diameter else "Estimated",
                    'head_diameter_calculation_mm': f"{head_diameter_mm:.4f}",
                    'head_height_input': f"{head_height:.4f} {original_unit}" if head_height else "Estimated",
                    'head_height_calculation_mm': f"{head_height_mm:.4f}",
                    'shank_volume_mm3': f"{shank_volume_mm3:.4f}",
                    'head_volume_mm3': f"{head_volume_mm3:.4f}",
                    'total_volume_mm3': f"{total_volume_mm3:.4f}",
                    'total_volume_cm3': f"{total_volume_cm3:.4f}",
                    'density_g_cm3': f"{density_g_cm3:.4f}"
                }
            }
            
        except Exception as e:
            logger.error(f"Socket product calculation error: {str(e)}")
            return None
    
    def _calculate_hex_product_weight(self, parameters: Dict[str, Any], product_type: str, standard: str, size: str, grade: str) -> Optional[Dict[str, Any]]:
        """Calculate weight for hex products"""
        try:
            # Get hex head dimensions
            width_across_flats, head_height, original_unit = self._get_hex_head_dimensions(standard, product_type, size, grade)
            
            # Store original dimensions for display
            original_width_across_flats = width_across_flats
            original_head_height = head_height
            
            # Extract parameters
            diameter_type = parameters.get('diameter_type', 'Blank Diameter')
            diameter_value = parameters.get('diameter_value', 0.0)
            diameter_unit = parameters.get('diameter_unit', 'mm')
            length = parameters.get('length', 0.0)
            length_unit = parameters.get('length_unit', 'mm')
            material = parameters.get('material', 'Carbon Steel')
            
            # Convert dimensions to mm only if needed
            diameter_mm = data_processor.convert_to_mm(diameter_value, diameter_unit)
            length_mm = data_processor.convert_to_mm(length, length_unit)
            
            # Convert head dimensions to mm (they should already be in mm from database)
            if width_across_flats is not None:
                width_across_flats_mm = data_processor.convert_to_mm(width_across_flats, original_unit)
            else:
                width_across_flats_mm = diameter_mm * 1.5  # Default ratio if not available
            
            if head_height is not None:
                head_height_mm = data_processor.convert_to_mm(head_height, original_unit)
            else:
                head_height_mm = diameter_mm * 0.65  # Default ratio if not available
            
            # SPECIAL CASE: For Pitch Diameter from thread data in Inch series
            if (diameter_type == "Pitch Diameter" and 
                'pitch_diameter_value' in st.session_state and
                st.session_state.pitch_diameter_value is not None):
                
                # Use the pitch diameter from thread data and convert from inches to mm if needed
                pitch_diameter = st.session_state.pitch_diameter_value
                # Thread data for ASME B1.1 is in inches, so convert to mm
                if diameter_unit == 'inch':
                    diameter_mm = pitch_diameter * 25.4
                else:
                    diameter_mm = pitch_diameter
            
            # Get material density in g/cm³
            density_g_cm3 = self.get_material_density(material)
            
            # For Threaded Rod, use simple cylinder volume calculation in mm³
            if product_type == "Threaded Rod":
                return self._calculate_threaded_rod_weight(diameter_mm, length_mm, density_g_cm3, diameter_value, diameter_unit, length, length_unit)
            
            # For hex products, use rectified hex product formula in mm³
            hex_products = ["Hex Bolt", "Heavy Hex Bolt", "Hex Cap Screws", "Heavy Hex Screws"]
            if product_type in hex_products:
                return self._calculate_hex_product_weight_detailed(
                    diameter_mm, length_mm, width_across_flats_mm, head_height_mm, density_g_cm3,
                    diameter_value, diameter_unit, length, length_unit, 
                    original_width_across_flats, original_head_height, original_unit
                )
            
            # For other products, use simple cylinder calculation in mm³
            return self._calculate_generic_weight(diameter_mm, length_mm, density_g_cm3, diameter_value, diameter_unit, length, length_unit)
            
        except Exception as e:
            logger.error(f"Hex product calculation error: {str(e)}")
            return None
    
    def _calculate_threaded_rod_weight(self, diameter_mm: float, length_mm: float, density_g_cm3: float,
                                     diameter_value: float, diameter_unit: str, length: float, length_unit: str) -> Dict[str, Any]:
        """Calculate weight for threaded rod"""
        shank_volume_mm3 = self.calculate_shank_volume(diameter_mm, length_mm)
        volume_cm3 = shank_volume_mm3 / 1000
        weight_g = volume_cm3 * density_g_cm3
        weight_kg = weight_g / 1000
        weight_lb = weight_kg * 2.20462
        
        return {
            'weight_kg': weight_kg,
            'weight_g': weight_g,
            'weight_lb': weight_lb,
            'volume_mm3': shank_volume_mm3,
            'volume_cm3': volume_cm3,
            'density_g_cm3': density_g_cm3,
            'diameter_mm': diameter_mm,
            'length_mm': length_mm,
            'original_diameter': f"{diameter_value} {diameter_unit}",
            'original_length': f"{length} {length_unit}",
            'calculation_method': 'Threaded Rod Cylinder Formula',
            'dimensions_used': {
                'diameter_input': f"{diameter_value:.4f} {diameter_unit}",
                'diameter_calculation_mm': f"{diameter_mm:.4f}",
                'length_input': f"{length:.4f} {length_unit}",
                'length_calculation_mm': f"{length_mm:.4f}",
                'volume_mm3': f"{shank_volume_mm3:.4f}",
                'volume_cm3': f"{volume_cm3:.4f}",
                'density_g_cm3': f"{density_g_cm3:.4f}"
            }
        }
    
    def _calculate_hex_product_weight_detailed(self, diameter_mm: float, length_mm: float, width_across_flats_mm: float,
                                             head_height_mm: float, density_g_cm3: float, diameter_value: float,
                                             diameter_unit: str, length: float, length_unit: str,
                                             original_width_across_flats: float, original_head_height: float,
                                             original_unit: str) -> Dict[str, Any]:
        """Calculate detailed weight for hex products"""
        # Calculate volumes in mm³
        shank_volume_mm3 = self.calculate_shank_volume(diameter_mm, length_mm)
        head_volume_mm3 = self.calculate_hex_head_volume(width_across_flats_mm, head_height_mm)
        total_volume_mm3 = shank_volume_mm3 + head_volume_mm3
        
        # Convert mm³ to cm³ for weight calculation
        total_volume_cm3 = total_volume_mm3 / 1000
        
        # Calculate Weight in grams and kg
        weight_g = total_volume_cm3 * density_g_cm3
        weight_kg = weight_g / 1000
        weight_lb = weight_kg * 2.20462
        
        # Calculate side length for display
        side_length_mm = width_across_flats_mm * 1.1547
        
        return {
            'weight_kg': weight_kg,
            'weight_g': weight_g,
            'weight_lb': weight_lb,
            'shank_volume_mm3': shank_volume_mm3,
            'head_volume_mm3': head_volume_mm3,
            'total_volume_mm3': total_volume_mm3,
            'total_volume_cm3': total_volume_cm3,
            'diameter_mm': diameter_mm,
            'length_mm': length_mm,
            'width_across_flats_mm': width_across_flats_mm,
            'head_height_mm': head_height_mm,
            'side_length_mm': side_length_mm,
            'density_g_cm3': density_g_cm3,
            'original_diameter': f"{diameter_value} {diameter_unit}",
            'original_length': f"{length} {length_unit}",
            'original_width_across_flats': f"{original_width_across_flats} {original_unit}" if original_width_across_flats else "N/A",
            'original_head_height': f"{original_head_height} {original_unit}" if original_head_height else "N/A",
            'calculation_method': 'Hex Product Formula',
            'formula_details': {
                'shank_volume_formula': '0.7853 × (diameter)² × length (mm³)',
                'head_volume_formula': '0.65 × side_length² × head_height (mm³)',
                'side_length_formula': 'width_across_flats × 1.1547 (mm)',
                'total_volume_formula': 'shank_volume + head_volume (mm³)',
                'volume_conversion': 'mm³ to cm³: divide by 1000',
                'weight_formula': 'total_volume_cm³ × density_g/cm³'
            },
            'dimensions_used': {
                'diameter_input': f"{diameter_value:.4f} {diameter_unit}",
                'diameter_calculation_mm': f"{diameter_mm:.4f}",
                'length_input': f"{length:.4f} {length_unit}",
                'length_calculation_mm': f"{length_mm:.4f}",
                'width_across_flats_input': f"{original_width_across_flats:.4f} {original_unit}" if original_width_across_flats else "Estimated",
                'width_across_flats_calculation_mm': f"{width_across_flats_mm:.4f}",
                'head_height_input': f"{original_head_height:.4f} {original_unit}" if original_head_height else "Estimated",
                'head_height_calculation_mm': f"{head_height_mm:.4f}",
                'side_length_calculation_mm': f"{side_length_mm:.4f}",
                'shank_volume_mm3': f"{shank_volume_mm3:.4f}",
                'head_volume_mm3': f"{head_volume_mm3:.4f}",
                'total_volume_mm3': f"{total_volume_mm3:.4f}",
                'total_volume_cm3': f"{total_volume_cm3:.4f}",
                'density_g_cm3': f"{density_g_cm3:.4f}"
            }
        }
    
    def _calculate_generic_weight(self, diameter_mm: float, length_mm: float, density_g_cm3: float,
                                diameter_value: float, diameter_unit: str, length: float, length_unit: str) -> Dict[str, Any]:
        """Calculate weight for generic products"""
        shank_volume_mm3 = self.calculate_shank_volume(diameter_mm, length_mm)
        volume_cm3 = shank_volume_mm3 / 1000
        weight_g = volume_cm3 * density_g_cm3
        weight_kg = weight_g / 1000
        weight_lb = weight_kg * 2.20462
        
        return {
            'weight_kg': weight_kg,
            'weight_g': weight_g,
            'weight_lb': weight_lb,
            'volume_mm3': shank_volume_mm3,
            'volume_cm3': volume_cm3,
            'density_g_cm3': density_g_cm3,
            'diameter_mm': diameter_mm,
            'length_mm': length_mm,
            'original_diameter': f"{diameter_value:.4f} {diameter_unit}",
            'original_length': f"{length:.4f} {length_unit}",
            'calculation_method': 'Standard Cylinder Formula',
            'dimensions_used': {
                'diameter_input': f"{diameter_value:.4f} {diameter_unit}",
                'diameter_calculation_mm': f"{diameter_mm:.4f}",
                'length_input': f"{length:.4f} {length_unit}",
                'length_calculation_mm': f"{length_mm:.4f}",
                'volume_mm3': f"{shank_volume_mm3:.4f}",
                'volume_cm3': f"{volume_cm3:.4f}",
                'density_g_cm3': f"{density_g_cm3:.4f}"
            }
        }
    
    def _get_socket_head_dimensions(self, standard: str, product: str, size: str, grade: str) -> Tuple[Optional[float], Optional[float], str]:
        """Get socket head dimensions from appropriate source"""
        if standard == "ASME B18.3":
            return self._get_asme_b18_3_dimensions(product, size)
        elif standard == "DIN-7991":
            return self._get_din7991_dimensions(product, size)
        else:
            return None, None, "unknown"
    
    def _get_asme_b18_3_dimensions(self, product: str, size: str) -> Tuple[Optional[float], Optional[float], str]:
        """Get head diameter and head height for ASME B18.3 socket head cap screws"""
        try:
            temp_df = data_loader.safe_load_excel_enhanced("asme_b18_3")
            original_unit = "inch"  # ASME B18.3 data is in inches
            
            # Filter by product and size
            if 'Product' in temp_df.columns and product != "All":
                temp_df = temp_df[temp_df['Product'].str.contains('Socket Head', na=False, case=False)]
            
            if 'Size' in temp_df.columns and size != "All":
                # Normalize size comparison - handle different formats
                temp_df['Size_Normalized'] = temp_df['Size'].astype(str).str.strip()
                size_normalized = str(size).strip()
                temp_df = temp_df[temp_df['Size_Normalized'] == size_normalized]
            
            if temp_df.empty:
                logger.warning(f"No ASME B18.3 data found for {product} size {size}")
                return None, None, original_unit
            
            # Find Head Diameter (Min) column
            head_dia_col = self._find_column(temp_df, ['Head Diameter (Min)', 'Head_Diameter_Min', 'Head Dia Min', 'Head Diameter Min'])
            head_height_col = self._find_column(temp_df, ['Head Height (Min)', 'Head_Height_Min', 'Head Height Min', 'Head_Ht_Min'])
            
            head_diameter = None
            head_height = None
            
            # Get Head Diameter (Min) value
            if head_dia_col and head_dia_col in temp_df.columns:
                head_diameter_val = temp_df[head_dia_col].iloc[0]
                if pd.notna(head_diameter_val):
                    head_diameter = float(head_diameter_val)
            
            # Get Head Height (Min) value
            if head_height_col and head_height_col in temp_df.columns:
                head_height_val = temp_df[head_height_col].iloc[0]
                if pd.notna(head_height_val):
                    head_height = float(head_height_val)
            
            return head_diameter, head_height, original_unit
                
        except Exception as e:
            logger.error(f"Error getting ASME B18.3 dimensions: {str(e)}")
            return None, None, "inch"
    
    def _get_din7991_dimensions(self, product: str, size: str) -> Tuple[Optional[float], Optional[float], str]:
        """Get head diameter and head height for DIN-7991 socket countersunk head cap screws"""
        try:
            temp_df = data_loader.safe_load_excel_enhanced("din7991")
            original_unit = "mm"  # DIN-7991 data is in mm
            
            # Filter by product and size
            if 'Product' in temp_df.columns and product != "All":
                temp_df = temp_df[temp_df['Product'] == product]
            
            if 'Size' in temp_df.columns and size != "All":
                # Normalize size comparison
                temp_df = temp_df[temp_df['Size'].astype(str).str.strip() == str(size).strip()]
            
            if temp_df.empty:
                return None, None, original_unit
            
            # Look for Head Diameter (dk) and Head Height (k) columns
            head_dia_col = self._find_column(temp_df, ['dk', 'head_diameter', 'head_dia'])
            head_height_col = self._find_column(temp_df, ['k', 'head_height', 'head_height'])
            
            head_diameter = None
            head_height = None
            
            if head_dia_col and head_dia_col in temp_df.columns:
                head_diameter = temp_df[head_dia_col].iloc[0]
                if pd.notna(head_diameter):
                    head_diameter = float(head_diameter)
            
            if head_height_col and head_height_col in temp_df.columns:
                head_height = temp_df[head_height_col].iloc[0]
                if pd.notna(head_height):
                    head_height = float(head_height)
            
            return head_diameter, head_height, original_unit
            
        except Exception as e:
            logger.warning(f"Error getting DIN-7991 dimensions: {str(e)}")
            return None, None, "mm"
    
    def _get_hex_head_dimensions(self, standard: str, product: str, size: str, grade: str) -> Tuple[Optional[float], Optional[float], str]:
        """Get width across flats and head height for hex products"""
        try:
            # Get the appropriate dataframe based on standard
            if standard == "ASME B18.2.1":
                temp_df = data_loader.safe_load_excel_enhanced("main_data")
                original_unit = "inch"
            elif standard == "ISO 4014":
                temp_df = data_loader.safe_load_excel_enhanced("iso4014")
                original_unit = "mm"
            elif standard == "DIN-7991":
                temp_df = data_loader.safe_load_excel_enhanced("din7991")
                original_unit = "mm"
            elif standard == "ASME B18.3":
                temp_df = data_loader.safe_load_excel_enhanced("asme_b18_3")
                original_unit = "inch"
            else:
                return None, None, "unknown"
            
            # Filter by product and size
            if 'Product' in temp_df.columns and product != "All":
                temp_df = temp_df[temp_df['Product'] == product]
            
            if 'Size' in temp_df.columns and size != "All":
                # Normalize size comparison
                temp_df = temp_df[temp_df['Size'].astype(str).str.strip() == str(size).strip()]
            
            # Filter by grade if specified (only for ISO 4014)
            if standard == "ISO 4014" and grade != "All" and 'Product_Grade' in temp_df.columns:
                temp_df = temp_df[temp_df['Product_Grade'] == grade]
            
            if temp_df.empty:
                return None, None, original_unit
            
            # Look for width across flats column
            width_col = self._find_column(temp_df, ['Width_Across_Flats_Min', 'W_Across_Flats_Min', 'Width_Min'])
            height_col = self._find_column(temp_df, ['Head_Height_Min', 'Head_Height', 'Height_Min'])
            
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
            
            return width_across_flats, head_height, original_unit
            
        except Exception as e:
            logger.warning(f"Error getting hex head dimensions: {str(e)}")
            return None, None, "unknown"
    
    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find column using exact or partial matching"""
        # First try exact match
        for col in df.columns:
            if col in possible_names:
                return col
        
        # Then try case-insensitive partial match
        for col in df.columns:
            col_lower = col.lower()
            for name in possible_names:
                if name.lower() in col_lower:
                    return col
        
        return None

# Initialize weight calculator
weight_calculator = WeightCalculator()

# ======================================================
# ENHANCED UI COMPONENTS
# ======================================================
class UIComponents:
    """Enhanced UI components with better user experience"""
    
    @staticmethod
    def show_loading_skeleton():
        """Show loading skeleton while data loads"""
        with st.container():
            st.markdown("""
            <div style="padding: 2rem; text-align: center;">
                <div class="skeleton-loader"></div>
                <p>Loading data...</p>
            </div>
            <style>
            .skeleton-loader {
                width: 100%;
                height: 20px;
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: loading 1.5s infinite;
                border-radius: 4px;
                margin: 1rem 0;
            }
            @keyframes loading {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
            </style>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def show_empty_state(message: str, icon: str = "📊"):
        """Show consistent empty states"""
        st.markdown(f"""
        <div style="text-align: center; padding: 3rem; color: #666;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">{icon}</div>
            <h3>{message}</h3>
            <p>Try adjusting your filters or check data connections</p>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def show_data_quality_indicators():
        """Show enhanced data quality indicators"""
        st.sidebar.markdown("---")
        with st.sidebar.expander("📊 Data Quality Status"):
            quality_report = data_loader.get_data_quality_report()
            
            for source_name, metrics in quality_report.items():
                status = metrics.get('status', 'unknown')
                completeness = metrics.get('completeness', 0)
                row_count = metrics.get('row_count', 0)
                
                if status == 'loaded' and completeness > 80:
                    st.markdown(f'<div class="data-quality-indicator quality-good">{source_name}: {completeness}% Complete ({row_count} records)</div>', unsafe_allow_html=True)
                elif status == 'loaded' and completeness > 50:
                    st.markdown(f'<div class="data-quality-indicator quality-warning">{source_name}: {completeness}% Complete ({row_count} records)</div>', unsafe_allow_html=True)
                elif status == 'empty':
                    st.markdown(f'<div class="data-quality-indicator quality-error">{source_name}: Not Loaded</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="data-quality-indicator quality-warning">{source_name}: Limited Access</div>', unsafe_allow_html=True)
    
    @staticmethod
    def show_error_boundary(func):
        """Decorator to show errors gracefully"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                st.error(f"An error occurred in {func.__name__}. Please try again or contact support.")
                if st.session_state.debug_mode:
                    st.code(traceback.format_exc())
                return None
        return wrapper

# ======================================================
# ENHANCED EXPORT FUNCTIONALITY
# ======================================================
class ExportManager:
    """Enhanced export functionality"""
    
    @staticmethod
    def export_to_excel(df: pd.DataFrame, filename_prefix: str) -> Optional[str]:
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
            logger.error(f"Export error: {str(e)}")
            return None
    
    @staticmethod
    def enhanced_export_data(filtered_df: pd.DataFrame, export_format: str):
        """Enhanced export with multiple format options"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_format == "Excel":
            excel_file = ExportManager.export_to_excel(filtered_df, f"fastener_data_{timestamp}")
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
# ENHANCED CALCULATION HISTORY
# ======================================================
class CalculationHistoryManager:
    """Enhanced calculation history management"""
    
    @staticmethod
    def save_calculation_history(calculation_data: Dict[str, Any]):
        """Save calculation to history"""
        if 'calculation_history' not in st.session_state:
            st.session_state.calculation_history = []
        
        calculation_data['timestamp'] = datetime.now().isoformat()
        calculation_data['id'] = hashlib.md5(str(calculation_data).encode()).hexdigest()[:8]
        
        st.session_state.calculation_history.append(calculation_data)
        
        # Keep only last 20 calculations
        if len(st.session_state.calculation_history) > 20:
            st.session_state.calculation_history = st.session_state.calculation_history[-20:]
        
        logger.info(f"Saved calculation to history: {calculation_data['id']}")
    
    @staticmethod
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
                        Weight: {calc.get('weight_kg', 'N/A'):.4f} kg
                        <br><small>{calc.get('timestamp', '')}</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No calculation history yet. Perform calculations to see history here.")

# ======================================================
# ENHANCED PAGE SETUP WITH JSC GROUP STYLING
# ======================================================
st.set_page_config(
    page_title="JSC Industries - Fastener Intelligence", 
    layout="wide",
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

# JSC Group Professional CSS with Enhanced Card Design
st.markdown("""
<style>
    :root {
        --jsc-primary: #0066b3;
        --jsc-primary-dark: #003366;
        --jsc-secondary: #00a0e3;
        --jsc-accent: #ff6b00;
        --jsc-light: #f8f9fa;
        --jsc-dark: #343a40;
        --jsc-success: #28a745;
        --jsc-warning: #ffc107;
        --jsc-danger: #dc3545;
        --jsc-gradient: linear-gradient(135deg, #0066b3 0%, #003366 100%);
        --jsc-gradient-light: linear-gradient(135deg, #00a0e3 0%, #0066b3 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    .jsc-header {
        background: var(--jsc-gradient);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .jsc-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--jsc-accent);
    }
    
    .jsc-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .jsc-header p {
        font-size: 1.2rem;
        opacity: 0.95;
        margin-bottom: 1rem;
    }
    
    .jsc-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid var(--jsc-primary);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
        position: relative;
        overflow: hidden;
    }
    
    .jsc-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: var(--jsc-gradient);
    }
    
    .jsc-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 102, 179, 0.15);
        border-left-color: var(--jsc-accent);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-left: 4px solid var(--jsc-primary);
        transition: transform 0.3s ease;
        border: 1px solid #e9ecef;
        text-align: center;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0, 102, 179, 0.15);
    }
    
    .jsc-badge {
        background: var(--jsc-gradient);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .jsc-badge-accent {
        background: var(--jsc-accent);
    }
    
    .jsc-badge-secondary {
        background: var(--jsc-secondary);
    }
    
    .jsc-badge-success {
        background: var(--jsc-success);
    }
    
    .stButton>button {
        background: var(--jsc-gradient);
        color: white;
        border: none;
        padding: 0.7rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 102, 179, 0.2);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0, 102, 179, 0.3);
        background: var(--jsc-primary-dark);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    .stButton>button[kind="primary"] {
        background: var(--jsc-gradient);
        color: white;
    }
    
    .stButton>button[kind="primary"]:hover {
        background: var(--jsc-primary-dark);
    }
    
    .stButton>button[kind="secondary"] {
        background: white;
        color: var(--jsc-primary);
        border: 2px solid var(--jsc-primary);
    }
    
    .stButton>button[kind="secondary"]:hover {
        background: var(--jsc-primary);
        color: white;
    }
    
    .css-1d391kg, .css-1lcbmhc {
        background: white;
        border-right: 1px solid #e9ecef;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, white 0%, #f8f9fa 100%);
    }
    
    .stTextInput>div>div>input, 
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>select {
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus, 
    .stNumberInput>div>div>input:focus,
    .stSelectbox>div>div>select:focus {
        border-color: var(--jsc-primary);
        box-shadow: 0 0 0 2px rgba(0, 102, 179, 0.1);
    }
    
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #e9ecef;
    }
    
    .streamlit-expanderHeader {
        background: var(--jsc-light);
        border-radius: 8px;
        border: 1px solid #e9ecef;
        font-weight: 600;
        color: var(--jsc-primary);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: white;
        border-radius: 8px 8px 0 0;
        padding: 1rem 2rem;
        border: 1px solid #e9ecef;
        border-bottom: none;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--jsc-primary);
        color: white;
    }
    
    .stProgress > div > div > div {
        background: var(--jsc-gradient);
    }
    
    .stAlert {
        border-radius: 8px;
        border: 1px solid;
    }
    
    .stAlert [data-testid="stMarkdownContainer"] {
        font-weight: 500;
    }
    
    .section-header {
        border-left: 5px solid var(--jsc-primary);
        padding-left: 1rem;
        margin: 2rem 0 1rem 0;
        color: var(--jsc-primary-dark);
        font-weight: 600;
        font-size: 1.4rem;
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
        position: relative;
        overflow: hidden;
    }
    
    .quick-action::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: var(--jsc-gradient);
    }
    
    .quick-action:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    
    .professional-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 2px solid var(--jsc-primary);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(0, 102, 179, 0.2);
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
        background: var(--jsc-gradient);
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
        color: var(--jsc-primary-dark);
        margin: 0;
    }
    
    .card-subtitle {
        font-size: 1.2rem;
        color: #6c757d;
        margin: 0.5rem 0 0 0;
    }
    
    .card-company {
        background: var(--jsc-gradient);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .spec-row {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        gap: 1rem;
        align-items: center;
        margin: 0.8rem 0;
        padding: 0.5rem;
        border-radius: 6px;
        background: #f8f9fa;
    }
    
    .spec-label-min, .spec-label-max {
        font-size: 0.85rem;
        color: #6c757d;
        text-align: center;
        font-weight: 500;
    }
    
    .spec-dimension {
        font-weight: 600;
        color: var(--jsc-primary-dark);
        text-align: center;
        padding: 0.3rem 1rem;
        background: white;
        border-radius: 4px;
        border: 1px solid #e9ecef;
    }
    
    .spec-value {
        font-weight: 600;
        color: var(--jsc-primary);
        text-align: center;
        padding: 0.3rem;
        background: white;
        border-radius: 4px;
        border: 1px solid #dee2e6;
    }
    
    .card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #e9ecef;
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    .card-actions {
        display: flex;
        gap: 1rem;
        margin-top: 1.5rem;
        justify-content: center;
    }
    
    .action-button {
        background: var(--jsc-gradient);
        color: white;
        border: none;
        padding: 0.7rem 1.5rem;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .action-button:hover {
        background: var(--jsc-primary-dark);
        transform: translateY(-2px);
    }
    
    .action-button.secondary {
        background: white;
        color: var(--jsc-primary);
        border: 2px solid var(--jsc-primary);
    }
    
    .action-button.secondary:hover {
        background: var(--jsc-primary);
        color: white;
    }
    
    .filter-section {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
        border: 1px solid #e9ecef;
        position: relative;
        overflow: hidden;
    }
    
    .filter-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: var(--jsc-gradient);
    }
    
    .filter-header {
        border-left: 4px solid var(--jsc-primary);
        padding-left: 1rem;
        margin-bottom: 1rem;
        color: var(--jsc-primary-dark);
        font-weight: 600;
        font-size: 1.2rem;
    }
    
    .independent-section {
        border: 2px solid var(--jsc-primary);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        position: relative;
        overflow: hidden;
    }
    
    .independent-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: var(--jsc-gradient);
    }
    
    .section-results {
        border: 2px solid var(--jsc-success);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #f0f8f0 0%, #ffffff 100%);
    }
    
    .combined-results {
        border: 2px solid var(--jsc-secondary);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #f0f8ff 0%, #ffffff 100%);
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
        border-left-color: var(--jsc-success);
    }
    
    .quality-warning {
        background: #fff3cd;
        color: #856404;
        border-left-color: var(--jsc-warning);
    }
    
    .quality-error {
        background: #f8d7da;
        color: #721c24;
        border-left-color: var(--jsc-danger);
    }
    
    .calculation-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid var(--jsc-success);
    }
    
    .spec-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .property-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.8rem;
        margin: 1rem 0;
    }
    
    .specification-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 1.5rem 0;
    }
    
    .jsc-footer {
        text-align: center;
        color: #6c757d;
        padding: 2rem;
        margin-top: 3rem;
        border-top: 1px solid #e9ecef;
    }
    
    @media (max-width: 768px) {
        .jsc-header {
            padding: 1.5rem !important;
        }
        
        .jsc-header h1 {
            font-size: 2rem !important;
        }
        
        .spec-grid,
        .property-grid,
        .specification-grid {
            grid-template-columns: 1fr;
        }
        
        .card-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.8rem 1rem;
        }
        
        .spec-row {
            grid-template-columns: 1fr;
            gap: 0.5rem;
        }
        
        .card-actions {
            flex-direction: column;
        }
    }
</style>
""", unsafe_allow_html=True)

# ======================================================
# MAIN APPLICATION INITIALIZATION
# ======================================================
def initialize_application():
    """Initialize the complete application"""
    logger.info("Initializing JSC Industries Fastener Intelligence Platform")
    
    # Initialize session state
    session_manager.initialize()
    
    # Load all data sources
    with st.spinner("Loading application data..."):
        # Process standard data
        product_manager.process_standard_data()
        
        # Process mechanical and chemical data
        me_chem_processor.process_mechanical_chemical_data()
    
    logger.info("Application initialization completed successfully")

# ======================================================
# ENHANCED PRODUCT DATABASE SECTION
# ======================================================
def show_enhanced_product_database():
    """Enhanced Product Intelligence Center with independent sections"""
    
    st.markdown("""
    <div class="jsc-header">
        <h1>Product Intelligence Center - Enhanced</h1>
        <p>Each section works completely independently with fallback data support</p>
        <div>
            <span class="jsc-badge">Enhanced</span>
            <span class="jsc-badge-accent">Fallback Support</span>
            <span class="jsc-badge-secondary">Robust Data</span>
            <span class="jsc-badge-success">Professional Grade</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Check data availability
    data_available = any([
        not data_loader.safe_load_excel_enhanced("main_data").empty,
        not data_loader.safe_load_excel_enhanced("me_chem_data").empty,
        not data_loader.safe_load_excel_enhanced("iso4014").empty,
        st.session_state.din7991_loaded,
        st.session_state.asme_b18_3_loaded
    ])
    
    if not data_available:
        st.warning("""
        ⚠️ **Limited Data Access** 
        Using fallback data. Some features may be limited. 
        Check your internet connection and data source accessibility for full functionality.
        """)
    
    # Section toggles
    st.markdown("### Section Controls")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        section_a_active = st.checkbox("Section A - Dimensional Specifications", 
                                     value=st.session_state.section_a_view, 
                                     key="section_a_toggle")
        st.session_state.section_a_view = section_a_active
    
    with col2:
        section_b_active = st.checkbox("Section B - Thread Specifications", 
                                     value=st.session_state.section_b_view, 
                                     key="section_b_toggle")
        st.session_state.section_b_view = section_b_active
    
    with col3:
        section_c_active = st.checkbox("Section C - Material Properties", 
                                     value=st.session_state.section_c_view, 
                                     key="section_c_toggle")
        st.session_state.section_c_view = section_c_active
    
    st.markdown("---")
    
    # SECTION A - DIMENSIONAL SPECIFICATIONS
    if st.session_state.section_a_view:
        show_section_a_dimensional_specs()
    
    # SECTION B - THREAD SPECIFICATIONS
    if st.session_state.section_b_view:
        show_section_b_thread_specs()
    
    # SECTION C - MATERIAL PROPERTIES
    if st.session_state.section_c_view:
        show_section_c_material_props()
    
    # COMBINE ALL RESULTS SECTION
    show_combined_results_section()
    
    # Quick actions
    show_quick_actions()

def show_section_a_dimensional_specs():
    """Show Section A - Dimensional Specifications"""
    st.markdown("""
    <div class="independent-section">
        <h3 class="filter-header">Section A - Dimensional Specifications</h3>
        <p><strong>Enhanced:</strong> Robust data handling with fallback support</p>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        # Product List
        all_products = product_manager.get_available_products()
        dimensional_product = st.selectbox(
            "Product List", 
            all_products, 
            key="section_a_product",
            index=all_products.index(st.session_state.section_a_current_product) if st.session_state.section_a_current_product in all_products else 0
        )
        st.session_state.section_a_current_product = dimensional_product
    
    with col2:
        # Series System
        series_options = ["All", "Inch", "Metric"]
        dimensional_series = st.selectbox(
            "Series System", 
            series_options, 
            key="section_a_series",
            index=series_options.index(st.session_state.section_a_current_series) if st.session_state.section_a_current_series in series_options else 0
        )
        st.session_state.section_a_current_series = dimensional_series
    
    with col3:
        # Standards
        available_standards = get_available_standards_for_product_series(dimensional_product, dimensional_series)
        dimensional_standard = st.selectbox(
            "Standards", 
            available_standards, 
            key="section_a_standard",
            index=available_standards.index(st.session_state.section_a_current_standard) if st.session_state.section_a_current_standard in available_standards else 0
        )
        st.session_state.section_a_current_standard = dimensional_standard
        
        if dimensional_standard != "All":
            std_series = st.session_state.available_series.get(dimensional_standard, "Unknown")
            st.caption(f"Series: {std_series}")
    
    with col4:
        # Size
        available_sizes = get_available_sizes_for_standard_product(dimensional_standard, dimensional_product)
        dimensional_size = st.selectbox(
            "Size", 
            available_sizes, 
            key="section_a_size",
            index=available_sizes.index(st.session_state.section_a_current_size) if st.session_state.section_a_current_size in available_sizes else 0
        )
        st.session_state.section_a_current_size = dimensional_size
        
        if dimensional_size != "All":
            st.caption(f"Sizes available: {len(available_sizes)-1}")
    
    with col5:
        # Grade (only for ISO 4014 Hex Bolt)
        if dimensional_standard == "ISO 4014" and dimensional_product == "Hex Bolt":
            grade_options = get_available_grades_for_standard_product(dimensional_standard, dimensional_product)
            dimensional_grade = st.selectbox(
                "Product Grade", 
                grade_options, 
                key="section_a_grade",
                index=grade_options.index(st.session_state.section_a_current_grade) if st.session_state.section_a_current_grade in grade_options else 0
            )
            st.session_state.section_a_current_grade = dimensional_grade
            
            if dimensional_grade != "All":
                st.caption(f"Grade: {dimensional_grade}")
        else:
            st.info("Grade not applicable")
            dimensional_grade = "Not Applicable"
            st.session_state.section_a_current_grade = "All"
    
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

def show_section_b_thread_specs():
    """Show Section B - Thread Specifications"""
    st.markdown("""
    <div class="independent-section">
        <h3 class="filter-header">Section B - Thread Specifications</h3>
        <p><strong>Enhanced:</strong> Simplified column mapping with fallback data</p>
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
        
        if thread_standard != "All":
            df_thread = thread_manager.get_thread_data_enhanced(thread_standard)
            if not df_thread.empty:
                st.caption(f"Threads available: {len(df_thread)}")
    
    with col2:
        # Thread sizes
        thread_size_options = thread_manager.get_thread_sizes_enhanced(thread_standard)
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
        # Tolerance classes
        if thread_standard == "ASME B1.1":
            tolerance_options = thread_manager.get_thread_classes_enhanced(thread_standard)
            if len(tolerance_options) == 1:  # Only "All"
                tolerance_options = ["All", "1A", "2A", "3A"]
            tolerance_class = st.selectbox(
                "Tolerance Class", 
                tolerance_options, 
                key="section_b_class",
                index=tolerance_options.index(st.session_state.section_b_current_class) if st.session_state.section_b_current_class in tolerance_options else 0
            )
            st.session_state.section_b_current_class = tolerance_class
        else:
            tolerance_options = thread_manager.get_thread_classes_enhanced(thread_standard)
            tolerance_class = st.selectbox(
                "Tolerance Class", 
                tolerance_options, 
                key="section_b_class",
                index=tolerance_options.index(st.session_state.section_b_current_class) if st.session_state.section_b_current_class in tolerance_options else 0
            )
            st.session_state.section_b_current_class = tolerance_class
        
        if tolerance_class != "All":
            st.caption(f"Classes available: {len(tolerance_options)-1}")
    
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

def show_section_c_material_props():
    """Show Section C - Material Properties"""
    st.markdown("""
    <div class="independent-section">
        <h3 class="filter-header">Section C - Material Properties</h3>
        <p><strong>Enhanced:</strong> Comprehensive property classes with fallback data</p>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Property classes
        property_classes = ["All"]
        if st.session_state.property_classes:
            property_classes.extend(sorted(st.session_state.property_classes))
        else:
            property_classes = ["All", "No data available"]
        
        property_class = st.selectbox(
            "Property Class (Grade)", 
            property_classes, 
            key="section_c_class",
            index=property_classes.index(st.session_state.section_c_current_class) if st.session_state.section_c_current_class in property_classes else 0
        )
        st.session_state.section_c_current_class = property_class
        
        if property_class != "All" and property_class != "No data available":
            st.caption(f"Selected: {property_class}")
    
    with col2:
        # Material standards
        material_standards = ["All"]
        if property_class != "All" and property_class != "No data available":
            mechem_standards = me_chem_processor.get_standards_for_property_class(property_class)
            if mechem_standards:
                material_standards.extend(sorted(mechem_standards))
            else:
                material_standards.extend(["ASTM A193", "ASTM A320", "ISO 898-1", "ASME B18.2.1"])
        
        material_standard = st.selectbox(
            "Material Standard", 
            material_standards, 
            key="section_c_standard",
            index=material_standards.index(st.session_state.section_c_current_standard) if st.session_state.section_c_current_standard in material_standards else 0
        )
        st.session_state.section_c_current_standard = material_standard
        
        if material_standard != "All":
            st.caption(f"Standard: {material_standard}")
    
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
                
                if st.session_state.section_c_results.empty:
                    st.warning(f"No data found for Property Class: {property_class} and Standard: {material_standard}")
                else:
                    st.success(f"Found {len(st.session_state.section_c_results)} records for {property_class}")
                
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Show Section C Results
    show_section_c_results()

def show_combined_results_section():
    """Show combined results section"""
    st.markdown("---")
    st.markdown("### Combine All Sections")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("COMBINE ALL SECTION RESULTS", use_container_width=True, type="secondary", key="combine_all"):
            st.session_state.combined_results = combine_all_results()
            st.rerun()
    
    # Show Combined Results
    show_combined_results()

def show_quick_actions():
    """Show quick actions section"""
    st.markdown("---")
    st.markdown("### Quick Actions")
    
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    
    with quick_col1:
        if st.button("Clear All Filters", use_container_width=True, key="clear_all"):
            session_manager.reset_section("all")
            st.rerun()
    
    with quick_col2:
        if st.button("View All Data", use_container_width=True, key="view_all"):
            # Show all available data
            st.session_state.section_a_results = data_loader.safe_load_excel_enhanced("main_data")
            st.session_state.section_b_results = thread_manager.get_thread_data_enhanced("ASME B1.1")
            st.session_state.section_c_results = data_loader.safe_load_excel_enhanced("me_chem_data")
            st.rerun()
    
    with quick_col3:
        if st.button("Export Everything", use_container_width=True, key="export_all"):
            combined = combine_all_results()
            if not combined.empty:
                ExportManager.enhanced_export_data(combined, "Excel")
            else:
                st.warning("No data to export")
    
    with quick_col4:
        if st.button("Reset Sections", use_container_width=True, key="reset_sections"):
            st.session_state.section_a_view = True
            st.session_state.section_b_view = True
            st.session_state.section_c_view = True
            st.rerun()

# ======================================================
# ENHANCED WEIGHT CALCULATOR SECTION
# ======================================================
def show_enhanced_weight_calculator():
    """Enhanced weight calculator with robust data handling"""
    
    st.markdown("""
    <div class="jsc-header">
        <h1>Weight Calculator - Enhanced</h1>
        <p>Robust calculations with comprehensive fallback data and validation</p>
        <div>
            <span class="jsc-badge">Enhanced</span>
            <span class="jsc-badge-accent">Validation</span>
            <span class="jsc-badge-secondary">Fallback Data</span>
            <span class="jsc-badge-success">Detailed Results</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("""
    **ENHANCED FEATURES:** 
    - **Robust Data Handling:** Fallback data when primary sources fail
    - **Comprehensive Validation:** Parameter validation before calculation
    - **Detailed Results:** Complete calculation breakdown for all products
    - **Error Recovery:** Graceful error handling with user-friendly messages
    """)
    
    # Initialize session state for form inputs
    if 'weight_form_submitted' not in st.session_state:
        st.session_state.weight_form_submitted = False
    
    # Main input form with enhanced workflow
    with st.form("enhanced_weight_calculator"):
        st.markdown("### Product Standards Selection")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            # A. Product Type
            product_options = product_manager.get_available_products()
            selected_product = st.selectbox(
                "A. Product Type",
                product_options,
                key="weight_calc_product_select"
            )
            
            if selected_product != "Select Product":
                st.caption(f"Selected: {selected_product}")
        
        with col2:
            # B. Series (Inch/Metric)
            series_options = product_manager.get_series_for_product(selected_product)
            selected_series = st.selectbox(
                "B. Series",
                series_options,
                key="weight_calc_series_select"
            )
            
            if selected_series != "Select Series":
                st.caption(f"Series: {selected_series}")
                if selected_series == "Inch":
                    st.caption("⚠️ Inch dimensions will be converted to mm")
        
        with col3:
            # C. Standard (based on Product + Series)
            if selected_product == "Threaded Rod":
                st.info("Standard not required for Threaded Rod")
                selected_standard = "Not Required"
            else:
                standard_options = product_manager.get_standards_for_product_series(selected_product, selected_series)
                selected_standard = st.selectbox(
                    "C. Standard",
                    standard_options,
                    key="weight_calc_standard_select"
                )
            
            if selected_standard != "Select Standard" and selected_standard != "Not Required":
                st.caption(f"Standard: {selected_standard}")
        
        with col4:
            # D. Size (based on Standard + Product)
            if selected_product == "Threaded Rod":
                st.info("Size not required for Threaded Rod")
                selected_size = "Not Required"
            else:
                size_options = product_manager.get_sizes_for_standard_product(selected_standard, selected_product)
                selected_size = st.selectbox(
                    "D. Size",
                    size_options,
                    key="weight_calc_size_select"
                )
            
            if selected_size != "Select Size" and selected_size != "Not Required":
                st.caption(f"Size: {selected_size}")
        
        with col5:
            # E. Grade (only for ISO 4014 Hex Bolt)
            if selected_standard == "ISO 4014" and selected_product == "Hex Bolt":
                grade_options = get_available_grades_for_standard_product(selected_standard, selected_product)
                selected_grade = st.selectbox(
                    "E. Product Grade",
                    grade_options,
                    key="weight_calc_grade_select"
                )
                
                if selected_grade != "All":
                    st.caption(f"Grade: {selected_grade}")
            else:
                st.info("Grade not applicable")
                selected_grade = "Not Applicable"
        
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
                        format="%.4f",
                        key="weight_calc_blank_diameter_input"
                    )
                with dia_col2:
                    blank_dia_unit = st.selectbox(
                        "Unit",
                        ["mm", "inch", "ft"],
                        key="weight_calc_blank_dia_unit_select"
                    )
                
                st.caption(f"Blank Diameter: {blank_diameter:.4f} {blank_dia_unit}")
            
            else:  # Pitch Diameter
                st.markdown("**Thread Specification**")
                
                # Thread Standard
                thread_std_options = thread_manager.get_thread_standards_for_series(selected_series)
                if selected_series == "Select Series":
                    thread_std_options = ["Select Thread Standard"]
                
                thread_standard = st.selectbox(
                    "Thread Standard",
                    thread_std_options,
                    key="weight_calc_thread_standard_select"
                )
                
                if thread_standard != "Select Thread Standard":
                    # Thread Size
                    thread_size_options = thread_manager.get_thread_sizes_enhanced(thread_standard)
                    thread_size = st.selectbox(
                        "Thread Size",
                        thread_size_options,
                        key="weight_calc_thread_size_select"
                    )
                    
                    # Thread Class
                    if selected_series == "Inch" and thread_standard == "ASME B1.1":
                        thread_class_options = thread_manager.get_thread_classes_enhanced(thread_standard)
                        if len(thread_class_options) == 1:  # Only "All"
                            thread_class_options = ["2A", "3A", "1A"]
                        thread_class = st.selectbox(
                            "Tolerance Class",
                            thread_class_options,
                            key="weight_calc_thread_class_select"
                        )
                    else:
                        thread_class = "N/A"
                        st.caption("Tolerance Class: Not applicable")
                    
                    st.caption(f"Thread: {thread_standard}, Size: {thread_size}, Class: {thread_class}")
                    
                    # Show pitch diameter information
                    if selected_diameter_type == "Pitch Diameter" and thread_size != "All":
                        pitch_diameter = thread_manager.get_pitch_diameter_from_thread_data(thread_standard, thread_size, thread_class)
                        if pitch_diameter is not None:
                            st.session_state.pitch_diameter_value = pitch_diameter
                            
                            if selected_series == "Inch":
                                pitch_diameter_mm = pitch_diameter * 25.4
                                st.success(f"Pitch Diameter (Min): {pitch_diameter:.4f} in → {pitch_diameter_mm:.4f} mm")
                            else:
                                st.success(f"Pitch Diameter (Min): {pitch_diameter:.4f} mm")
                        else:
                            st.warning("Pitch diameter not found in thread data")
        
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
                    value=50.0,
                    step=0.1,
                    format="%.4f",
                    key="weight_calc_length_input"
                )
            with length_col2:
                length_unit = st.selectbox(
                    "Unit",
                    ["mm", "inch", "ft", "meter"],
                    key="weight_calc_length_unit_select"
                )
            
            if length_unit != "mm":
                st.caption(f"→ {data_processor.convert_to_mm(length, length_unit):.4f} mm")
            else:
                st.caption("✓ Already in mm")
        
        with col2:
            # Material
            material_options = ["Carbon Steel", "Stainless Steel", "Alloy Steel", "Brass", "Aluminum", 
                              "Copper", "Titanium", "Bronze", "Inconel", "Monel", "Nickel"]
            material = st.selectbox(
                "Material",
                material_options,
                key="weight_calc_material_select"
            )
            
            density = weight_calculator.get_material_density(material)
            st.caption(f"Density: {density:.4f} g/cm³")
        
        with col3:
            # Calculate button space
            st.markdown("<br>", unsafe_allow_html=True)
            calculate_btn = st.form_submit_button("Calculate Weight", use_container_width=True, type="primary")
    
    # Handle form submission
    if calculate_btn:
        handle_weight_calculation(
            selected_product, selected_series, selected_standard, selected_size, selected_grade,
            selected_diameter_type, blank_diameter, blank_dia_unit, thread_standard, thread_size, thread_class,
            length, length_unit, material
        )
    
    # Display current selection summary
    if selected_product != "Select Product":
        show_selection_summary(
            selected_product, selected_series, selected_standard, selected_size, selected_grade,
            selected_diameter_type, blank_diameter, blank_dia_unit, thread_standard, thread_size, thread_class,
            length, length_unit, material
        )
    
    # Display calculation results
    if st.session_state.weight_calculation_performed and st.session_state.weight_calc_result:
        show_calculation_results()

def handle_weight_calculation(selected_product, selected_series, selected_standard, selected_size, selected_grade,
                            selected_diameter_type, blank_diameter, blank_dia_unit, thread_standard, thread_size, thread_class,
                            length, length_unit, material):
    """Handle weight calculation with validation"""
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
            if 'pitch_diameter_value' in st.session_state and st.session_state.pitch_diameter_value is not None:
                pitch_diameter = st.session_state.pitch_diameter_value
                
                # Determine unit based on thread standard
                if selected_series == "Inch":
                    calculation_params.update({
                        'diameter_value': pitch_diameter,
                        'diameter_unit': 'inch'
                    })
                    st.success(f"Using Pitch Diameter: {pitch_diameter:.4f} inches for calculation")
                else:
                    calculation_params.update({
                        'diameter_value': pitch_diameter,
                        'diameter_unit': 'mm'
                    })
                    st.success(f"Using Pitch Diameter: {pitch_diameter:.4f} mm for calculation")
            else:
                st.error("Pitch diameter not available for calculation")
                return
        
        # Perform calculation using enhanced calculator
        result = weight_calculator.calculate_weight(calculation_params)
        
        if result:
            st.session_state.weight_calc_result = result
            st.session_state.weight_calculation_performed = True
            
            # Save to calculation history
            calculation_data = {
                'product': selected_product,
                'series': selected_series,
                'size': selected_size if selected_product != "Threaded Rod" else "Threaded Rod",
                'grade': selected_grade if selected_standard == "ISO 4014" and selected_product == "Hex Bolt" else "N/A",
                'diameter': f"{blank_diameter:.4f} {blank_dia_unit}" if selected_diameter_type == 'Blank Diameter' else f"{thread_size} mm",
                'length': f"{length:.4f} {length_unit}",
                'material': material,
                'weight_kg': result['weight_kg'],
                'weight_lb': result['weight_lb'],
                'timestamp': datetime.now().isoformat()
            }
            CalculationHistoryManager.save_calculation_history(calculation_data)
            
            st.success("**Weight Calculation Completed Successfully!**")

def show_selection_summary(selected_product, selected_series, selected_standard, selected_size, selected_grade,
                         selected_diameter_type, blank_diameter, blank_dia_unit, thread_standard, thread_size, thread_class,
                         length, length_unit, material):
    """Show current selection summary"""
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
            - **Value:** {blank_diameter:.4f} {blank_dia_unit}
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
    - **Length:** {length:.4f} {length_unit}
    - **Material:** {material}
    - **Material Density:** {weight_calculator.get_material_density(material):.4f} g/cm³
    """)

def show_calculation_results():
    """Show detailed calculation results"""
    result = st.session_state.weight_calc_result
    
    st.markdown("### Calculation Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Weight (kg)", f"{result['weight_kg']:.4f}")
    with col2:
        st.metric("Weight (grams)", f"{result['weight_g']:.4f}")
    with col3:
        st.metric("Weight (pounds)", f"{result['weight_lb']:.4f}")
    with col4:
        st.metric("Density", f"{result['density_g_cm3']:.4f} g/cm³")
    
    # Enhanced detailed results
    with st.expander("📐 Detailed Calculation Parameters"):
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
                st.markdown("#### Calculated Values (Millimeters)")
                for key, value in dimensions.items():
                    if 'calculation' in key.lower() and 'mm' in key:
                        st.markdown(f"- **{key.replace('_', ' ').title()}:** `{value} mm`")
            
            # Show volume calculations
            st.markdown("#### Volume Calculations")
            vol_col1, vol_col2 = st.columns(2)
            with vol_col1:
                if 'shank_volume_mm3' in dimensions:
                    st.markdown(f"- **Shank Volume:** `{dimensions['shank_volume_mm3']} mm³`")
                if 'head_volume_mm3' in dimensions:
                    st.markdown(f"- **Head Volume:** `{dimensions['head_volume_mm3']} mm³`")
                if 'total_volume_mm3' in dimensions:
                    st.markdown(f"- **Total Volume:** `{dimensions['total_volume_mm3']} mm³`")
            
            with vol_col2:
                if 'total_volume_cm3' in dimensions:
                    st.markdown(f"- **Total Volume:** `{dimensions['total_volume_cm3']} cm³`")
                if 'volume_cm3' in dimensions:
                    st.markdown(f"- **Volume:** `{dimensions['volume_cm3']} cm³`")
                st.markdown(f"- **Density:** `{dimensions['density_g_cm3']} g/cm³`")
        
        # Show formula details for all product types
        if 'formula_details' in result:
            st.markdown("### 🧮 Formula Details")
            formulas = result['formula_details']
            for formula_name, formula in formulas.items():
                st.markdown(f"- **{formula_name.replace('_', ' ').title()}:** `{formula}`")

# ======================================================
# ENHANCED HOME DASHBOARD
# ======================================================
def show_enhanced_home():
    """Show professional engineering dashboard"""
    
    st.markdown("""
    <div class="jsc-header">
        <h1>JSC Industries - Enhanced Fastener Intelligence</h1>
        <p>Professional Platform v4.0 - Robust Data Handling with Fallback Support</p>
        <div>
            <span class="jsc-badge">Enhanced</span>
            <span class="jsc-badge-accent">Fallback Data</span>
            <span class="jsc-badge-secondary">Validation</span>
            <span class="jsc-badge-success">Professional Grade</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # System metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = sum([len(df) for df in data_loader.loaded_data.values() if isinstance(df, pd.DataFrame)])
    total_dimensional_standards = st.session_state.dimensional_standards_count
    total_threads = len(data_config.thread_files)
    total_mecert = len(data_loader.safe_load_excel_enhanced("me_chem_data"))
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: var(--jsc-primary); margin:0;">Products</h3>
            <h2 style="color: var(--jsc-primary-dark); margin:0.5rem 0;">{total_products}</h2>
            <p style="color: #7f8c8d; margin:0;">Total Records</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: var(--jsc-primary); margin:0;">Dimensional Standards</h3>
            <h2 style="color: var(--jsc-primary-dark); margin:0.5rem 0;">{total_dimensional_standards}</h2>
            <p style="color: #7f8c8d; margin:0;">ASME B18.2.1, ASME B18.3, ISO 4014, DIN-7991</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: var(--jsc-primary); margin:0;">Thread Types</h3>
            <h2 style="color: var(--jsc-primary-dark); margin:0.5rem 0;">{total_threads}</h2>
            <p style="color: #7f8c8d; margin:0;">Available</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: var(--jsc-primary); margin:0;">ME&CERT</h3>
            <h2 style="color: var(--jsc-primary-dark); margin:0.5rem 0;">{total_mecert}</h2>
            <p style="color: #7f8c8d; margin:0;">Properties</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<h2 class="section-header">Engineering Tools - Enhanced</h2>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    actions = [
        ("Product Database", "Professional product discovery with enhanced filters and fallback data", "database"),
        ("Engineering Calculator", "Enhanced weight calculations with robust validation", "calculator"),
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
        st.markdown('<h3 class="section-header">System Status - Enhanced</h3>', unsafe_allow_html=True)
        
        status_items = [
            ("ASME B18.2.1 Data", not data_loader.safe_load_excel_enhanced("main_data").empty, "jsc-badge"),
            ("ISO 4014 Data", not data_loader.safe_load_excel_enhanced("iso4014").empty, "jsc-badge-accent"),
            ("DIN-7991 Data", st.session_state.din7991_loaded, "jsc-badge-secondary"),
            ("ASME B18.3 Data", st.session_state.asme_b18_3_loaded, "jsc-badge-success"),
            ("ME&CERT Data", not data_loader.safe_load_excel_enhanced("me_chem_data").empty, "jsc-badge"),
            ("Thread Data", any(not thread_manager.get_thread_data_enhanced(std).empty for std in data_config.thread_files.keys()), "jsc-badge-accent"),
            ("Weight Calculations", True, "jsc-badge-secondary"),
            ("Enhanced Calculator", True, "jsc-badge-success"),
        ]
        
        for item_name, status, badge_class in status_items:
            if status:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0;">{item_name} - Active</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="{badge_class}" style="margin: 0.3rem 0; background: #6c757d;">{item_name} - Limited</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<h3 class="section-header">Enhanced Features</h3>', unsafe_allow_html=True)
        
        features = [
            "Robust data loading with comprehensive fallback support",
            "Enhanced error handling and validation",
            "Simplified column mapping for thread data",
            "Comprehensive calculation parameter validation",
            "Detailed calculation results for all product types",
            "Professional reporting with enhanced styling",
            "Carbon steel density: 7.85 g/cm³",
            "Batch processing capabilities",
            "Database-connected calculations with fallbacks",
            "Enhanced user interface with loading states",
            "ISO 4014 Product Grade selection",
            "Comprehensive logging and monitoring",
            "Data quality indicators and reporting",
            "Graceful error recovery mechanisms"
        ]
        
        for feature in features:
            st.markdown(f'<div class="jsc-card" style="padding: 0.5rem; margin: 0.2rem 0;">• {feature}</div>', unsafe_allow_html=True)
    
    # Show calculation history
    CalculationHistoryManager.show_calculation_history()

# ======================================================
# ENHANCED HELP SYSTEM
# ======================================================
def show_enhanced_help_system():
    """Show contextual help system"""
    with st.sidebar:
        st.markdown("---")
        with st.expander("🆘 Enhanced Weight Calculator Guide"):
            st.markdown("""
            **ENHANCED DATA HANDLING:**
            
            **Fallback Data Support:**
            - Automatic fallback when primary data sources fail
            - Comprehensive fallback data for all product types
            - Graceful degradation of features
            
            **Validation & Error Handling:**
            - Comprehensive parameter validation
            - User-friendly error messages
            - Detailed logging for debugging
            
            **Calculation Methods:**
            - **Socket Head Products:** Cylinder volume formula
            - **Hex Products:** Hex head volume formula  
            - **Threaded Rod:** Simple cylinder formula
            - **All calculations:** Proper unit conversion
            
            **DENSITY VALUES (g/cm³):**
            - Carbon Steel: 7.85
            - Stainless Steel: 8.00
            - Alloy Steel: 7.85
            - Brass: 8.50
            - Aluminum: 2.70
            - Copper: 8.96
            - Titanium: 4.50
            
            **Detailed Parameters:**
            - Complete dimension breakdown
            - Volume calculations for each component
            - Formula details for all product types
            """)
        
        with st.expander("🔧 Technical Details"):
            st.markdown("""
            **Data Sources:**
            - Primary: Google Sheets (online)
            - Secondary: Local Excel files
            - Fallback: Built-in comprehensive data
            
            **Performance:**
            - Cached data loading (2-hour TTL)
            - Lazy loading for large datasets
            - Progressive UI updates
            
            **Error Recovery:**
            - Automatic retry mechanisms
            - Fallback data activation
            - User-friendly error messages
            """)

# ======================================================
# SECTION DISPATCHER
# ======================================================
def show_section(title):
    """Enhanced section dispatcher with error handling"""
    try:
        if title == "Product Database":
            show_enhanced_product_database()
        elif title == "Calculations":
            show_enhanced_weight_calculator()
        else:
            st.info(f"Section {title} is coming soon!")
        
        st.markdown("---")
        if st.button("Back to Dashboard", use_container_width=True):
            st.session_state.selected_section = None
            st.rerun()
    except Exception as e:
        logger.error(f"Error in section {title}: {str(e)}")
        st.error(f"An error occurred in the {title} section. Please try again.")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())

# ======================================================
# LEGACY FUNCTIONS (for compatibility)
# ======================================================
def get_available_standards_for_product_series(product, series):
    """Get available standards based on selected product and series"""
    return product_manager.get_standards_for_product_series(product, series)

def get_available_sizes_for_standard_product(standard, product, grade="All"):
    """Get available sizes based on selected standard and product"""
    return product_manager.get_sizes_for_standard_product(standard, product)

def get_available_grades_for_standard_product(standard, product):
    """Get available grades for specific standard and product"""
    grade_options = ["All"]
    
    if standard == "Select Standard" or product == "Select Product":
        return grade_options
    
    # Only ISO 4014 has product grades A and B
    if standard == "ISO 4014" and product == "Hex Bolt":
        temp_df = data_loader.safe_load_excel_enhanced("iso4014")
        
        # Filter by product if specified
        if product != "All" and 'Product' in temp_df.columns:
            temp_df = temp_df[temp_df['Product'] == product]
        
        # Get grade options from the data
        if 'Product_Grade' in temp_df.columns:
            unique_grades = temp_df['Product_Grade'].dropna().unique()
            unique_grades = [str(grade).strip() for grade in unique_grades if str(grade).strip() != '']
            if len(unique_grades) > 0:
                grade_options.extend(sorted(unique_grades))
        else:
            # Default grades for ISO 4014 Hex Bolt
            grade_options.extend(["A", "B"])
    
    return grade_options

def apply_section_a_filters():
    """Apply filters for Section A - Dimensional Specifications"""
    filters = st.session_state.section_a_filters
    
    if not filters:
        return pd.DataFrame()
    
    product = filters.get('product', 'All')
    series = filters.get('series', 'All')
    standard = filters.get('standard', 'All')
    size = filters.get('size', 'All')
    grade = filters.get('grade', 'All')
    
    # Get appropriate dataframe
    if standard == "ASME B18.2.1":
        temp_df = data_loader.safe_load_excel_enhanced("main_data")
    elif standard == "ISO 4014":
        temp_df = data_loader.safe_load_excel_enhanced("iso4014")
    elif standard == "DIN-7991":
        temp_df = data_loader.safe_load_excel_enhanced("din7991")
    elif standard == "ASME B18.3":
        temp_df = data_loader.safe_load_excel_enhanced("asme_b18_3")
    else:
        return pd.DataFrame()
    
    # Apply filters
    if product != "All" and 'Product' in temp_df.columns:
        temp_df = temp_df[temp_df['Product'] == product]
    
    if size != "All" and 'Size' in temp_df.columns:
        temp_df = temp_df[temp_df['Size'].astype(str).str.strip() == str(size).strip()]
    
    # Apply grade filter if specified (only for ISO 4014)
    if standard == "ISO 4014" and grade != "All" and 'Product_Grade' in temp_df.columns:
        temp_df = temp_df[temp_df['Product_Grade'] == grade]
    
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
    
    return thread_manager.get_thread_data_enhanced(standard, size, thread_class)

def apply_section_c_filters():
    """Apply filters for Section C - Material Properties"""
    filters = st.session_state.section_c_filters
    
    if not filters:
        return pd.DataFrame()
    
    property_class = filters.get('property_class', 'All')
    standard = filters.get('standard', 'All')
    
    if property_class == "All":
        return data_loader.safe_load_excel_enhanced("me_chem_data")
    
    df_mechem = data_loader.safe_load_excel_enhanced("me_chem_data")
    if df_mechem.empty:
        return pd.DataFrame()
    
    # Find property class columns
    property_class_cols = me_chem_processor._find_property_class_columns(df_mechem)
    
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
        standard_cols = me_chem_processor._find_standard_columns(filtered_data)
        
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
                ExportManager.enhanced_export_data(st.session_state.section_a_results, "Excel")
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
            ExportManager.enhanced_export_data(st.session_state.section_b_results, "Excel")
        
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
            me_chem_processor.show_mechanical_chemical_details(st.session_state.section_c_filters.get('property_class'))
        
        if st.button("Export Section C Results", key="export_section_c"):
            ExportManager.enhanced_export_data(st.session_state.section_c_results, "Excel")
        
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
                ExportManager.enhanced_export_data(st.session_state.combined_results, "Excel")
        with col2:
            if st.button("Clear Combined Results", key="clear_combined"):
                st.session_state.combined_results = pd.DataFrame()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def extract_product_details(row):
    """Extract product details from dataframe row and map to card format"""
    details = {
        'Product': row.get('Product', 'Hex Bolt'),
        'Size': row.get('Size', 'N/A'),
        'Standards': row.get('Standards', 'ASME B18.2.1'),
        'Thread': row.get('Thread', '1/4-20-UNC-2A'),
        'Product Grade': row.get('Product_Grade', 'N/A'),
        
        # Map dimensional specifications
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

def show_professional_product_card(product_details):
    """Display a beautiful professional product specification card"""
    # Implementation of professional product card display
    # (This would be the same implementation as in the original code)
    st.info("Professional product card display would be implemented here")

# ======================================================
# MAIN APPLICATION
# ======================================================
def main():
    """Main application entry point"""
    
    # Initialize application
    initialize_application()
    
    # Show help system
    show_enhanced_help_system()
    
    # Show data quality indicators
    UIComponents.show_data_quality_indicators()
    
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
        
        # Show session summary in debug mode
        if st.session_state.debug_mode:
            with st.expander("Session State Summary"):
                session_summary = session_manager.get_session_summary()
                st.json(session_summary)
    
    # Main content area
    if st.session_state.selected_section is None:
        show_enhanced_home()
    else:
        show_section(st.session_state.selected_section)
    
    # Footer
    st.markdown("""
        <hr>
        <div class="jsc-footer">
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
                <span class="jsc-badge">Enhanced Platform</span>
                <span class="jsc-badge-accent">Fallback Support</span>
                <span class="jsc-badge-secondary">Robust Data</span>
                <span class="jsc-badge-success">Professional Grade</span>
            </div>
            <p><strong>© 2024 JSC Industries Pvt Ltd</strong> | Born to Perform • Engineered for Excellence</p>
            <p style="font-size: 0.8rem;">Enhanced Fastener Intelligence Platform v4.0 - Robust data handling with comprehensive fallback support</p>
        </div>
    """, unsafe_allow_html=True)

# Run the application
if __name__ == "__main__":
    main()