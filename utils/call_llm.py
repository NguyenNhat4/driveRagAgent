import os
import google.generativeai as genai
from google.api_core import retry

def call_llm(prompt: str) -> str:
    """
    Calls Google Gemini API.
    Reads GEMINI_API_KEY from environment variables.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found in environment variables."

    genai.configure(api_key=api_key)

    # Use a standard model
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error calling Gemini: {str(e)}"

if __name__ == "__main__":
    # Test call
    print(call_llm("Hello, say hi!"))
