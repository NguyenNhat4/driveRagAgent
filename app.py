import streamlit as st
import os
import streamlit.components.v1 as components
from dotenv import load_dotenv
from flow import create_ingestion_flow, create_retrieval_flow
from utils.drive_tools import get_service_account_email
from utils.embedding_models import get_embedding_models

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Google Drive RAG Agent", layout="wide")

# Pre-load embedding models
with st.spinner("Initializing AI Models..."):
    get_embedding_models()

# Env Var Setup
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = st.text_input("Enter Gemini API Key", type="password")

st.title("🤖 Chat with your Google Drive (Hybrid Search)")

# Tabs
tab1, tab2 = st.tabs(["📂 Ingest Data", "💬 Chat"])

with tab1:
    st.header("Ingest Folder")

    # Display Service Account Email
    sa_email = get_service_account_email()
    st.info(f"**Action Required:** Please share your Google Drive folder with this Service Account email:\n\n`{sa_email}`")

    st.markdown("---")

    st.markdown("**Step 2: Run Ingestion**")
    folder_id_input = st.text_input("Paste Folder ID here:", help="The ID string from the URL of your Google Drive folder.")

    if st.button("Start Ingestion"):
        if not folder_id_input:
            st.error("Please enter a Folder ID.")
        elif "Unknown" in sa_email and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.path.exists("service_account.json"):
             st.error("Service Account Credentials not found. Please add 'service_account.json' to the root or set GOOGLE_APPLICATION_CREDENTIALS.")
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
