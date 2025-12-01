import os
import io
import pickle
import logging
from typing import Optional, List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import pdfplumber
import docx2txt
import streamlit as st
import streamlit.components.v1 as components


# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"
DEFAULT_PORT = 8080

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_credentials() -> Optional[Credentials]:
    """
    Get valid user credentials from storage or initiate OAuth flow.
    
    Returns:
        Valid Credentials object, or None if authentication fails.
    """
    creds = None
    
    # Try to load existing credentials
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except ValueError as e:
            logger.error(f"Token file is invalid: {e}")
            logger.info("Deleting token.json and creating new one...")
            os.remove(TOKEN_FILE)
    
    # Refresh or create new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing access token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None # Force re-auth

        if not creds:
            logger.info("Starting OAuth flow...")
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. Please download it from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, 
                SCOPES
            )
            creds = flow.run_local_server(
                port=DEFAULT_PORT,
                access_type='offline',
                prompt='consent'
            )
        
        # Save credentials for next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        logger.info(f"Credentials saved to {TOKEN_FILE}")
    
    return creds

@st.cache_resource
def get_drive_service():
    """Authentication to Google Drive"""
    try:
        creds = get_credentials()
        if not creds:
            logger.error("Failed to retrieve credentials.")
            return None
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Error creating Drive service: {e}")
        return None

def search_files(query_name):
    """Search for files by name containing the query_name."""
    service = get_drive_service()
    if not service:
        return []

    try:
        # Search for files with name containing the query, not trashed
        q = f"name contains '{query_name}' and trashed = false"
        results = service.files().list(
            q=q, pageSize=10, fields="nextPageToken, files(id, name, mimeType)").execute()
        items = results.get('files', [])
        return items
    except Exception as e:
        logger.error(f"An error occurred during search: {e}")
        return []

def read_file(file_id, mime_type):
    """Downloads and extracts text from a file."""
    service = get_drive_service()
    if not service:
        return "Error: Could not connect to Drive."

    try:
        request = service.files().get_media(fileId=file_id)

        # Handle Google Docs (export to text)
        if mime_type == 'application/vnd.google-apps.document':
            request = service.files().export_media(fileId=file_id, mimeType='text/plain')

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        fh.seek(0)

        # Extract text based on mime_type
        if mime_type == 'application/pdf':
            with pdfplumber.open(fh) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        elif 'wordprocessingml' in mime_type: # docx
            # docx2txt needs a file path or file-like object
            with open("temp.docx", "wb") as f:
                f.write(fh.read())
            text = docx2txt.process("temp.docx")
            os.remove("temp.docx")
            return text
        else:
            # Assume plain text
            return fh.read().decode('utf-8')

    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return f"Error reading file: {str(e)}"

if __name__ == "__main__":
    if not os.path.exists("credentials.json"):
        print("No credentials.json found. Skipping integration test.")
    else:
        # This will trigger the auth flow if no token.json
        files = search_files("test")
        print(f"Found: {files}")
