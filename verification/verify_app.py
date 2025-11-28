from playwright.sync_api import sync_playwright

def verify_streamlit_app():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Wait for streamlit to start
            page.goto("http://localhost:8501")
            page.wait_for_selector('text="🤖 Chat with your Google Drive"')
            page.screenshot(path="verification/streamlit_app.png")
            print("Screenshot taken successfully")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_streamlit_app()
