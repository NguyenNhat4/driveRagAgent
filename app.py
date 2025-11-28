import streamlit as st
import os
import tempfile
from flow import create_rag_flow

st.set_page_config(page_title="Google Drive RAG Agent", layout="wide")

st.title("🤖 Chat with your Google Drive")
st.write("Hỏi đáp thông tin từ tài liệu trong Google Drive của bạn (Tiếng Việt).")

# Sidebar for configuration
with st.sidebar:
    st.header("Cấu hình")

    # API Key
    api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

    # Service Account
    st.subheader("Google Drive Auth")
    uploaded_file = st.file_uploader("Upload service_account.json", type=["json"])

    creds_path = "service_account.json"
    if uploaded_file is not None:
        # Save to a temp file or overwrite local (in a real app, handle securely)
        # For this demo, we'll write to the current directory so the utils can find it
        with open("service_account.json", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("Credential file loaded!")
    else:
        if os.path.exists("service_account.json"):
            st.info("Using existing service_account.json")
        else:
            st.warning("Please upload service_account.json to access Drive.")

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input
if prompt := st.chat_input("Bạn muốn tìm gì trong Drive?"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Debugging: Đang suy nghĩ...")

        # Prepare Shared Store
        shared = {
            "user_query": prompt,
            "creds_path": "service_account.json"
        }

        # Run Flow
        try:
            rag_flow = create_rag_flow()

            # We can visualize progress if we hook into the nodes or just check results after
            # Since PocketFlow is synchronous (for now), we'll wait for result.

            message_placeholder.markdown("🔍 Đang tìm kiếm file...")
            rag_flow.run(shared)

            # Check intermediate steps to show progress info
            status_text = ""
            if "search_term" in shared:
                status_text += f"ℹ️ Đã tìm kiếm với từ khóa: `{shared['search_term']}`\n\n"

            files = shared.get("files_found", [])
            if files:
                status_text += f"📄 Đã tìm thấy file: **{files[0]['name']}**\n\n"
            elif shared.get("search_term") != "NONE":
                status_text += "❌ Không tìm thấy file phù hợp.\n\n"

            final_answer = shared.get("answer", "Xin lỗi, đã có lỗi xảy ra.")

            full_response = status_text + final_answer
            message_placeholder.markdown(full_response)

            # Add to history
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"Error: {e}")
