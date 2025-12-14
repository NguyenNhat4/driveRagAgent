from fastmcp import FastMCP
from utils.drive_tools import search_files, read_file, get_drive_service
import logging

# Initialize FastMCP server
mcp = FastMCP("Google Drive MCP")

@mcp.tool
def list_files(query: str) -> str:
    """
    List files in Google Drive based on a query.

    Args:
        query: The name query to search for.
    """
    try:
        files = search_files(query)
        if not files:
            return "No files found."

        result = "Files found:\n"
        for f in files:
            result += f"- {f['name']} (ID: {f['id']}, MIME: {f['mimeType']})\n"
        return result
    except Exception as e:
        return f"Error listing files: {str(e)}"

@mcp.tool
def get_file_content(file_id: str, mime_type: str = None) -> str:
    """
    Read the content of a file from Google Drive.

    Args:
        file_id: The ID of the file to read.
        mime_type: The MIME type of the file (optional, but recommended for Google Docs/PDFs).
    """
    try:
        # If mime_type is not provided, try to fetch it
        if not mime_type:
            service = get_drive_service()
            file_meta = service.files().get(fileId=file_id).execute()
            mime_type = file_meta.get('mimeType')

        content = read_file(file_id, mime_type)
        return content
    except Exception as e:
        return f"Error reading file content: {str(e)}"

if __name__ == "__main__":
    mcp.run()
