import os
import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from settings import get_storage

# OAuth 2.0 scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Access to files created by the app
    'https://www.googleapis.com/auth/drive.metadata.readonly',  # Read metadata for all files
    'https://www.googleapis.com/auth/userinfo.email',  # Get user's email address
    'https://www.googleapis.com/auth/userinfo.profile',  # Get user's basic profile info
    'openid'  # OpenID Connect
]

def debug_session_state(location):
    """Debug helper to print session state"""
    print(f"\n=== Session State at {location} ===")
    print(f"oauth_flow present: {'oauth_flow' in st.session_state}")
    print(f"credentials present: {'credentials' in st.session_state}")
    if 'oauth_flow' in st.session_state:
        print(f"oauth_flow: {st.session_state.oauth_flow}")
    print("=== End Session State ===\n")

def create_flow():
    """Create OAuth 2.0 flow instance"""
    try:
        debug_session_state("create_flow - start")
        
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("Missing Google OAuth credentials. Please check your environment variables.")
            
        # Determine the redirect URI based on environment
        is_production = os.getenv('PRODUCTION', 'false').lower() == 'true'
        redirect_uri = "https://pdf-to-csv-paani.streamlit.app/" if is_production else "http://localhost:8501/"
        
        print(f"Creating flow with redirect URI: {redirect_uri}")
        
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Configure for out of band flow
        flow.prompt = 'consent'
        flow.access_type = 'offline'  # Get refresh token
        
        debug_session_state("create_flow - end")
        return flow
        
    except Exception as e:
        print(f"Error in create_flow: {str(e)}")
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
        debug_session_state("handle_oauth_callback - start")
        
        if 'oauth_flow' not in st.session_state:
            print("No oauth_flow in session state")
            st.error("OAuth flow not found in session state. Please try connecting to Google Drive again.")
            return
        
        if not st.session_state.oauth_flow:
            print("oauth_flow is None in session state")
            st.error("OAuth flow is None in session state. Please try connecting to Google Drive again.")
            return

        flow = st.session_state.oauth_flow
        print(f"Retrieved flow from session state: {flow}")
        
        # Get the authorization code from URL parameters
        code = st.query_params.get('code')
        if not code:
            print("No code in query parameters")
            st.error("No authorization code received")
            return
        
        print(f"Received authorization code: {code[:10]}...")
        
        # Get the redirect URI
        is_production = os.getenv('PRODUCTION', 'false').lower() == 'true'
        redirect_uri = "https://pdf-to-csv-paani.streamlit.app/" if is_production else "http://localhost:8501/"
        
        print(f"Using redirect URI for token exchange: {redirect_uri}")
        
        # Exchange code for tokens
        try:
            flow.fetch_token(
                code=code,
                authorization_response=f"{redirect_uri}?code={code}"
            )
            print("Successfully exchanged code for tokens")
        except Exception as e:
            print(f"Error exchanging code for tokens: {str(e)}")
            raise
        
        credentials = flow.credentials
        print("Got credentials from flow")
        
        # Save credentials
        st.session_state.credentials = credentials
        save_oauth_credentials(credentials)
        print("Saved credentials")
        
        # Clear the OAuth flow from session state
        st.session_state.oauth_flow = None
        print("Cleared oauth_flow from session state")
        
        debug_session_state("handle_oauth_callback - before rerun")
        
        st.success("Successfully connected to Google Drive!")
        st.rerun()
        
    except Exception as e:
        print(f"Error in handle_oauth_callback: {str(e)}")
        st.error(f"Failed to exchange token: {str(e)}")
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

def disconnect_google_drive():
    """Disconnect from Google Drive by clearing credentials and session state"""
    try:
        debug_session_state("disconnect_google_drive - start")
        
        # Clear credentials from session state
        st.session_state.credentials = None
        
        # Clear oauth flow if present
        if 'oauth_flow' in st.session_state:
            st.session_state.oauth_flow = None
        
        # Clear stored credentials
        storage = get_storage()
        storage.delete_credential('oauth_credentials')
        
        print("Successfully cleared all Google Drive credentials and session state")
        debug_session_state("disconnect_google_drive - end")
        
        st.success("Successfully disconnected from Google Drive!")
        st.rerun()
        
    except Exception as e:
        print(f"Error in disconnect_google_drive: {str(e)}")
        st.error(f"Failed to disconnect from Google Drive: {str(e)}")

def initialize_oauth():
    """Initialize OAuth-related session state variables"""
    debug_session_state("initialize_oauth - start")
    
    if 'oauth_flow' not in st.session_state:
        print("Initializing oauth_flow in session state")
        st.session_state.oauth_flow = None
    if 'credentials' not in st.session_state:
        print("Initializing credentials in session state")
        st.session_state.credentials = load_oauth_credentials()
    
    # Allow OAuth for local development
    is_production = os.getenv('PRODUCTION', 'false').lower() == 'true'
    if not is_production:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
    debug_session_state("initialize_oauth - end")
