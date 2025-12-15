from pocketflow import Node
from utils.call_llm import call_llm
from utils.drive_tools import search_files, read_file, get_drive_service
import os
import uuid
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVectorParams, Filter, FieldCondition, MatchValue, Prefetch, SparseVector
from utils.embedding_models import get_embedding_models

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
        Answer in the same language as the User Query.
        """
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["answer"] = exec_res
        return "default"

# --- New Nodes ---

class LoadFolderNode(Node):
    """
    Node to load all files from a specific Google Drive Folder ID.
    Checks if files are already indexed in Qdrant to avoid redundant processing.
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

        # Check existing files in Qdrant
        db_path = "./qdrant_db"
        collection_name = "drive_docs"
        client = QdrantClient(path=db_path)

        # We process files one by one and check existence
        documents = []
        for f in files:
            # We skip folders inside folders for this simple iteration
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                continue

            file_id = f['id']

            # Check if this file is already indexed
            if client.collection_exists(collection_name):
                count_result = client.count(
                    collection_name=collection_name,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="file_id",
                                match=MatchValue(value=file_id)
                            )
                        ]
                    )
                )
                if count_result.count > 0:
                    logger.info(f"Skipping file {f['name']} (ID: {file_id}) - already indexed.")
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
    Node to index chunks into Qdrant using FastEmbed for Hybrid Search (Dense + Sparse + ColBERT).
    """
    def prep(self, shared):
        return shared.get("chunks", [])

    def exec(self, chunks):
        if not chunks:
            return "No chunks to index."

        db_path = "./qdrant_db"
        if not os.path.exists(db_path):
            os.makedirs(db_path)

        client = QdrantClient(path=db_path)
        collection_name = "drive_docs"

        # Get cached models
        dense_model, sparse_model, colbert_model = get_embedding_models()

        # Check if collection exists and create if NOT exists (incremental update)
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(size=384, distance=Distance.COSINE),
                    "colbert": VectorParams(size=128, distance=Distance.COSINE, multivector_config={"comparator": "max_sim"}),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(index=None) # Default index
                }
            )

        logger.info("Generating embeddings and indexing...")

        # Process in batches (if needed, but simple list for now)
        docs_text = [c['text'] for c in chunks]

        # Generate all embeddings
        # Generators return iterables, we consume them
        dense_embeddings = list(dense_model.embed(docs_text))
        sparse_embeddings = list(sparse_model.embed(docs_text))
        colbert_embeddings = list(colbert_model.embed(docs_text))

        points = []
        for i, text in enumerate(docs_text):
            # Deterministic UUID for idempotency
            # Combine file_id and chunk_index to make a unique ID string
            file_id = chunks[i]['metadata']['file_id']
            chunk_idx = chunks[i]['metadata']['chunk_index']
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{file_id}_{chunk_idx}"))

            # Create PointStruct
            points.append(PointStruct(
                id=point_id,
                vector={
                    "dense": dense_embeddings[i].tolist(),
                    "colbert": colbert_embeddings[i].tolist(),
                    "sparse": sparse_embeddings[i].as_object()
                },
                payload={
                    "text": text,
                    **chunks[i]['metadata']
                }
            ))

        # Upsert
        client.upsert(
            collection_name=collection_name,
            points=points
        )

        return f"Successfully indexed {len(chunks)} chunks with Hybrid + ColBERT embeddings."

    def post(self, shared, prep_res, exec_res):
        shared["index_status"] = exec_res
        return "default"

class QdrantSearchNode(Node):
    """
    Node to search Qdrant using Hybrid Search and Late Interaction Re-ranking.
    """
    def prep(self, shared):
        return shared.get("user_query")

    def exec(self, user_query):
        if not user_query:
            return []

        db_path = "./qdrant_db"
        client = QdrantClient(path=db_path)
        collection_name = "drive_docs"

        # Get cached models
        dense_model, sparse_model, colbert_model = get_embedding_models()

        # Generate query embeddings
        # Models expect list of strings
        query_dense = list(dense_model.embed([user_query]))[0]
        query_sparse = list(sparse_model.embed([user_query]))[0]
        query_colbert = list(colbert_model.embed([user_query]))[0]

        dense_vec = query_dense.tolist()
        sparse_vec = SparseVector(**query_sparse.as_object())
        colbert_vec = query_colbert.tolist()

        try:
             # Hybrid Search (Dense + Sparse) Prefetch
             # We fetch more candidates to re-rank with ColBERT

             results = client.query_points(
                 collection_name=collection_name,
                 prefetch=[
                     # Prefetch with Dense
                     Prefetch(
                         query=dense_vec,
                         using="dense",
                         limit=20
                     ),
                     # Prefetch with Sparse
                     Prefetch(
                         query=sparse_vec,
                         using="sparse",
                         limit=20
                     )
                 ],
                 # Main query using ColBERT to re-rank the prefetched results
                 query=colbert_vec,
                 using="colbert",
                 limit=5
             ).points

             return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def post(self, shared, prep_res, exec_res):
        shared["retrieved_context"] = exec_res
        return "default"
