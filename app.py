import streamlit as st
import os
import json
import streamlit.components.v1 as components
from flow import create_ingestion_flow, create_retrieval_flow
from utils.drive_tools import get_drive_service

st.set_page_config(page_title="Google Drive RAG Agent", layout="wide")

# Read Google App Credentials from credentials.json
CLIENT_ID = ""
APP_ID = ""
API_KEY = os.getenv("GOOGLE_API_KEY", "")

if os.path.exists("credentials.json"):
    try:
        with open("credentials.json", "r") as f:
            creds_data = json.load(f)
            # Handle different formats (installed vs web)
            if 'installed' in creds_data:
                CLIENT_ID = creds_data['installed'].get('client_id', '')
            elif 'web' in creds_data:
                CLIENT_ID = creds_data['web'].get('client_id', '')

            # App ID (Project Number) is usually not in credentials.json explicitly in the same way,
            # but users might confuse Project ID with Project Number.
            # For Picker, we need Project Number.
            # If not found, we fallback to env var.
            APP_ID = os.getenv("GOOGLE_APP_ID", "")
    except Exception as e:
        st.error(f"Error reading credentials.json: {e}")

st.title("🤖 Chat with your Google Drive (Hybrid Search)")

# Check Env Vars
if "GEMINI_API_KEY" not in os.environ:
    st.warning("⚠️ GEMINI_API_KEY is missing from environment variables.")
else:
    # We rely on os.environ being set by the user or .env
    pass

if not API_KEY:
    st.warning("⚠️ GOOGLE_API_KEY (for Picker) is missing from environment variables.")

# Tabs
tab1, tab2 = st.tabs(["📂 Ingest Data", "💬 Chat"])

with tab1:
    st.header("Ingest Folder")

    st.markdown("""
    **Step 1: Authenticate & Pick Folder**
    1. Ensure `credentials.json` is in the root directory.
    2. Click below to open Google Picker.
    3. If this is your first time, you will be redirected to login (terminal or browser window) for the backend processing as well.
    """)

    if st.button("Open Google Picker"):
        if not CLIENT_ID:
            st.error("Client ID not found in credentials.json. Please check your setup.")
        else:
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
        elif not os.path.exists("credentials.json"):
            st.error("credentials.json not found. Please place it in the root directory.")
        else:
            with st.spinner("Authenticating and processing files... check your terminal if a login window doesn't appear."):
                shared = {
                    "folder_id": folder_id_input
                }

                try:
                    ingest_flow = create_ingestion_flow()
                    ingest_flow.run(shared)

                    st.success(shared.get("index_status", "Ingestion completed!"))
                    docs = shared.get('documents', [])
                    chunks = shared.get('chunks', [])
                    if docs:
                        st.info(f"Processed {len(docs)} files into {len(chunks)} chunks.")
                    else:
                        st.warning("No files found or processed. Check permissions or folder content.")

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
                    if context:
                        for c in context:
                            st.markdown(f"**Source:** {c.payload['metadata']['source']}")
                            st.text(c.payload['text'][:200] + "...")
                            st.divider()
                    else:
                        st.write("No context retrieved.")

                answer = shared.get("answer", "I couldn't generate an answer.")
                message_placeholder.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"Error: {e}")
