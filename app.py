import os
import time
import tempfile
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import streamlit as st
from gdrive_handler import GDriveHandler
from process_csv import extract_csv_from_pdf, save_csv_data
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OAuth 2.0 configuration
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

def create_flow():
    """Create OAuth flow for Google Drive authentication"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Missing OAuth credentials. Please set GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET environment variables."
        )
    
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8501"]
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri="http://localhost:8501"
    )

def main():
    st.set_page_config(page_title="PDF to CSV Converter", layout="wide")
    st.title("PDF to CSV Converter with Google Drive")
    
    # Initialize session state for credentials
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None
    
    # Initialize flow in session state if not present
    if 'oauth_flow' not in st.session_state:
        st.session_state.oauth_flow = None
    
    # Check for Google Drive authentication
    if not st.session_state.credentials:
        st.info("""
        ### Google Drive Authentication Required
        
        This app requires Google Drive access to store processed files. Since the app is in testing mode:
        1. You must be added as a test user
        2. Use the same Google account that was added as a test user
        3. Accept the unverified app warning during login
        """)
        
        # Handle OAuth callback
        if 'code' in st.query_params:
            try:
                if st.session_state.oauth_flow is None:
                    st.session_state.oauth_flow = create_flow()
                
                code = st.query_params['code']
                st.session_state.oauth_flow.fetch_token(code=code)
                st.session_state.credentials = st.session_state.oauth_flow.credentials
                st.success("Successfully connected to Google Drive!")
                st.rerun()
            except Exception as e:
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
                else:
                    st.error(f"Failed to authenticate: {str(e)}")
                return
        
        # Show connect button if not in OAuth callback
        if st.button("Connect to Google Drive"):
            try:
                st.session_state.oauth_flow = create_flow()
                auth_url, _ = st.session_state.oauth_flow.authorization_url(prompt='consent')
                st.markdown(f'Click [here]({auth_url}) to connect your Google account')
            except Exception as e:
                st.error(f"Failed to create authentication flow: {str(e)}")
            return
        
        return
    
    # Main app interface after authentication
    st.success("Connected to Google Drive")
    
    try:
        # Create Google Drive handler
        gdrive_handler = GDriveHandler(st.session_state.credentials)
        
        # Get or create folders
        st.subheader("Google Drive Folders")
        
        # Simple create folder button first
        if st.button("➕ Create New Folder"):
            with st.spinner("Creating folder..."):
                new_folder_name = f"PDF_Input_{time.strftime('%Y%m%d_%H%M%S')}"
                folder_id = gdrive_handler.create_folder(new_folder_name)
                st.session_state.input_folder_id = folder_id
                st.success(f"Created folder: {new_folder_name}")
                time.sleep(1)
                st.rerun()
        
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
            
            # Show folder selection
            selected = st.selectbox(
                "Select a folder containing PDFs:",
                options=folder_options,
                format_func=lambda x: x["name"]
            )
            
            if selected and selected["id"]:
                st.write(f"Selected: {selected['name']}")
                st.markdown(f"🔗 [Open in Google Drive](https://drive.google.com/drive/folders/{selected['id']})")
                
                # List PDF files
                with st.spinner("Checking for PDF files..."):
                    pdf_files = gdrive_handler.list_files(selected["id"], "application/pdf", recursive=True)
                    if pdf_files:
                        st.success(f"Found {len(pdf_files)} PDF files")
                        if st.button("🔄 Process Files", type="primary"):
                            # Create output folder quietly
                            timestamp = time.strftime("%Y%m%d_%H%M%S")
                            output_folder_name = f"CSV_Output_{timestamp}"
                            output_folder_id = gdrive_handler.create_folder(output_folder_name)
                            
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
                                                # Create CSV filename
                                                csv_filename = f"{os.path.splitext(pdf_file['name'])[0]}_{timestamp}.csv"
                                                
                                                # Save and upload CSV
                                                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_csv:
                                                    save_csv_data(csv_data, tmp_csv.name)
                                                    gdrive_handler.upload_file(
                                                        tmp_csv.name,
                                                        output_folder_id,
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
                                st.markdown(f"🔗 [Open Output Folder](https://drive.google.com/drive/folders/{output_folder_id})")
                                
                            except Exception as e:
                                st.error(f"❌ Processing failed: {str(e)}")
                            
                            finally:
                                progress_bar.empty()
                    else:
                        st.warning("No PDF files found in this folder")
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
