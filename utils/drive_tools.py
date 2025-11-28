import os
import io
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import pdfplumber
import docx2txt

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service(creds_path="service_account.json"):
    """Authentication to Google Drive"""
    creds = None
    if os.path.exists(creds_path):
        try:
            creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Error loading service account: {e}")
            return None
    else:
        logger.warning(f"Service account file not found at {creds_path}")
        return None

    return build('drive', 'v3', credentials=creds)

def search_files(query_name, creds_path="service_account.json"):
    """Search for files by name containing the query_name."""
    service = get_drive_service(creds_path)
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

def read_file(file_id, mime_type, creds_path="service_account.json"):
    """Downloads and extracts text from a file."""
    service = get_drive_service(creds_path)
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
            # implementing a workaround or using a temp file might be needed
            # but docx2txt.process supports file-like objects? No, usually path.
            # Let's try writing to temp.
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
    # Mock test if no creds
    if not os.path.exists("service_account.json"):
        print("No service_account.json found. Skipping integration test.")
    else:
        files = search_files("test")
        print(f"Found: {files}")
