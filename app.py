import streamlit as st
import os
import json
import streamlit.components.v1 as components
from dotenv import load_dotenv
from flow import create_ingestion_flow, create_retrieval_flow
from utils.drive_tools import get_drive_service

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Google Drive RAG Agent", layout="wide")

# Check for Gemini API Key
if "GEMINI_API_KEY" not in os.environ:
    st.error("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
    st.stop()

# Helper to load credentials from JSON if Env Vars are missing
def load_google_creds():
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    app_id = os.getenv("GOOGLE_APP_ID", "") # Project Number
    api_key = os.getenv("GOOGLE_API_KEY", "")

    if not client_id or not app_id:
        if os.path.exists("credentials.json"):
            try:
                with open("credentials.json", "r") as f:
                    creds = json.load(f)
                    # Look for installed or web
                    data = creds.get("installed") or creds.get("web")
                    if data:
                        if not client_id:
                            client_id = data.get("client_id", "")
                        if not app_id:
                            # Try project_id as fallback, though strictly should be project_number
                            app_id = data.get("project_id", "")
            except Exception as e:
                st.error(f"Error reading credentials.json: {e}")

    return client_id, app_id, api_key

CLIENT_ID, APP_ID, API_KEY = load_google_creds()

st.title("🤖 Chat with your Google Drive (Hybrid Search)")

# Tabs
tab1, tab2 = st.tabs(["📂 Ingest Data", "💬 Chat"])

with tab1:
    st.header("Ingest Folder")

    st.markdown("""
    **Step 1: Pick a Folder**
    Click the button below to open Google Picker. Select a folder, and copy its ID.
    *Note: You will be asked to authenticate with Google if you haven't already.*
    """)

    # Check if we have necessary keys for Picker
    if not CLIENT_ID:
         st.warning("⚠️ Google Client ID is missing. Please set GOOGLE_CLIENT_ID in .env or provide credentials.json.")
    if not API_KEY:
         st.warning("⚠️ Google API Key is missing. Please set GOOGLE_API_KEY in .env. The Picker requires a Browser API Key.")

    # Check if APP_ID looks like a project number (numeric)
    if APP_ID and not APP_ID.isdigit():
        st.warning(f"⚠️ 'GOOGLE_APP_ID' (Project Number) appears to be non-numeric ('{APP_ID}'). The Google Picker API usually requires the numeric Project Number. Please set GOOGLE_APP_ID in your .env file.")

    if st.button("Open Google Picker"):
        with open("templates/google_picker.html", "r") as f:
            html_template = f.read()

        # Inject Creds
        html_content = html_template.replace("{client_id}", CLIENT_ID)\
                                    .replace("{app_id}", APP_ID)\
                                    .replace("{api_key}", API_KEY)

        components.html(html_content, height=600, scrolling=True)

    st.markdown("---")

    st.markdown("**Step 2: Run Ingestion**")
    folder_id_input = st.text_input("Paste Folder ID here:")

    if st.button("Start Ingestion"):
        if not folder_id_input:
            st.error("Please enter a Folder ID.")
        else:
            with st.spinner("Loading files, chunking, and indexing... This may take a while."):
                shared = {
                    "folder_id": folder_id_input
                }

                try:
                    ingest_flow = create_ingestion_flow()
                    ingest_flow.run(shared)

                    st.success(shared.get("index_status", "Ingestion completed!"))
                    st.info(f"Processed {len(shared.get('documents', []))} files into {len(shared.get('chunks', []))} chunks.")

                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

with tab2:
    st.header("Chat with Data")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask something about your documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")

            shared = {"user_query": prompt}

            try:
                retrieval_flow = create_retrieval_flow()
                retrieval_flow.run(shared)

                # Show retrieved snippets (optional debug)
                context = shared.get("retrieved_context", [])
                with st.expander("View Retrieved Context"):
                    for c in context:
                        metadata = c.payload.get('metadata', {})
                        source = metadata.get('source', 'Unknown')
                        st.markdown(f"**Source:** {source}")
                        st.text(c.payload['text'][:200] + "...")
                        st.divider()

                answer = shared.get("answer", "I couldn't generate an answer.")
                message_placeholder.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"Error: {e}")
