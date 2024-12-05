import streamlit as st
from settings import get_settings, get_storage
import google.generativeai as genai
from gdrive_handler import GDriveHandler
from oauth_handler import initialize_oauth, create_flow
import os

def show_welcome_screen():
    """Show welcome screen with setup instructions"""
    # Initialize OAuth settings
    initialize_oauth()
    
    st.markdown("""
    # Welcome to PDF to CSV Converter! 🎉
    
    This app helps you convert PDF tables into CSV files using AI-powered extraction.
    Let's get you set up with everything you need.
    """)
    
    # Initialize session state
    if 'setup_complete' not in st.session_state:
        st.session_state.setup_complete = False
    if 'show_welcome' not in st.session_state:
        st.session_state.show_welcome = True
    
    # Get current settings
    settings = get_settings()
    api_key = settings.get('api_key')
    
    # Create tabs for setup steps
    tab1, tab2 = st.tabs(["1. API Setup", "2. Google Drive Setup"])
    
    with tab1:
        st.markdown("""
        ## Step 1: Configure Gemini API
        
        To use this app, you'll need a Gemini API key:
        
        1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Create or select a project
        3. Click "Create API key" and copy it
        4. Paste your API key below
        """)
        
        # API Key input
        api_key_input = st.text_input(
            "Enter your Gemini API key:",
            type="password",
            value=api_key if api_key else "",
            help="Your API key will be stored securely in your browser"
        )
        
        if api_key_input:
            # Save API key
            storage = get_storage()
            storage.save_credential('api_key', api_key_input)
            st.success("✅ API key saved!")
            st.session_state.api_key = api_key_input
            
            # Test the API key
            try:
                genai.configure(api_key=api_key_input)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content("Test")
                st.success("✅ API Key is valid!")
            except Exception as e:
                st.error("❌ Invalid API Key. Please check and try again.")
        else:
            st.warning("Please enter your API key")
    
    with tab2:
        st.markdown("""
        ## Step 2: Connect Google Drive
        
        Next, let's connect your Google Drive account:
        
        1. Click the "Connect to Google Drive" button below
        2. Select your Google account
        3. Review and accept the permissions
        """)
        
        # Google Drive connection
        if st.button("Connect to Google Drive"):
            try:
                flow = create_flow()
                auth_url, _ = flow.authorization_url(prompt='consent')
                st.session_state.oauth_flow = flow  # Store flow in session state
                st.markdown(f'Click [here]({auth_url}) to connect your Google account')
            except Exception as e:
                st.error(f"Failed to create authentication flow: {str(e)}")
    
    # Check if setup is complete
    if api_key and st.session_state.get('credentials'):
        st.session_state.setup_complete = True
        st.session_state.show_welcome = False
        st.success("🎉 Setup complete! You're ready to start converting PDFs.")
        st.button("Start Using the App", type="primary")
        st.rerun()

def show_settings_menu():
    """Show the settings menu in the sidebar"""
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Show connected account
        if st.session_state.get('credentials'):
            try:
                gdrive = GDriveHandler(st.session_state.credentials)
                about = gdrive.service.about().get(fields="user").execute()
                email = about["user"]["emailAddress"]
                st.success(f"Connected as: {email}")
                
                if st.button("Disconnect Google Drive"):
                    try:
                        os.remove(os.path.join(os.path.expanduser('~'), '.pdf_to_csv_creds'))
                        st.session_state.credentials = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error disconnecting: {str(e)}")
            except Exception:
                st.error("Connection error. Please reconnect.")
                st.session_state.pop('credentials', None)
        
        # API Key settings
        st.subheader("Gemini API Key")
        if st.session_state.get('api_key'):
            st.success("API Key configured")
            if st.button("Change API Key"):
                st.session_state.api_key = None
                st.rerun()
        
        # About section
        st.subheader("About")
        st.markdown("""
        PDF to CSV Converter
        - Powered by Google Gemini AI
        - Version 1.0.0
        """)

def show_tutorial():
    """Show the tutorial for first-time users"""
    if 'show_tutorial' not in st.session_state:
        st.session_state.show_tutorial = True
    
    if st.session_state.show_tutorial:
        with st.sidebar:
            st.subheader("🎓 Quick Tutorial")
            st.markdown("""
            1. Select an input folder containing PDFs
            2. Select an output folder for CSVs
            3. Click 'Process Files' to convert
            """)
            if st.button("Got it!"):
                st.session_state.show_tutorial = False
                st.rerun()
