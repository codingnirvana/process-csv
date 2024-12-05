import streamlit as st
st.set_page_config(page_title="PDF to CSV Converter", layout="wide")

import os
import time
import tempfile
from gdrive_handler import GDriveHandler
from process_csv import extract_csv_from_pdf, save_csv_data
from dotenv import load_dotenv
from settings import show_settings, check_settings, get_settings, get_storage
import traceback
from oauth_handler import (
    initialize_oauth,
    handle_oauth_callback,
    create_flow
)

# Load environment variables from .env file
load_dotenv(dotenv_path=".env", override=True)

# OAuth 2.0 configuration
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Per-file access to files created or opened by the app
    'https://www.googleapis.com/auth/drive.readonly',  # Read-only access to file metadata and files
    'https://www.googleapis.com/auth/drive.metadata.readonly',  # Read-only access to file metadata
    'https://www.googleapis.com/auth/userinfo.email',  # Get user's email address
    'https://www.googleapis.com/auth/userinfo.profile',  # Get user's basic profile info
    'openid'  # OpenID Connect
]

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

def disconnect_google_drive():
    """Disconnect from Google Drive"""
    st.session_state.credentials = None
    st.session_state.oauth_flow = None
    st.success("Disconnected from Google Drive")

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
    
    # Initialize OAuth settings
    initialize_oauth()
    
    # Check for OAuth callback
    if 'code' in st.query_params:
        handle_oauth_callback()
        return
    
    # Handle OAuth connection
    if not st.session_state.credentials:
        st.info("""
        ### Google Drive Authentication Required
        
        This app requires Google Drive access to store processed files. Since the app is in testing mode:
        1. You must be added as a test user
        2. Use the same Google account that was added as a test user
        3. Accept the unverified app warning during login
        """)
        
        if st.button("Connect to Google Drive"):
            try:
                # Create and store flow
                flow = create_flow()
                auth_url, _ = flow.authorization_url(prompt='consent')
                
                # Store flow in session state BEFORE generating URL
                st.session_state.oauth_flow = flow
                
                # Show auth URL
                st.markdown(f'Click [here]({auth_url}) to connect your Google account')
                return
            except Exception as e:
                st.error(f"Failed to create authentication flow: {str(e)}")
                return
    
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
            <h3>PDF to CSV Converter</h3>
            <p style='color: #666; font-size: 0.9rem'>Powered by Gemini AI</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Settings button
        if st.button("⚙️ Settings", key="settings_btn", help="Configure API keys and model settings"):
            st.session_state.show_settings = not st.session_state.show_settings
            
        # Google Drive connection status and buttons
        st.markdown("### Google Drive Connection")
        if st.session_state.credentials:
            st.success("✓ Connected to Google Drive")
            if st.button("Disconnect from Google Drive", type="secondary"):
                disconnect_google_drive()
        else:
            st.error("✗ Not connected to Google Drive")
            if st.button("Connect to Google Drive"):
                try:
                    # Create and store flow
                    flow = create_flow()
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    
                    # Store flow in session state BEFORE generating URL
                    st.session_state.oauth_flow = flow
                    
                    # Show auth URL
                    st.markdown(f'Click [here]({auth_url}) to connect your Google account')
                    return
                except Exception as e:
                    st.error(f"Failed to create authentication flow: {str(e)}")
                    return
    
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
