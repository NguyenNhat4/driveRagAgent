# Google Drive RAG Agent - Setup Guide

This guide explains how to set up the Google Cloud Platform (GCP) project and configure the environment for the Google Drive RAG Agent.

## Prerequisites

- A Google Cloud account.
- Python 3.9+ installed.
- Access to the Google Drive folder you want to ingest.

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click on the project dropdown at the top and select **New Project**.
3. Name your project (e.g., `drive-rag-agent`) and click **Create**.

## Step 2: Enable APIs

1. In the sidebar, go to **APIs & Services > Library**.
2. Search for and enable the following APIs:
   - **Google Drive API** (for backend access)
   - **Google Picker API** (for the frontend folder selector)

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**.
2. Select **External** (unless you are in a Google Workspace organization and want to limit it to internal users) and click **Create**.
3. Fill in the **App Information**:
   - App name: `Drive RAG Agent`
   - User support email: Your email.
4. Click **Save and Continue**.
5. **Scopes**:
   - Click **Add or Remove Scopes**.
   - Add `.../auth/drive.metadata.readonly` and `.../auth/drive.readonly`.
   - Click **Update** and then **Save and Continue**.
6. **Test Users**:
   - Add your own Google email address as a test user.
   - Click **Save and Continue**.

## Step 4: Create Credentials

You need two types of credentials: an **OAuth 2.0 Client ID** and an **API Key**.

### A. OAuth 2.0 Client ID (for Authentication)

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Select **Desktop app** (since we are running this locally/via Streamlit backend logic for the initial auth flow).
   - Name it `Desktop Client`.
   - Click **Create**.
   - **Download** the JSON file.
   - **Rename** it to `credentials.json` and place it in the root directory of this project.

### B. API Key (for Google Picker)

1. On the Credentials page, click **Create Credentials > API Key**.
2. Copy the API Key. You will use this in the `.env` file.
3. (Optional but Recommended) Restrict the key:
   - Click the pencil icon to edit the key.
   - Under **API restrictions**, select **Restrict key** and choose **Google Picker API**.

### C. OAuth 2.0 Client ID (for Google Picker - Web Application)

*Note: Google Picker requires a "Web application" Client ID to work correctly in the browser.*

1. Click **Create Credentials > OAuth client ID**.
2. Select **Web application**.
3. Name it `Web Client`.
4. **Authorized JavaScript origins**:
   - You need to add the URL where your Streamlit app is running.
   - If running locally, this is usually `http://localhost:8501`.
   - The app will display the exact origin you need to add in the "Troubleshooting" section of the Picker UI.
5. Click **Create**.
6. Copy the **Client ID**. You will use this in the `.env` file.

## Step 5: Get Project Number

1. Go to the [Google Cloud Dashboard](https://console.cloud.google.com/home/dashboard).
2. Locate the **Project Number** (numeric) on the dashboard info card.

## Step 6: Environment Configuration

1. Create a file named `.env` in the root directory.
2. Add the following variables:

```env
# Gemini LLM Key
GEMINI_API_KEY=your_gemini_api_key_here

# Google Cloud Project Credentials
# Use the "Web application" Client ID for the Picker
GOOGLE_CLIENT_ID=your_web_client_id_here

# Use the "Desktop app" Client ID logic is handled by credentials.json,
# but the Picker needs the Web Client ID.

GOOGLE_APP_ID=your_project_number_here
GOOGLE_API_KEY=your_api_key_here
```

**Important Note on Client IDs:**
- This application uses a hybrid approach.
- The **backend** (Python) uses `credentials.json` (Desktop Client) to authenticate and read files from Drive.
- The **frontend** (Google Picker) uses `GOOGLE_CLIENT_ID` (Web Client) and `GOOGLE_API_KEY` to let you select folders.

## Step 7: Run the Application

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run Streamlit:
   ```bash
   streamlit run app.py
   ```
3. Open your browser to the URL shown (usually `http://localhost:8501`).

## Troubleshooting

- **403 Forbidden**: Ensure you enabled the APIs and added yourself as a Test User.
- **Origin Mismatch / Invalid Request in Picker**: Check the `GOOGLE_CLIENT_ID` in `.env` matches the Web Client ID in Console, and that `http://localhost:8501` is added to Authorized JavaScript Origins.
- **Token Issues**: If you change scopes or encounter auth errors, delete the `token.json` file to force re-authentication.
