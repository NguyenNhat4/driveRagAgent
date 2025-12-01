from pocketflow import Flow
from nodes import (
    ExtractSearchTermNode,
    AnswerNode,
    LoadFolderNode,
    ChunkNode,
    QdrantIndexNode,
    QdrantSearchNode
)

def create_ingestion_flow():
    load = LoadFolderNode()
    chunk = ChunkNode()
    index = QdrantIndexNode()

    load >> chunk >> index

    return Flow(start=load)

def create_retrieval_flow():
    # We can skip extraction if we trust the raw query or use Qdrant's query_text
    # But let's keep it simple: Query -> Search -> Answer

    search = QdrantSearchNode()
    answer = AnswerNode()

    search >> answer

    return Flow(start=search)
