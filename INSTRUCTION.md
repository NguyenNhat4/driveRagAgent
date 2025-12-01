# Google Drive RAG Agent Instructions

This application allows you to ingest documents from a specific Google Drive folder into a local Qdrant vector database (using Hybrid Search) and chat with them using Google Gemini.

## Prerequisites

1.  **Python 3.10+**
2.  **Google Cloud Project** with:
    *   **Google Drive API** enabled.
    *   **Google Picker API** enabled.
3.  **OAuth Credentials (User Auth)**:
    *   Go to **APIs & Services > Credentials** in Google Cloud Console.
    *   Create **OAuth 2.0 Client ID** (Application type: **Desktop App** is easiest for local dev, or **Web application** if you are configuring redirect URIs correctly).
    *   Download the JSON file and rename it to `credentials.json` in the root of this project.
    *   **Note:** If using Web Application flow for the Picker, ensure the authorized Javascript origins include your streamlit url (e.g., `http://localhost:8501`).
4.  **API Key** (for Google Picker):
    *   Create an API Key in Google Cloud Console.
    *   Restrict it to the Google Picker API.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables:**
    Set the following environment variables. You can do this in your terminal.

    ```bash
    export GEMINI_API_KEY="your_gemini_api_key"
    export GOOGLE_API_KEY="your_google_api_key_for_picker"
    export GOOGLE_APP_ID="your_project_number" # Found in Google Cloud Console Dashboard
    ```

3.  **Credentials:**
    Ensure `credentials.json` is present in the root directory.

## Running the App

1.  Start Streamlit:
    ```bash
    streamlit run app.py
    ```

2.  **Ingestion (Tab 1):**
    *   **Auth (Backend):** When you click "Start Ingestion" for the first time, a browser window (or terminal link) will open asking you to login with your Google Account. This authorizes the Python backend to download files.
    *   **Auth (Frontend/Picker):** Click **Open Google Picker** to select a folder visually. Copy the Folder ID.
    *   Paste the ID and run ingestion.

3.  **Chat (Tab 2):**
    *   Switch to the Chat tab.
    *   Ask questions about the documents in the ingested folder.

## Troubleshooting

*   **"Port 8080 is in use"**: The backend auth tries to use port 8080. Ensure it's free or change `DEFAULT_PORT` in `utils/drive_tools.py`.
*   **Picker Authentication Error**: Ensure "Authorized Javascript origins" in your OAuth Client ID settings matches your Streamlit URL exactly (no trailing slash).
*   **"No valid credentials found"**: Check `credentials.json` path and content.
