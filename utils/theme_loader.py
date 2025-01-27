import streamlit as st
import os
import logging

logger = logging.getLogger(__name__)

def load_theme():
    """Load and apply the application theme."""
    try:
        # Get the current file's directory
        current_dir = os.path.dirname(os.path.dirname(__file__))
        css_file = os.path.join(current_dir, "assets", "css", "theme.css")
        
        if os.path.exists(css_file):
            with open(css_file, 'r', encoding='utf-8') as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
                logger.info("Theme loaded successfully")
        else:
            logger.error(f"Theme file not found at: {css_file}")
            
    except Exception as e:
        logger.error(f"Error loading theme: {str(e)}")
        raise