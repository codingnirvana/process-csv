import streamlit as st
import os

def show_settings():
    """Show settings page"""
    st.title("Settings")
    
    # Initialize settings in session state if not present
    if 'gemini_settings' not in st.session_state:
        st.session_state.gemini_settings = {
            'api_key': '',
            'model': 'gemini-1.5-flash'
        }
    
    st.subheader("🔑 Gemini API Configuration")
    
    # API Key input
    api_key = st.text_input(
        "Gemini API Key",
        value=st.session_state.gemini_settings.get('api_key', ''),
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
            st.session_state.gemini_settings.get('model', 'gemini-1.5-flash')
        ),
        help="Select which Gemini model to use for PDF processing"
    )
    
    # Save settings button
    if st.button("💾 Save Settings"):
        st.session_state.gemini_settings = {
            'api_key': api_key,
            'model': selected_model
        }
        st.success("✅ Settings saved successfully!")

def check_settings():
    """Check if required settings are configured"""
    return (
        'gemini_settings' in st.session_state and
        st.session_state.gemini_settings.get('api_key')
    )
