import os
import time
import tempfile
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import streamlit as st
from gdrive_handler import GDriveHandler
from process_csv import extract_csv_from_pdf, save_csv_data
from dotenv import load_dotenv
from settings import show_settings, check_settings

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
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8501"]
            }
        },
        scopes=SCOPES
    )
    
    # Clear any existing credentials to force re-authentication with new scopes
    if 'credentials' in st.session_state:
        st.session_state.credentials = None
    if 'oauth_flow' in st.session_state:
        st.session_state.oauth_flow = None
    
    # Set redirect URI to the Streamlit app URL
    flow.redirect_uri = "http://localhost:8501"
    return flow

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
        
        # Store credentials in session state
        st.session_state.credentials = st.session_state.oauth_flow.credentials
        
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
        return

def main():
    st.set_page_config(page_title="PDF to CSV Converter", layout="wide")
    st.title("PDF to CSV Converter with Google Drive")
    
    # Initialize session states
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None
    if 'show_settings' not in st.session_state:
        st.session_state.show_settings = False
    if 'oauth_flow' not in st.session_state:
        st.session_state.oauth_flow = None
    
    # Check for OAuth callback
    if 'code' in st.query_params:
        handle_oauth_callback()
        return
    
    # Show settings button in sidebar if authenticated
    if st.session_state.credentials:
        with st.sidebar:
            st.title("Navigation")
            if st.button("⚙️ Settings"):
                st.session_state.show_settings = True
    
    # Show settings page or main app
    if st.session_state.show_settings:
        show_settings()
        if st.button("Back to Main"):
            st.session_state.show_settings = False
            st.rerun()
    else:
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
                return
        
        # Check if settings are configured
        if not check_settings():
            st.warning("⚙️ Please configure your Gemini API settings first")
            if st.button("Go to Settings"):
                st.session_state.show_settings = True
                st.rerun()
            return
        
        # Main app interface after authentication
        st.success("Connected to Google Drive")
        
        try:
            # Create Google Drive handler
            gdrive_handler = GDriveHandler(st.session_state.credentials)
            
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
                                                
                                                # Process PDF
                                                csv_data = extract_csv_from_pdf(tmp_pdf.name)
                                                
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
            if "invalid_grant" in str(e) or "expired" in str(e):
                st.warning("Session expired. Please reconnect to Google Drive")
                st.session_state.credentials = None
                st.rerun()

if __name__ == "__main__":
    main()
