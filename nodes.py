from pocketflow import Node
from utils.call_llm import call_llm
from utils.drive_tools import search_files, read_file
import json

class ExtractSearchTermNode(Node):
    def prep(self, shared):
        return shared.get("user_query", "")

    def exec(self, user_query):
        # System prompt to extract search term
        prompt = f"""
        User Query: "{user_query}"

        Task: Extract the main file name or keyword to search for in Google Drive.
        Only return the keyword/filename. Do not add any explanation.
        If the user is just saying hello, return "NONE".

        Example:
        Query: "What is in the annual_report_2023.pdf?"
        Output: annual_report_2023

        Query: "Find the meeting notes."
        Output: meeting notes
        """
        response = call_llm(prompt)
        return response.strip()

    def post(self, shared, prep_res, exec_res):
        shared["search_term"] = exec_res
        if exec_res == "NONE":
            return "skip_search"
        return "default"

class SearchDriveNode(Node):
    def prep(self, shared):
        return shared.get("search_term", ""), shared.get("creds_path", "service_account.json")

    def exec(self, inputs):
        search_term, creds_path = inputs
        if not search_term or search_term == "NONE":
            return []

        files = search_files(search_term, creds_path=creds_path)
        return files

    def post(self, shared, prep_res, exec_res):
        shared["files_found"] = exec_res
        if not exec_res:
            return "not_found"
        return "found"

class ReadDocumentNode(Node):
    def prep(self, shared):
        files = shared.get("files_found", [])
        creds_path = shared.get("creds_path", "service_account.json")
        if not files:
            return None
        # Naively pick the first file
        return files[0], creds_path

    def exec(self, inputs):
        if not inputs:
            return "No file to read."
        file_info, creds_path = inputs
        file_id = file_info['id']
        mime_type = file_info['mimeType']

        content = read_file(file_id, mime_type, creds_path=creds_path)
        return content

    def post(self, shared, prep_res, exec_res):
        shared["selected_file_content"] = exec_res
        return "default"

class AnswerNode(Node):
    def prep(self, shared):
        return shared.get("user_query"), shared.get("selected_file_content"), shared.get("files_found")

    def exec(self, inputs):
        query, content, files = inputs

        if not content:
            prompt = f"""
            User Query: {query}
            Context: No relevant files were found in the drive search.
            Task: Answer the user politely in Vietnamese explaining that no documents were found matching the request.
            """
        else:
            filename = files[0]['name'] if files else "the document"
            prompt = f"""
            User Query: {query}

            Context from file '{filename}':
            {content[:20000]}
            (Truncated if too long)

            Task: Answer the user's question based *only* on the context provided above.
            Answer in Vietnamese.
            If the answer is not in the context, say so.
            """

        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["answer"] = exec_res
        return "default"
