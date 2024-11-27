import streamlit as st
st.set_page_config(page_title="PDF to CSV Converter", layout="wide")

import os
import time
import tempfile
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from gdrive_handler import GDriveHandler
from process_csv import extract_csv_from_pdf, save_csv_data
from dotenv import load_dotenv
from settings import show_settings, check_settings, get_settings, get_storage
import traceback

# Load environment variables from .env file
load_dotenv()

# OAuth 2.0 configuration
SCOPES = [
    'https://www.googleapis.com/auth/drive',  # Full Drive access
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

def create_flow():
    """Create OAuth 2.0 flow instance"""
    try:
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        is_production = os.getenv('PRODUCTION', 'false').lower() == 'true'
        
        if not client_id or not client_secret:
            raise ValueError("Missing OAuth credentials. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")

        # Define production and development URIs
        prod_uri = "https://pdf-to-csv-paani.streamlit.app"
        dev_uri = "http://localhost:8501"
        
        # Set base URI based on environment
        base_uri = prod_uri if is_production else dev_uri
        redirect_uri = f"{base_uri}/"  # Use trailing slash version as primary

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": [
                        f"{prod_uri}/",  # Production with trailing slash
                        f"{prod_uri}",   # Production without trailing slash
                        f"{dev_uri}/",   # Development with trailing slash
                        f"{dev_uri}"     # Development without trailing slash
                    ],
                    "javascript_origins": [
                        prod_uri,
                        dev_uri
                    ]
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/drive.file',  # Minimal scope for file access
            ],
            redirect_uri=redirect_uri
        )

        # Set additional security parameters
        flow.prompt = "consent"  # Always show consent screen
        flow.access_type = "offline"  # Get refresh token
        
        return flow
    except Exception as e:
        st.error(f"Failed to create OAuth flow: {str(e)}")
        raise

def save_oauth_credentials(credentials):
    """Save OAuth credentials to local storage"""
    if not credentials:
        return
    
    storage = get_storage()
    creds_dict = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    storage.save_credential('oauth_credentials', creds_dict)

def load_oauth_credentials():
    """Load OAuth credentials from local storage"""
    storage = get_storage()
    creds_dict = storage.get_credential('oauth_credentials')
    
    if creds_dict:
        try:
            return Credentials(
                token=creds_dict['token'],
                refresh_token=creds_dict['refresh_token'],
                token_uri=creds_dict['token_uri'],
                client_id=creds_dict['client_id'],
                client_secret=creds_dict['client_secret'],
                scopes=creds_dict['scopes']
            )
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
            return None
    return None

def handle_oauth_callback():
    """Handle OAuth callback and token exchange"""
    try:
        if st.session_state.oauth_flow is None:
            st.session_state.oauth_flow = create_flow()
        
        # Get the authorization code from URL parameters
        code = st.query_params.get('code')
        if not code:
            st.error("No authorization code received")
            return
        
        # Exchange code for tokens
        token = st.session_state.oauth_flow.fetch_token(
            authorization_response=f"http://localhost:8501/?code={code}",
            code=code
        )
        
        # Store credentials in session state and local storage
        st.session_state.credentials = st.session_state.oauth_flow.credentials
        save_oauth_credentials(st.session_state.credentials)
        
        # Clear the URL parameters
        st.query_params.clear()
        
        st.success("Successfully connected to Google Drive!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Authentication failed: {str(e)}")
        if 'access_denied' in str(e):
            st.error("""
            ### Access Denied
            
            This error typically occurs when:
            1. Your Google account is not added as a test user
            2. You're using a different Google account than the one added as a test user
            3. You didn't accept the unverified app warning
            
            Please make sure:
            1. Your Google email is added as a test user in the OAuth consent screen
            2. You're using the same Google account during login
            3. Click "Continue" on the unverified app warning
            """)
        elif 'invalid_grant' in str(e):
            st.error("""
            ### Invalid Grant Error
            
            This typically happens when:
            1. The authentication session expired
            2. The authorization code was already used
            3. There's a mismatch in redirect URIs
            
            Please try:
            1. Clicking the 'Connect to Google Drive' button again
            2. Using a fresh browser session
            3. Clearing your browser cookies
            """)
            # Reset credentials and flow
            st.session_state.credentials = None
            st.session_state.oauth_flow = None
            # Clear stored credentials
            storage = get_storage()
            storage.delete_credential('oauth_credentials')
        return

def process_pdf_file(pdf_file):
    """Process the uploaded PDF file"""
    if pdf_file is None:
        return
    
    settings = get_settings()
    api_key = settings.get('api_key')
    model = settings.get('model', 'gemini-1.5-flash')  # Ensure default model if not set
    
    if not api_key:
        st.error("Please configure your Gemini API key in settings first!")
        return
        
    with st.spinner('Processing PDF...'):
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_file.getvalue())
                pdf_path = tmp_file.name
            
            # Extract CSV data
            csv_data = extract_csv_from_pdf(pdf_path, api_key=api_key, model_name=model)
            
            if csv_data:
                st.success("PDF processed successfully!")
                
                # Save CSV data
                csv_filename = pdf_file.name.rsplit('.', 1)[0] + '.csv'
                save_csv_data(csv_data, csv_filename)
                
                # Display preview
                st.subheader("CSV Preview")
                st.write(csv_data)
                
                # Download button
                st.download_button(
                    "Download CSV",
                    csv_data,
                    csv_filename,
                    "text/csv",
                    key='download-csv'
                )
                
                # Upload to Google Drive if authenticated
                if st.session_state.get('credentials'):
                    gdrive = GDriveHandler(st.session_state.credentials)
                    
                    with st.spinner('Uploading to Google Drive...'):
                        file_id = gdrive.upload_file(
                            csv_filename, 
                            csv_data, 
                            'text/csv'
                        )
                        if file_id:
                            st.success(f"File uploaded to Google Drive successfully!")
            else:
                st.error("Failed to extract data from PDF. Please try another file.")
                
        except Exception as e:
            st.error(f"❌ Error processing {pdf_file.name}: {str(e)}")
            st.error("Stack trace:")
            st.code(traceback.format_exc(), language="python")
        finally:
            # Clean up temporary file
            if 'tmp_file' in locals():
                os.unlink(tmp_file.name)

def main():
    st.title("PDF to CSV Converter with Google Drive")
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .status-section {
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        .status-section .success {
            color: #00c853;
            padding: 0.3rem 0;
        }
        .status-section .error {
            color: #ff1744;
            padding: 0.3rem 0;
        }
        h1 {
            font-size: 1.8rem !important;
            font-weight: 600 !important;
        }
        h3 {
            font-size: 1rem !important;
            font-weight: 600 !important;
            color: #666;
            margin-top: 1rem !important;
        }
        .stButton button {
            border-radius: 4px;
            padding: 0.3rem 1rem;
        }
        .settings-btn button {
            padding: 0.2rem 0.5rem;
            min-width: 2rem;
        }
        .back-btn {
            max-width: 150px;
            margin: 0 auto;
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize session states
    if 'credentials' not in st.session_state:
        st.session_state.credentials = load_oauth_credentials()
    if 'show_settings' not in st.session_state:
        st.session_state.show_settings = False
    if 'oauth_flow' not in st.session_state:
        st.session_state.oauth_flow = None
    
    # Get settings for API key and model
    settings = get_settings()
    api_key = settings.get('api_key')
    model = settings.get('model', 'gemini-1.5-flash')
    
    # Show sidebar always
    with st.sidebar:
        # Add logo/title section with refined styling
        st.markdown("""
        <div style='text-align: center; margin-bottom: 1rem'>
            <h1 style='font-size: 1.3rem; margin-bottom: 0.5rem; color: #1e88e5'>🔄 PDF to CSV</h1>
            <p style='color: #666; font-size: 0.8rem; margin-bottom: 0.5rem'>Powered by Gemini AI</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin: 1rem 0; border-top: 1px solid #eee;'></div>", unsafe_allow_html=True)
        
        # Status Section with refined styling
        st.markdown("<div class='status-section'>", unsafe_allow_html=True)
        st.markdown("### System Status")
        
        # API Status with Settings link
        col1, col2 = st.columns([4, 1])
        with col1:
            if api_key:
                st.markdown("<div class='success'>✓ Gemini API</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='error'>✗ Gemini API</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='settings-btn'>", unsafe_allow_html=True)
            if st.button("⚙️", help="Configure API Settings", key="settings_btn"):
                st.session_state.show_settings = True
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Google Drive Status
        if st.session_state.credentials:
            st.markdown("<div class='success'>✓ Google Drive</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='error'>✗ Google Drive</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Show settings page or main app
    if st.session_state.show_settings:
        show_settings()
        st.markdown("<div class='back-btn'>", unsafe_allow_html=True)
        if st.button("← Back to App"):
            st.session_state.show_settings = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    if not api_key:
        st.warning("⚠️ Please configure your Gemini API key in settings first!")
        return
    
    # Check for OAuth callback
    if 'code' in st.query_params:
        handle_oauth_callback()
        return
    
    # Main app logic
    if not st.session_state.credentials:
        st.info("""
        ### Google Drive Authentication Required
        
        This app requires Google Drive access to store processed files. Since the app is in testing mode:
        1. You must be added as a test user
        2. Use the same Google account that was added as a test user
        3. Accept the unverified app warning during login
        """)
        
        # Handle OAuth callback
        if st.button("Connect to Google Drive"):
            try:
                st.session_state.oauth_flow = create_flow()
                auth_url, _ = st.session_state.oauth_flow.authorization_url(prompt='consent')
                st.markdown(f'Click [here]({auth_url}) to connect your Google account')
            except Exception as e:
                st.error(f"Failed to create authentication flow: {str(e)}")
            return  # Add return here to prevent showing the rest of the interface
        
    try:
        # Verify credentials are valid by making a test API call
        gdrive_handler = GDriveHandler(st.session_state.credentials)
        
        # Test API call
        try:
            gdrive_handler.list_folders()
            st.success("Connected to Google Drive")
        except Exception as e:
            if "invalid_grant" in str(e) or "expired" in str(e):
                st.warning("Session expired. Please reconnect to Google Drive")
                st.session_state.credentials = None
                st.rerun()
            else:
                raise e
        
        # Get or create folders
        st.subheader("Google Drive Folders")
        
        # List folders with error handling
        with st.spinner("Loading folders..."):
            folders = gdrive_handler.list_folders()
        
        if folders:
            # Create simple folder options
            folder_options = [{"id": None, "name": "-- Select a folder --"}]
            for folder in folders:
                folder_options.append({
                    "id": folder["id"],
                    "name": folder["name"]
                })
            
            # Create columns for input and output folder selection
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📁 Input Folder")
                selected_input = st.selectbox(
                    "Select folder containing PDFs:",
                    options=folder_options,
                    format_func=lambda x: x["name"],
                    key="input_folder"
                )
                
                if selected_input and selected_input["id"]:
                    st.markdown(f"🔗 [Open in Drive](https://drive.google.com/drive/folders/{selected_input['id']})")
            
            with col2:
                st.subheader("📁 Output Folder")
                selected_output = st.selectbox(
                    "Select folder for CSV output:",
                    options=folder_options,
                    format_func=lambda x: x["name"],
                    key="output_folder"
                )
                
                if selected_output and selected_output["id"]:
                    st.markdown(f"🔗 [Open in Drive](https://drive.google.com/drive/folders/{selected_output['id']})")
            
            # Create New Folder button
            if st.button("➕ Create New Folder"):
                with st.spinner("Creating folder..."):
                    new_folder_name = f"PDF_Processing_{time.strftime('%Y%m%d_%H%M%S')}"
                    folder_id = gdrive_handler.create_folder(new_folder_name)
                    st.success(f"Created folder: {new_folder_name}")
                    time.sleep(1)
                    st.rerun()
            
            # Only proceed if both input and output folders are selected
            if selected_input and selected_input["id"] and selected_output and selected_output["id"]:
                # List PDF files
                with st.spinner("Checking for PDF files..."):
                    pdf_files = gdrive_handler.list_files(selected_input["id"], "application/pdf", recursive=True)
                    if pdf_files:
                        st.success(f"Found {len(pdf_files)} PDF files")
                        if st.button("🔄 Process Files", type="primary"):
                            # Setup progress tracking
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            processed = 0
                            failed = 0
                            
                            try:
                                for i, pdf_file in enumerate(pdf_files, 1):
                                    try:
                                        # Update progress
                                        progress = i / len(pdf_files)
                                        progress_bar.progress(progress)
                                        status_text.write(f"Processing file {i} of {len(pdf_files)}: {pdf_file['name']}")
                                        
                                        # Download PDF
                                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                                            gdrive_handler.download_file(pdf_file['id'], tmp_pdf.name)
                                            
                                            # Process PDF using api_key and model from settings
                                            csv_data = extract_csv_from_pdf(
                                                pdf_path=tmp_pdf.name,
                                                api_key=api_key,
                                                model_name=model
                                            )
                                            
                                            if csv_data:
                                                # Create CSV filename - just change extension from .pdf to .csv
                                                csv_filename = os.path.splitext(pdf_file['name'])[0] + '.csv'
                                                
                                                # Save and upload CSV
                                                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_csv:
                                                    save_csv_data(csv_data, tmp_csv.name)
                                                    gdrive_handler.upload_file(
                                                        tmp_csv.name,
                                                        selected_output["id"],
                                                        new_filename=csv_filename
                                                    )
                                                    os.unlink(tmp_csv.name)
                                                processed += 1
                                            else:
                                                st.error(f"❌ No data extracted from: {pdf_file['name']}")
                                                failed += 1
                                            
                                            os.unlink(tmp_pdf.name)
                                    
                                    except Exception as e:
                                        st.error(f"❌ Error processing {pdf_file['name']}: {str(e)}")
                                        st.error("Stack trace:")
                                        st.code(traceback.format_exc(), language="python")
                                        failed += 1
                            
                                # Final status
                                progress_bar.empty()
                                status_text.empty()
                                
                                if failed > 0:
                                    st.warning(f"Completed with some errors: {processed} files processed, {failed} files failed")
                                else:
                                    st.success(f"✅ Successfully processed all {processed} files!")
                                
                                # Show output folder link
                                st.markdown(f"🔗 [View Results in Drive](https://drive.google.com/drive/folders/{selected_output['id']})")
                                
                            except Exception as e:
                                st.error(f"❌ Processing failed: {str(e)}")
                                st.error("Stack trace:")
                                st.code(traceback.format_exc(), language="python")
                            finally:
                                progress_bar.empty()
                    else:
                        st.warning("No PDF files found in the selected input folder")
            elif selected_input and selected_input["id"]:
                st.info("Please select an output folder for the CSV files")
            elif selected_output and selected_output["id"]:
                st.info("Please select an input folder containing PDF files")

        else:
            st.warning("No folders found. Click 'Create New Folder' above to create one.")
    
    except Exception as e:
        st.error("⚠️ Error occurred")
        st.error(str(e))
        st.error("Stack trace:")
        st.code(traceback.format_exc(), language="python")
        if "invalid_grant" in str(e) or "expired" in str(e):
            st.warning("Session expired. Please reconnect to Google Drive")
            st.session_state.credentials = None
            st.rerun()

if __name__ == "__main__":
    main()
