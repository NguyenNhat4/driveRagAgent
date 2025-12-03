import streamlit as st
import os
import streamlit.components.v1 as components
from dotenv import load_dotenv
from flow import create_ingestion_flow, create_retrieval_flow
from utils.drive_tools import get_drive_service

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Google Drive RAG Agent", layout="wide")

# Env Var Setup
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = st.text_input("Enter Gemini API Key", type="password")

# Read Google App Credentials from Env
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
APP_ID = os.getenv("GOOGLE_APP_ID", "") # Project Number
API_KEY = os.getenv("GOOGLE_API_KEY", "")

st.title("🤖 Chat with your Google Drive (Hybrid Search)")

# Tabs
tab1, tab2 = st.tabs(["📂 Ingest Data", "💬 Chat"])

with tab1:
    st.header("Ingest Folder")

    st.markdown("""
    **Step 1: Pick a Folder**
    Click the button below to open Google Picker. Select a folder, and copy its ID.
    *Note: Ensure you have authorized the app.*
    """)

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
        elif not os.path.exists("credentials.json"):
            st.error("credentials.json not found. Please setup your Google Cloud Project and download the credentials file.")
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
                        st.markdown(f"**Source:** {c.payload['metadata']['source']}")
                        st.text(c.payload['text'][:200] + "...")
                        st.divider()

                answer = shared.get("answer", "I couldn't generate an answer.")
                message_placeholder.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"Error: {e}")
