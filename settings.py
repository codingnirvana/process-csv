import streamlit as st
import os
import json
from browser_storage import BrowserStorage

# Create storage instance only when needed
_storage = None
DEFAULT_SETTINGS = {
    'api_key': '',
    'model': 'gemini-1.5-flash'
}

def get_storage():
    """Get or create the storage instance"""
    global _storage
    if _storage is None:
        _storage = BrowserStorage(prefix="gemini_")
    return _storage

def get_settings():
    """Get current settings or return defaults"""
    storage = get_storage()
    settings = storage.get_credential("settings")
    if not settings:
        settings = DEFAULT_SETTINGS.copy()
    return settings

def save_settings(settings):
    """Save settings to storage"""
    storage = get_storage()
    storage.save_credential("settings", settings)

def show_settings():
    """Show settings page"""
    st.title("Settings")
    
    # Get current settings
    current_settings = get_settings()
    
    st.subheader("🔑 Gemini API Configuration")
    
    # API Key input
    api_key = st.text_input(
        "Gemini API Key",
        value=current_settings.get('api_key', ''),
        type="password",
        help="Enter your Gemini API key. Get one from https://makersuite.google.com/app/apikey"
    )
    
    # Model Selection
    model_options = {
        "gemini-1.5-pro": "Gemini-1.5-Pro (More accurate, slower)",
        "gemini-1.5-flash": "Gemini-1.5-Flash (Faster, good for most cases)"
    }
    
    selected_model = st.selectbox(
        "Gemini Model",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=list(model_options.keys()).index(
            current_settings.get('model', 'gemini-1.5-flash')
        ),
        help="Select which Gemini model to use for PDF processing"
    )
    
    # Save button
    if st.button("Save Settings"):
        new_settings = {
            'api_key': api_key,
            'model': selected_model
        }
        save_settings(new_settings)
        st.success("Settings saved successfully!")
        
        # Add a debug message to show current settings
        st.write("Current settings:", {
            'model': new_settings['model'],
            'api_key': '***' if new_settings['api_key'] else 'Not set'
        })
        
        # Show all stored credentials for debugging
        storage = get_storage()
        st.write("All stored credentials:", storage.list_credentials())

def check_settings():
    """Check if required settings are configured"""
    settings = get_settings()
    api_key = settings.get('api_key')
    return bool(api_key and api_key.strip())
