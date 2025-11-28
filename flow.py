from pocketflow import Flow
from nodes import ExtractSearchTermNode, SearchDriveNode, ReadDocumentNode, AnswerNode

def create_rag_flow():
    # Instantiate nodes
    extract = ExtractSearchTermNode()
    search = SearchDriveNode()
    read = ReadDocumentNode()
    answer = AnswerNode()

    # Define transitions
    # Extract -> Search
    extract >> search
    extract - "skip_search" >> answer # If just chit-chat

    # Search -> Read or Answer (if not found)
    search - "found" >> read
    search - "not_found" >> answer

    # Read -> Answer
    read >> answer

    # Create Flow
    return Flow(start=extract)
