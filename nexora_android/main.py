import os
import threading
import time
import flet as ft
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NexoraAndroid")

# Set Android Mode Flag to disable heavy workers
os.environ["ANDROID_MODE"] = "true"

def start_backend():
    logger.info("Starting Backend Server...")
    try:
        # Import here to ensure env var is set
        # We need to add current dir to path to find 'backend' module
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from backend.server import app
        # Host 0.0.0.0 allows other devices to connect (Server Mode)
        # Port 8000
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        logger.error(f"Backend failed to start: {e}")

def main(page: ft.Page):
    page.title = "Nexora Ops"
    page.padding = 0
    page.bgcolor = "#000000"
    
    # Start Backend in Background Thread
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Show loading screen while backend starts
    loading_text = ft.Text("Initializing Nexora Core...", color="white", size=20)
    page.add(
        ft.Container(
            content=loading_text,
            alignment=ft.alignment.center,
            expand=True
        )
    )
    page.update()
    
    # Wait for backend (simple delay)
    time.sleep(3) 
    
    # Clear loading screen
    page.clean()
    
    # Add WebView pointing to local backend
    # We use 127.0.0.1 for the WebView to connect locally
    wv = ft.WebView(
        url="http://127.0.0.1:8000",
        expand=True,
        on_page_started=lambda _: logger.info("WebView: Page started"),
        on_page_ended=lambda _: logger.info("WebView: Page ended"),
        on_web_resource_error=lambda e: logger.error(f"WebView Error: {e.description}")
    )
    
    page.add(wv)

if __name__ == "__main__":
    ft.app(target=main)
