import os
import io
import logging
from typing import Optional, List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
import pdfplumber
import docx2txt
import streamlit as st

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.metadata.readonly']
# We prioritize env var, but fallback to a default file name
DEFAULT_SERVICE_ACCOUNT_FILE = "service_account.json"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_credentials() -> Optional[service_account.Credentials]:
    """
    Get valid Service Account credentials from storage or environment.
    """
    creds = None
    
    # Check for GOOGLE_APPLICATION_CREDENTIALS env var first
    gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if gac and os.path.exists(gac):
        try:
            creds = service_account.Credentials.from_service_account_file(gac, scopes=SCOPES)
            return creds
        except Exception as e:
            logger.error(f"Error loading credentials from {gac}: {e}")

    # Fallback to default file in root
    if os.path.exists(DEFAULT_SERVICE_ACCOUNT_FILE):
        try:
            creds = service_account.Credentials.from_service_account_file(DEFAULT_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            return creds
        except Exception as e:
            logger.error(f"Error loading credentials from {DEFAULT_SERVICE_ACCOUNT_FILE}: {e}")
            
    logger.error("No valid service account credentials found.")
    return None

def get_service_account_email() -> str:
    """
    Helper to get the service account email for display.
    """
    creds = get_credentials()
    if creds and hasattr(creds, 'service_account_email'):
        return creds.service_account_email
    return "Unknown (Check credentials)"

# Global variable to cache the service instance
_DRIVE_SERVICE = None

def get_drive_service():
    """Authentication to Google Drive"""
    global _DRIVE_SERVICE
    if _DRIVE_SERVICE:
        return _DRIVE_SERVICE

    creds = get_credentials()
    if not creds:
        logger.error("Could not obtain valid credentials.")
        return None

    _DRIVE_SERVICE = build('drive', 'v3', credentials=creds)
    return _DRIVE_SERVICE

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
            with open("temp.docx", "wb") as f:
                f.write(fh.read())
            try:
                text = docx2txt.process("temp.docx")
            finally:
                if os.path.exists("temp.docx"):
                    os.remove("temp.docx")
            return text
        else:
            # Assume plain text
            return fh.read().decode('utf-8')

    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return f"Error reading file: {str(e)}"

if __name__ == "__main__":
    # Mock test
    email = get_service_account_email()
    print(f"Service Account Email: {email}")
