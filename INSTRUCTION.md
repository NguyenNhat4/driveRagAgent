# Google Drive RAG Agent Instructions

This application allows you to ingest documents from a specific Google Drive folder into a local Qdrant vector database (using Hybrid Search) and chat with them using Google Gemini.

## Prerequisites

1.  **Python 3.10+**
2.  **Google Cloud Project** with:
    *   **Google Drive API** enabled.
    *   **Google Picker API** enabled.
3.  **Service Account** (for Backend Access):
    *   Create a Service Account in your Google Cloud Console.
    *   Download the JSON key file and rename it to `service_account.json` in the root of this project.
    *   **Crucial:** You must share the Google Drive folders you want to ingest with the email address of this Service Account (found inside the JSON file, usually `client_email`).
4.  **OAuth 2.0 Client ID** (for Google Picker Frontend):
    *   Create an OAuth Client ID (Web Application).
    *   Add your local URL (e.g., `http://localhost:8501`) to "Authorized JavaScript origins".
    *   Note the `Client ID` and `Project Number` (App ID).
5.  **API Key** (for Google Picker):
    *   Create an API Key in Google Cloud Console.
    *   Restrict it to the Google Picker API (recommended).

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables:**
    Set the following environment variables. You can do this in your terminal or create a `.env` file (if you use `python-dotenv`, otherwise just export them).

    ```bash
    export GEMINI_API_KEY="your_gemini_api_key"
    export GOOGLE_CLIENT_ID="your_oauth_client_id"
    export GOOGLE_APP_ID="your_project_number"
    export GOOGLE_API_KEY="your_google_api_key" # for Picker
    ```

    *   `GEMINI_API_KEY`: Get this from Google AI Studio.
    *   `GOOGLE_CLIENT_ID`: From OAuth Client.
    *   `GOOGLE_APP_ID`: Project Number (not project ID string, the numeric one).
    *   `GOOGLE_API_KEY`: API Key for Picker.

3.  **Service Account:**
    Ensure `service_account.json` is present in the root directory.

## Running the App

1.  Start Streamlit:
    ```bash
    streamlit run app.py
    ```

2.  **Ingestion (Tab 1):**
    *   Click **Open Google Picker**.
    *   Authenticate with your Google Account.
    *   Select a folder.
    *   Copy the **Folder ID** displayed.
    *   Paste it into the "Folder ID" field.
    *   **Important:** Go to Google Drive and **Share** that folder with your Service Account email (e.g., `my-agent@my-project.iam.gserviceaccount.com`).
    *   Click **Start Ingestion**.
    *   Wait for the process to complete (logs will show file reading and chunking).

3.  **Chat (Tab 2):**
    *   Switch to the Chat tab.
    *   Ask questions about the documents in the ingested folder.

## Architecture

*   **PocketFlow**: Orchestrates the logic via `Flows` and `Nodes`.
*   **Nodes**:
    *   `LoadFolderNode`: Reads files from Drive.
    *   `ChunkNode`: Splits text using Recursive Character Splitter.
    *   `QdrantIndexNode`: Upserts chunks to local Qdrant (Hybrid: Dense + Sparse).
    *   `QdrantSearchNode`: Retrieves context.
    *   `AnswerNode`: Generates answers using Gemini.
*   **Database**: Local Qdrant instance (persisted in `./qdrant_db`).
