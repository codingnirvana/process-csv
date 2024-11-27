import json
from typing import Any, Dict
import streamlit as st
from streamlit_local_storage import LocalStorage

class BrowserStorage:
    """
    A class to manage credentials and API keys using browser's localStorage.
    The storage persists across browser refreshes and restarts.
    """
    
    def __init__(self, prefix: str = "app_"):
        """
        Initialize the BrowserStorage.
        
        Args:
            prefix (str): Prefix for storage keys to avoid naming conflicts
        """
        self.prefix = prefix
        self.storage = LocalStorage()
    
    def save_credential(self, name: str, value: Any) -> bool:
        """
        Save a credential to localStorage.
        
        Args:
            name (str): Name/identifier for the credential
            value (Any): Value to store (must be JSON serializable)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"{self.prefix}{name}"
            serialized_value = json.dumps(value)
            self.storage.setItem(key, serialized_value)
            return True
        except Exception as e:
            print(f"Error saving credential: {str(e)}")
            return False
    
    def get_credential(self, name: str, default: Any = None) -> Any:
        """
        Retrieve a credential from localStorage.
        
        Args:
            name (str): Name/identifier of the credential
            default (Any): Default value if credential doesn't exist
            
        Returns:
            Any: The credential value or default if not found
        """
        try:
            key = f"{self.prefix}{name}"
            result = self.storage.getItem(key)
            if result is None:
                return default
            return json.loads(result)
        except Exception as e:
            print(f"Error retrieving credential: {str(e)}")
            return default
    
    def delete_credential(self, name: str) -> bool:
        """
        Delete a credential from localStorage.
        
        Args:
            name (str): Name/identifier of the credential to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"{self.prefix}{name}"
            self.storage.deleteItem(key)
            return True
        except Exception as e:
            print(f"Error deleting credential: {str(e)}")
            return False
    
    def list_credentials(self) -> Dict[str, Any]:
        """
        Get a dictionary of all stored credentials.
        
        Returns:
            Dict[str, Any]: Dictionary of credential names and their values
        """
        try:
            items = {}
            # Get all items from localStorage
            all_items = self.storage.getAll()
            if all_items:
                for key, value in all_items.items():
                    if key.startswith(self.prefix):
                        items[key[len(self.prefix):]] = json.loads(value)
            return items
        except Exception as e:
            print(f"Error listing credentials: {str(e)}")
            return {}
    
    def clear_all_credentials(self) -> bool:
        """
        Clear all stored credentials from localStorage.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete all items with our prefix
            all_items = self.storage.getAll()
            if all_items:
                for key in all_items.keys():
                    if key.startswith(self.prefix):
                        self.storage.deleteItem(key)
            return True
        except Exception as e:
            print(f"Error clearing credentials: {str(e)}")
            return False
