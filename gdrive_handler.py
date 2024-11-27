import os
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from pathlib import Path
import time
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GDriveHandler:
    """Handler for Google Drive operations"""
    
    def __init__(self, credentials):
        """Initialize the Google Drive service"""
        self.service = build('drive', 'v3', credentials=credentials)
    
    def list_folders(self, parent_id=None):
        """List folders in Google Drive or within a specific folder"""
        try:
            # First verify the service is working
            about = self.service.about().get(fields="user").execute()
            
            # Then list folders
            query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, parents)',
                pageSize=1000  # Increase page size
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            logging.error(f"Error listing folders: {str(e)}")
            if "invalid_grant" in str(e):
                raise Exception("Your Google Drive session has expired. Please reconnect.")
            elif "insufficientPermissions" in str(e):
                raise Exception("Insufficient permissions to list folders. Please check your Google Drive access.")
            else:
                raise Exception(f"Failed to list folders: {str(e)}")
    
    def get_folder_path(self, folder_id):
        """Get the full path of a folder"""
        try:
            path = []
            current_id = folder_id
            
            while current_id:
                file = self.service.files().get(
                    fileId=current_id,
                    fields='id, name, parents'
                ).execute()
                
                path.insert(0, {'id': file['id'], 'name': file['name']})
                current_id = file.get('parents', [None])[0]
            
            return path
            
        except Exception as e:
            logging.error(f"Error getting folder path: {str(e)}")
            raise Exception(f"Failed to get folder path: {str(e)}")
    
    def create_folder(self, folder_name, parent_id=None):
        """Create a folder in Google Drive"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            file = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except Exception as e:
            logging.error(f"Error creating folder: {str(e)}")
            raise Exception(f"Failed to create folder: {str(e)}")
    
    def create_folder_path(self, path_parts, parent_id=None):
        """Create a folder path, creating intermediate folders if needed"""
        try:
            current_parent = parent_id
            for part in path_parts:
                # Check if folder exists
                query = f"name = '{part}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                if current_parent:
                    query += f" and '{current_parent}' in parents"
                
                results = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id)'
                ).execute()
                
                files = results.get('files', [])
                
                if files:
                    current_parent = files[0]['id']
                else:
                    current_parent = self.create_folder(part, current_parent)
            
            return current_parent
            
        except Exception as e:
            logging.error(f"Error creating folder path: {str(e)}")
            raise Exception(f"Failed to create folder path: {str(e)}")
    
    def list_files(self, folder_id, mime_type=None, recursive=False):
        """List files in a folder"""
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            if mime_type:
                query += f" and mimeType = '{mime_type}'"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, parents)'
            ).execute()
            
            files = results.get('files', [])
            
            if recursive:
                # Get subfolders
                folders = [f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder']
                for folder in folders:
                    files.extend(self.list_files(folder['id'], mime_type, recursive=True))
            
            return files
            
        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            raise Exception(f"Failed to list files: {str(e)}")
    
    def download_file(self, file_id, local_path):
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
        except Exception as e:
            logging.error(f"Error downloading file: {str(e)}")
            raise Exception(f"Failed to download file: {str(e)}")
    
    def upload_file(self, local_path, parent_id=None, new_filename=None):
        """Upload a file to Google Drive"""
        try:
            file_metadata = {
                'name': new_filename or os.path.basename(local_path)
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            media = MediaFileUpload(
                local_path,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except Exception as e:
            logging.error(f"Error uploading file: {str(e)}")
            raise Exception(f"Failed to upload file: {str(e)}")

    def process_local_directory(self, local_dir, gdrive_parent_id=None, progress_callback=None):
        """Process a local directory and mirror its structure in Google Drive."""
        local_path = Path(local_dir)
        
        # Create corresponding folder in Google Drive
        folder_name = local_path.name
        current_folder_id = self.create_folder(folder_name, gdrive_parent_id)
        
        if progress_callback:
            progress_callback(f"Processing directory: {local_path}")

        # Process all items in the directory
        for item in local_path.iterdir():
            if item.is_dir():
                # Recursively process subdirectories
                self.process_local_directory(
                    item, 
                    current_folder_id, 
                    progress_callback
                )
            elif item.is_file() and item.suffix.lower() == '.pdf':
                if progress_callback:
                    progress_callback(f"Uploading file: {item.name}")
                try:
                    self.upload_file(str(item), current_folder_id)
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    logging.error(f"Error uploading {item.name}: {str(e)}")

        return current_folder_id
