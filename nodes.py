from pocketflow import Node
from utils.call_llm import call_llm
from utils.drive_tools import search_files, read_file, get_drive_service
import os
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Existing Nodes (Modified if needed) ---

class ExtractSearchTermNode(Node):
    def prep(self, shared):
        return shared.get("user_query", "")

    def exec(self, user_query):
        prompt = f"""
        User Query: "{user_query}"

        Task: Extract the main keywords to search for.
        Return only the keywords.
        """
        response = call_llm(prompt)
        return response.strip()

    def post(self, shared, prep_res, exec_res):
        shared["search_term"] = exec_res
        return "default"

class AnswerNode(Node):
    def prep(self, shared):
        return shared.get("user_query"), shared.get("retrieved_context", [])

    def exec(self, inputs):
        query, context_list = inputs

        context_text = "\n\n".join([c.payload['text'] for c in context_list]) if context_list else "No relevant context found."

        prompt = f"""
        User Query: {query}

        Context:
        {context_text[:20000]}

        Task: Answer the user's question based *only* on the context provided above.
        Answer in Vietnamese.
        """
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["answer"] = exec_res
        return "default"

# --- New Nodes ---

class LoadFolderNode(Node):
    """
    Node to load all files from a specific Google Drive Folder ID.
    """
    def prep(self, shared):
        return shared.get("folder_id")

    def exec(self, folder_id):
        if not folder_id:
            raise ValueError("No Folder ID provided.")

        service = get_drive_service()
        if not service:
            raise RuntimeError("Could not create Drive Service.")

        # List all non-trashed files in the folder
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query, pageSize=100, fields="nextPageToken, files(id, name, mimeType)"
        ).execute()

        files = results.get('files', [])
        logger.info(f"Found {len(files)} files in folder {folder_id}")

        documents = []
        for f in files:
            # We skip folders inside folders for this simple iteration,
            # but could be recursive in a real app.
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                continue

            logger.info(f"Reading file: {f['name']}")
            try:
                content = read_file(f['id'], f['mimeType'])
                if content and isinstance(content, str) and len(content.strip()) > 0:
                     documents.append({"name": f['name'], "id": f['id'], "content": content})
            except Exception as e:
                logger.error(f"Failed to read file {f['name']}: {e}")

        return documents

    def post(self, shared, prep_res, exec_res):
        shared["documents"] = exec_res
        return "default"

class ChunkNode(Node):
    """
    Node to chunk documents.
    """
    def prep(self, shared):
        return shared.get("documents", [])

    def exec(self, documents):
        if not documents:
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        chunked_docs = []
        for doc in documents:
            chunks = splitter.split_text(doc['content'])
            for i, chunk in enumerate(chunks):
                chunked_docs.append({
                    "text": chunk,
                    "metadata": {
                        "source": doc['name'],
                        "file_id": doc['id'],
                        "chunk_index": i
                    }
                })

        logger.info(f"Generated {len(chunked_docs)} chunks from {len(documents)} documents.")
        return chunked_docs

    def post(self, shared, prep_res, exec_res):
        shared["chunks"] = exec_res
        return "default"

class QdrantIndexNode(Node):
    """
    Node to index chunks into Qdrant using FastEmbed for Hybrid Search.
    """
    def prep(self, shared):
        return shared.get("chunks", [])

    def exec(self, chunks):
        if not chunks:
            return "No chunks to index."

        # Initialize Qdrant Client (In-Memory)
        # In a real app, you might persist this to disk or a server
        client = QdrantClient(":memory:")

        # We need to store the client in a persistent place (like Streamlit session state)
        # BUT PocketFlow nodes are transient.
        # For this demo, we will re-create the collection every time we ingest,
        # which means previous data is lost if we restart.
        # To fix this in a persistent way, we would use a path on disk.

        # Let's use a local path to persist data across runs
        db_path = "./qdrant_db"
        if not os.path.exists(db_path):
            os.makedirs(db_path)

        client = QdrantClient(path=db_path)

        collection_name = "drive_docs"

        # Check if collection exists, if not create it
        # Note: When using FastEmbed (add/query), we don't strictly need to define vector config manually
        # if we rely on the library defaults, but it's good practice.
        # However, qdrant-client's `add` method handles it.

        # Prepare documents and metadata
        docs = [c['text'] for c in chunks]
        metadatas = [c['metadata'] for c in chunks]
        ids = list(range(len(docs))) # Simple integer IDs

        logger.info("Indexing chunks into Qdrant...")
        client.add(
            collection_name=collection_name,
            documents=docs,
            metadata=metadatas,
            ids=ids,
            parallel=0 # Use all cores
        )

        return f"Successfully indexed {len(docs)} chunks."

    def post(self, shared, prep_res, exec_res):
        shared["index_status"] = exec_res
        return "default"

class QdrantSearchNode(Node):
    """
    Node to search Qdrant using Hybrid Search.
    """
    def prep(self, shared):
        return shared.get("user_query")

    def exec(self, user_query):
        if not user_query:
            return []

        db_path = "./qdrant_db"
        client = QdrantClient(path=db_path)
        collection_name = "drive_docs"

        try:
             # Hybrid search happens automatically if the collection was created with `add`
             results = client.query(
                collection_name=collection_name,
                query_text=user_query,
                limit=5
            )
             return results
        except Exception as e:
            logger.warning(f"Search failed (maybe collection empty?): {e}")
            return []

    def post(self, shared, prep_res, exec_res):
        shared["retrieved_context"] = exec_res
        return "default"
